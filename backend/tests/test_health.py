import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_live_endpoint():
    """Verify /health/live returns HTTP 200 independently of any external dependencies."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "live"
    assert data["service"] == "backend-api"
    assert "timestamp" in data


def test_health_live_unaffected_by_database_state(monkeypatch):
    """Verify liveness probe returns HTTP 200 even when database is reported down."""
    monkeypatch.setattr("backend.app.api.health.check_db_health", lambda: False)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_health_ready_success(monkeypatch):
    """Verify /health/ready returns HTTP 200 when database health check succeeds."""
    monkeypatch.setattr("backend.app.api.health.check_db_health", lambda: True)
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "timestamp" in data


def test_health_ready_failure_returns_503(monkeypatch):
    """Verify /health/ready returns HTTP 503 and sanitized message when database check fails."""
    monkeypatch.setattr("backend.app.api.health.check_db_health", lambda: False)
    response = client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "disconnected"
    assert "detail" in data
    # Ensure sensitive credentials or raw tracebacks are not exposed
    content_str = str(data).lower()
    assert "password" not in content_str
    assert "traceback" not in content_str
    assert "postgres" not in content_str


def test_cors_preflight_allows_configured_origins():
    """Verify configured CORS origins receive access control allow headers."""
    response = client.options(
        "/health/live",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
