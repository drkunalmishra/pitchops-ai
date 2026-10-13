from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_healthz() -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_stats_requires_token() -> None:
    assert client.get("/v1/corpus/stats").status_code == 401
    assert client.get("/api/v1/corpus/stats").status_code == 401
    assert client.get("/api/v1/corpus/stats", headers={"Authorization": "Bearer junk"}).status_code == 401
