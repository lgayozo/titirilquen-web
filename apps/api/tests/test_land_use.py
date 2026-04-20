from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_land_use_solve() -> None:
    client = TestClient(app)
    r = client.post(
        "/land-use/solve",
        json={
            "L": 51,
            "CBD": 25,
            "land_use": {
                "H_por_estrato": [100, 100, 100],
                "beta": 1.0,
                "max_iter": 2000,
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["parcelas"]) == 51
    assert sum(len(p) for p in body["parcelas"]) == 300
    assert body["result"]["converged"] is True


def test_coupled_solve() -> None:
    client = TestClient(app)
    r = client.post(
        "/coupled/solve",
        json={
            "sim": {
                "city": {
                    "n_celdas": 51,
                    "largo_ciudad_km": 5,
                    "densidad_por_celda": 1,
                    "share_estratos": [0.1, 0.4, 0.5],
                },
                "supply": {},
                "demand": {
                    "estratos": {
                        "1": {"prob_teletrabajo": 0.2, "prob_auto": 0.6,
                              "betas": {"asc_auto": 1.5, "asc_metro": -0.2, "asc_bici": -0.9,
                                        "asc_caminata": -0.5, "b_tiempo_viaje": -0.055,
                                        "b_costo": -0.00008, "b_tiempo_espera": -0.05,
                                        "b_tiempo_caminata": -0.15,
                                        "penalizaciones_fisicas": {"bici_10": -0.09, "bici_20": -0.15,
                                                                    "bici_30": -0.5, "walk_5": -0.09,
                                                                    "walk_15": -0.18, "walk_25": -0.4}}},
                        "2": {"prob_teletrabajo": 0.2, "prob_auto": 0.6,
                              "betas": {"asc_auto": 1.5, "asc_metro": -0.2, "asc_bici": -0.9,
                                        "asc_caminata": -0.5, "b_tiempo_viaje": -0.055,
                                        "b_costo": -0.00008, "b_tiempo_espera": -0.05,
                                        "b_tiempo_caminata": -0.15,
                                        "penalizaciones_fisicas": {"bici_10": -0.09, "bici_20": -0.15,
                                                                    "bici_30": -0.5, "walk_5": -0.09,
                                                                    "walk_15": -0.18, "walk_25": -0.4}}},
                        "3": {"prob_teletrabajo": 0.2, "prob_auto": 0.6,
                              "betas": {"asc_auto": 1.5, "asc_metro": -0.2, "asc_bici": -0.9,
                                        "asc_caminata": -0.5, "b_tiempo_viaje": -0.055,
                                        "b_costo": -0.00008, "b_tiempo_espera": -0.05,
                                        "b_tiempo_caminata": -0.15,
                                        "penalizaciones_fisicas": {"bici_10": -0.09, "bici_20": -0.15,
                                                                    "bici_30": -0.5, "walk_5": -0.09,
                                                                    "walk_15": -0.18, "walk_25": -0.4}}},
                    }
                },
                "max_iter": 3,
                "seed": 42,
            },
            "land_use": {
                "H_por_estrato": [30, 50, 70],
                "max_iter": 2000,
            },
            "outer_max_iter": 2,
            "outer_tol": 1.0,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["iterations"]) >= 1
    first = body["iterations"][0]
    assert "land_use" in first
    assert "transport" in first
    assert "T_matrix" in first
