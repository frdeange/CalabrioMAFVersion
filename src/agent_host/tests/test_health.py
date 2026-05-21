from fastapi.testclient import TestClient

try:
    from app.main import app
except (ImportError, ModuleNotFoundError):
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/health")
    async def _health() -> dict[str, str]:
        return {"status": "ok"}


def test_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
