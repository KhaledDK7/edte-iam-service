import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from src.main import app

DATA = Path(__file__).resolve().parents[2] / "data"


def _payload() -> dict[str, Any]:
    return {
        "users": json.loads((DATA / "users.json").read_text(encoding="utf-8")),
        "roles": json.loads((DATA / "roles.json").read_text(encoding="utf-8")),
        "policies": json.loads((DATA / "policies.json").read_text(encoding="utf-8")),
    }


def test_health() -> None:
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_ingest_ok(fake_driver) -> None:  # type: ignore[no-untyped-def]
    app.state.driver = fake_driver
    response = TestClient(app).post("/api/v1/iam/ingest", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["actors_written"] == 6
    assert body["roles_written"] == 10
    assert body["grants_written"] == 8


def test_ingest_rejects_invalid_urn(fake_driver) -> None:  # type: ignore[no-untyped-def]
    app.state.driver = fake_driver
    payload = _payload()
    payload["users"][0]["urn"] = "not-a-urn"
    response = TestClient(app).post("/api/v1/iam/ingest", json=payload)
    assert response.status_code == 422
    assert fake_driver.log == []


def test_ingest_neo4j_down_returns_503() -> None:
    class DownDriver:
        def session(self) -> Any:
            raise ServiceUnavailable("connection refused")

    app.state.driver = DownDriver()
    response = TestClient(app).post("/api/v1/iam/ingest", json=_payload())
    assert response.status_code == 503
