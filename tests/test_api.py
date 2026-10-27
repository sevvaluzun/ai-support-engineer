
import pytest
from fastapi.testclient import TestClient

import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use an isolated SQLite database for every test
    test_db = tmp_path / "test_tickets.db"

    monkeypatch.setattr(app, "DB_PATH", str(test_db))

    with TestClient(app.app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_and_get_ticket(client):
    payload = {
        "customer": "Test Company",
        "subject": "Login Error",
        "description": "Users cannot log in."
    }

    response = client.post("/tickets", json=payload)

    assert response.status_code == 201

    ticket = response.json()
    assert ticket["customer"] == "Test Company"
    assert ticket["subject"] == "Login Error"
    assert ticket["status"] == "open"

    ticket_id = ticket["id"]

    get_response = client.get(f"/tickets/{ticket_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == ticket_id


def test_missing_ticket_returns_404(client):
    response = client.get("/tickets/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"

from llm_service import TicketAnalysis


@pytest.fixture
def sample_ticket(client):
    response = client.post(
        "/tickets",
        json={
            "customer": "Test Company",
            "subject": "API Error 429",
            "description": "Users receive HTTP 429 errors."
        }
    )

    assert response.status_code == 201
    return response.json()


def test_ai_analysis_with_mock(client, sample_ticket, monkeypatch):
    def fake_analyze_ticket(subject, description):
        return TicketAnalysis(
            category="API Rate Limiting",
            priority="high",
            possible_cause="Rate limit may have been exceeded.",
            suggested_action="Review request volume.",
            sources=["API Rate Limiting"]
        )

    monkeypatch.setattr(
        app,
        "analyze_ticket",
        fake_analyze_ticket
    )

    ticket_id = sample_ticket["id"]

    response = client.post(f"/tickets/{ticket_id}/analyze")

    assert response.status_code == 200
    assert response.json()["category"] == "API Rate Limiting"
    assert response.json()["priority"] == "high"
    assert response.json()["sources"] == ["API Rate Limiting"]

    history = client.get(f"/tickets/{ticket_id}/analyses")

    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["sources"] == ["API Rate Limiting"]


def test_log_investigation_with_mock(client, sample_ticket, monkeypatch):
    def fake_investigate_logs(subject, description):
        return "HTTP 429 rate limit warning found in simulated logs."

    monkeypatch.setattr(
        app,
        "investigate_ticket_logs",
        fake_investigate_logs
    )

    ticket_id = sample_ticket["id"]

    response = client.post(f"/tickets/{ticket_id}/investigate")

    assert response.status_code == 200
    assert response.json()["ticket_id"] == ticket_id
    assert "HTTP 429" in response.json()["investigation"]


def test_full_investigation_with_mock(client, sample_ticket, monkeypatch):
    def fake_analyze_ticket(subject, description):
        return TicketAnalysis(
            category="API Rate Limiting",
            priority="medium",
            possible_cause="Possible rate limit issue.",
            suggested_action="Check API usage.",
            sources=["API Rate Limiting"]
        )

    def fake_investigate_logs(subject, description):
        return "Simulated API logs contain HTTP 429 warnings."

    monkeypatch.setattr(app, "analyze_ticket", fake_analyze_ticket)
    monkeypatch.setattr(
        app,
        "investigate_ticket_logs",
        fake_investigate_logs
    )

    ticket_id = sample_ticket["id"]

    response = client.post(
        f"/tickets/{ticket_id}/full-investigation"
    )

    assert response.status_code == 200

    result = response.json()

    assert result["ticket_id"] == ticket_id
    assert result["analysis"]["priority"] == "medium"
    assert result["analysis"]["sources"] == ["API Rate Limiting"]
    assert "HTTP 429" in result["log_investigation"]
    assert isinstance(result["analysis_id"], int)

    history = client.get(f"/tickets/{ticket_id}/analyses")
    assert len(history.json()) == 1
