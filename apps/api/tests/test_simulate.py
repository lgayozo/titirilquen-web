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


def test_simulate_con_q_dada_reproduce_la_corrida() -> None:
    # D11c: la `localizacion_Q` de una corrida, reenviada como `Q_dada`, puebla
    # la ciudad igual (la lente Transporte de Comparar congela así la base).
    client = TestClient(app)
    req = {
        "sim": _config_pequeno(),
        "land_use": {"H_por_estrato": [25, 100, 125], "forma": "normal", "max_iter": 200},
        "localizacion": "equilibrio",
    }
    base = client.post("/simulate", json=req).json()
    assert len(base["localizacion_Q"]) == 3
    otra = client.post("/simulate", json={**req, "Q_dada": base["localizacion_Q"]}).json()
    assert otra["agentes"] == base["agentes"]
