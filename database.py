
import os
import sqlite3

import psycopg
from psycopg.rows import dict_row


def get_database_type():
    """
    Choose the database according to environment variables.
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        if not database_url.startswith(
            ("postgresql://", "postgres://")
        ):
            raise ValueError("Unsupported DATABASE_URL")

        return "postgresql"

    return "sqlite"


def get_connection():
    """
    Return a connection to SQLite or PostgreSQL.
    """
    database_type = get_database_type()

    if database_type == "postgresql":
        return psycopg.connect(
            os.environ["DATABASE_URL"],
            row_factory=dict_row,
            connect_timeout=10
        )

    db_path = os.getenv(
        "DB_PATH",
        "/app/data/tickets.db"
    )

    os.makedirs(
        os.path.dirname(db_path) or ".",
        exist_ok=True
    )

    conn = sqlite3.connect(
        db_path,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn

def adapt_query(query: str) -> str:
    """
    Convert SQLite parameter placeholders
    to PostgreSQL placeholders when needed.
    """
    if get_database_type() == "postgresql":
        return query.replace("?", "%s")

    return query


def execute_query(conn, query: str, params=()):
    """
    Run a parameterized SQL statement
    using the selected database.
    """
    return conn.execute(
        adapt_query(query),
        params
    )
