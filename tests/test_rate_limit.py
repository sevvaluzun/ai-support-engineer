
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import app


def test_daily_ai_limit(monkeypatch):
    """
    Verify that the first 10 requests are accepted
    and the 11th request is rejected.
    No Gemini API calls or real database writes.
    """
    usage = {"count": 0}
    dates = []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, query, params):
            usage_date, limit = params
            dates.append(usage_date)

            if usage["count"] >= limit:
                return FakeCursor(None)

            usage["count"] += 1
            return FakeCursor({"request_count": usage["count"]})

    class FakeCursor:
        def __init__(self, result):
            self.result = result

        def fetchone(self):
            return self.result

    monkeypatch.setattr(
        app, "get_database_type", lambda: "postgresql"
    )
    monkeypatch.setattr(
        app, "get_connection", lambda: FakeConnection()
    )

    # First 10 requests should succeed
    for _ in range(10):
        app.consume_ai_quota()

    assert usage["count"] == 10

    # The 11th request must be rejected
    with pytest.raises(HTTPException) as error:
        app.consume_ai_quota()

    assert error.value.status_code == 429
    assert usage["count"] == 10

    # All requests were assigned to the current UTC date
    assert set(dates) == {
        datetime.now(timezone.utc).date().isoformat()
    }
