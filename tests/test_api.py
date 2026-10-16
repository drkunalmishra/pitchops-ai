from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_healthz() -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_stats_requires_token() -> None:
    assert client.get("/v1/corpus/stats").status_code == 401
    assert client.get("/api/v1/corpus/stats").status_code == 401
    assert client.get("/api/v1/corpus/stats", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_post_endpoints_take_json_bodies() -> None:
    """Request models must be module-level: models defined inside a router factory (with postponed annotations)
    silently become a required ?body= query parameter and every POST returns 422."""
    from services.api.main import app

    spec = app.openapi()
    for path, ops in spec["paths"].items():
        post = ops.get("post")
        if not post or path.endswith("/upload") or not path.startswith("/v1/"):
            continue
        assert not any(p["name"] == "body" for p in post.get("parameters", [])), path
        if any(k in path for k in ("approve", "reject", "versions", "regenerate-line", "edit", "selection", "relevance")):
            assert "requestBody" in post, f"{path} has no JSON body"
