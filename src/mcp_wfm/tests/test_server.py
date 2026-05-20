from fastapi.testclient import TestClient

from app.server import app


def test_server_imports() -> None:
    from app import server  # noqa: F401


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
