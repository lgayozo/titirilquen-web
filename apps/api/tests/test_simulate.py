from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from titirilquen_core.presets import DEFAULT_STRATA


def _config_pequeno() -> dict:
    return {
        "city": {
            "n_celdas": 51,
            "largo_ciudad_km": 5,
            # Era `densidad_por_celda: 5`, campo renombrado en D-28. La
            # conversión documentada es hab/celda x (n_celdas-1) / largo_km:
            # 5 x 50 / 5 = 50 hab/km. El test llevaba meses en 422 porque
            # `apps/api/tests` no está en `testpaths` y nadie lo corría.
            "densidad_hab_km": 50,
            "share_estratos": [0.1, 0.4, 0.5],
        },
        "supply": {},
        "demand": {"estratos": DEFAULT_STRATA},
        "max_iter": 3,
        "seed": 42,
    }


def test_simulate_endpoint() -> None:
    client = TestClient(app)
    r = client.post("/simulate", json=_config_pequeno())
    assert r.status_code == 200
    body = r.json()
    assert "iteraciones" in body
    assert len(body["iteraciones"]) == 3
    assert "agentes" in body
    assert body["iteraciones"][-1]["modal_split"] is not None


def test_stream_endpoint() -> None:
    client = TestClient(app)
    with client.stream("POST", "/simulate/stream", json=_config_pequeno()) as r:
        assert r.status_code == 200
        eventos = 0
        done = False
        for line in r.iter_lines():
            if line.startswith("data:"):
                eventos += 1
            if line.startswith("event: done"):
                done = True
        assert eventos >= 3
        assert done
