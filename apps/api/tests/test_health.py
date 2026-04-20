from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_health() -> None:
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_presets() -> None:
    client = TestClient(app)
    r = client.get("/presets")
    assert r.status_code == 200
    data = r.json()
    assert "city" in data
    assert "policy" in data
    assert "strata_default" in data
    assert "Pro-Bici" in data["policy"]
