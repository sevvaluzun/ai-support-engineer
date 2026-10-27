import logging
import os
import json
import sqlite3

from tool_service import investigate_ticket_logs
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from llm_service import analyze_ticket, TicketAnalysis


DB_PATH = os.getenv("DB_PATH", "/app/data/tickets.db")


# -----------------------------------
# DATABASE CONNECTION
# -----------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------------
# DATABASE INITIALIZATION + MIGRATION
# -----------------------------------

def initialize_database():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

    with get_connection() as conn:

        # Tickets table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            )
        """)

        # AI analysis history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ticket_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                possible_cause TEXT NOT NULL,
                suggested_action TEXT NOT NULL,
                analyzed_at TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT '[]',
                FOREIGN KEY (ticket_id) REFERENCES tickets(id)
            )
        """)

        # Migration for existing databases
        columns = conn.execute(
            "PRAGMA table_info(ticket_analyses)"
        ).fetchall()

        column_names = [column["name"] for column in columns]

        if "sources" not in column_names:
            conn.execute(
                "ALTER TABLE ticket_analyses "
                "ADD COLUMN sources TEXT NOT NULL DEFAULT '[]'"
            )


# -----------------------------------
# FASTAPI APPLICATION
# -----------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="AI Support Engineer",
    lifespan=lifespan
)


# -----------------------------------
# PYDANTIC MODELS
# -----------------------------------

class TicketCreate(BaseModel):
    customer: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    description: str = Field(min_length=1)


# -----------------------------------
# HEALTH CHECK
# -----------------------------------

@app.get("/health")
def health_check():
    return {"status": "healthy"}


# -----------------------------------
# CREATE TICKET
# -----------------------------------

@app.post("/tickets", status_code=201)
def create_ticket(ticket: TicketCreate):
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tickets (
                customer,
                subject,
                description,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                ticket.customer,
                ticket.subject,
                ticket.description,
                created_at
            )
        )

        ticket_id = cursor.lastrowid

    return get_ticket(ticket_id)


# -----------------------------------
# LIST TICKETS
# -----------------------------------

@app.get("/tickets")
def get_tickets():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tickets ORDER BY id"
        ).fetchall()

    return [dict(row) for row in rows]


# -----------------------------------
# GET TICKET BY ID
# -----------------------------------

@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return dict(row)


# -----------------------------------
# SAVE AI ANALYSIS TO SQLITE
# -----------------------------------

def save_analysis(ticket_id: int, analysis: TicketAnalysis):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO ticket_analyses (
                ticket_id,
                category,
                priority,
                possible_cause,
                suggested_action,
                analyzed_at,
                sources
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                analysis.category,
                analysis.priority,
                analysis.possible_cause,
                analysis.suggested_action,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(analysis.sources, ensure_ascii=False)
            )
        )

        return cursor.lastrowid


# -----------------------------------
# ANALYZE TICKET USING GEMINI + RAG
# -----------------------------------

@app.post(
    "/tickets/{ticket_id}/analyze",
    response_model=TicketAnalysis
)
def analyze_existing_ticket(ticket_id: int):
    ticket = get_ticket(ticket_id)

    try:
        analysis = analyze_ticket(
            subject=ticket["subject"],
            description=ticket["description"]
        )

    except Exception:
        logging.exception("Log investigation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log investigation is temporarily unavailable"
        )

    save_analysis(ticket_id, analysis)

    return analysis


# -----------------------------------
# GET AI ANALYSIS HISTORY
# -----------------------------------

@app.get("/tickets/{ticket_id}/analyses")
def get_ticket_analyses(ticket_id: int):
    get_ticket(ticket_id)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM ticket_analyses
            WHERE ticket_id = ?
            ORDER BY id DESC
            """,
            (ticket_id,)
        ).fetchall()

    analyses = []

    for row in rows:
        analysis = dict(row)

        # Convert JSON text into a Python list
        analysis["sources"] = json.loads(analysis["sources"])

        analyses.append(analysis)

    return analyses

class InvestigationResponse(BaseModel):
    ticket_id: int
    investigation: str


@app.post(
    "/tickets/{ticket_id}/investigate",
    response_model=InvestigationResponse
)
def investigate_existing_ticket(ticket_id: int):
    ticket = get_ticket(ticket_id)

    try:
        investigation = investigate_ticket_logs(
            subject=ticket["subject"],
            description=ticket["description"]
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Log investigation is temporarily unavailable"
        )

    return InvestigationResponse(
        ticket_id=ticket_id,
        investigation=investigation
    )

# -----------------------------------
# COMBINED AI ANALYSIS + LOG INVESTIGATION
# -----------------------------------

class FullInvestigationResponse(BaseModel):
    ticket_id: int
    analysis_id: int
    analysis: TicketAnalysis
    log_investigation: str


@app.post(
    "/tickets/{ticket_id}/full-investigation",
    response_model=FullInvestigationResponse
)
def full_investigation(ticket_id: int):
    ticket = get_ticket(ticket_id)

    try:
        analysis = analyze_ticket(
            subject=ticket["subject"],
            description=ticket["description"]
        )

        investigation = investigate_ticket_logs(
            subject=ticket["subject"],
            description=ticket["description"]
        )

    except Exception:
        logging.exception("Full investigation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Full investigation is temporarily unavailable"
        )

    analysis_id = save_analysis(ticket_id, analysis)

    return FullInvestigationResponse(
        ticket_id=ticket_id,
        analysis_id=analysis_id,
        analysis=analysis,
        log_investigation=investigation
    )

