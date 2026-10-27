import os
import sqlite3
from pathlib import Path

LOG_DB_PATH = Path(
    os.getenv("LOG_DB_PATH", "/app/data/system_logs.db")
)



def initialize_logs():
    LOG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(LOG_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        count = conn.execute(
            "SELECT COUNT(*) FROM system_logs"
        ).fetchone()[0]

        if count == 0:
            sample_logs = [
                (
                    "authentication",
                    "ERROR",
                    "Database connection timeout during login",
                    "2026-10-27T14:00:00Z"
                ),
                (
                    "authentication",
                    "ERROR",
                    "Login requests failing with HTTP 500",
                    "2026-10-27T14:01:00Z"
                ),
                (
                    "api",
                    "WARNING",
                    "Rate limit exceeded: HTTP 429",
                    "2026-10-27T14:02:00Z"
                ),
                (
                    "database",
                    "ERROR",
                    "Connection pool exhausted",
                    "2026-10-27T14:03:00Z"
                )
            ]

            conn.executemany(
                """
                INSERT INTO system_logs (
                    service,
                    level,
                    message,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                sample_logs
            )


def search_logs(service: str, limit: int = 10):
    """
    Search simulated system logs by service.

    Args:
        service: Select authentication, api, or database.
                 Use authentication for login, auth,
                 or sign-in problems.
        limit: Maximum number of records to retrieve.
    """

    # Validate model-provided arguments
    allowed_services = {"authentication", "api", "database"}

    if service not in allowed_services:
        return {
            "error": "Invalid service",
            "allowed_services": sorted(allowed_services)
        }

    limit = max(1, min(int(limit), 50))

    print(
        f"[TOOL CALLED] search_logs("
        f"service={service}, limit={limit})"
    )

    with sqlite3.connect(LOG_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT service, level, message, created_at
            FROM system_logs
            WHERE service = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (service, limit)
        ).fetchall()

    return [dict(row) for row in rows]


if __name__ == "__main__":
    initialize_logs()

    results = search_logs("authentication")

    for log in results:
        print(log)
