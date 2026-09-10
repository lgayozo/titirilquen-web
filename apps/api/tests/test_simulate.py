from __future__ import annotations

from fastapi.testclient import TestClient
from titirilquen_core.presets import DEFAULT_STRATA

from api.main import app


def _config_pequeno() -> dict:
    return {
        "city": {"n_celdas": 51, "largo_ciudad_km": 5},
        "supply": {},
        "demand": {"estratos": DEFAULT_STRATA},
        "max_iter": 3,
        "seed": 42,
    }


def test_simulate_endpoint() -> None:
    client = TestClient(app)
    # 250 hogares sobre oferta uniforme y mezcla π_h: la «densidad plana» de
    # antes (50 hab/km × 5 km), ahora como uso de suelo (D-46).
    r = client.post(
        "/simulate",
        json={
            "sim": _config_pequeno(),
            "land_use": {"H_por_estrato": [25, 100, 125], "forma": "uniforme", "max_iter": 200},
            "localizacion": "original",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "iteraciones" in body
    assert len(body["iteraciones"]) == 3
    assert "agentes" in body
    assert body["iteraciones"][-1]["modal_split"] is not None
