"""Los números de los tutoriales de la aplicación (`apps/web/src/tutorials`).

Mismo contrato que los `datos_capNN.py`: los MDX transcriben desde
`tutoriales.json`, y regenerar no cambia nada salvo `_meta`. Todo se corre con
la configuración con que arranca la aplicación (`_config_web`, `_land_use_web`)
y los escenarios replican los de `apps/web/src/tutorials/scenarios.ts`: parten
de los defaults y cambian un solo campo.

Correr desde `packages/titirilquen_core`:

    uv run python ../../docs/libro/datos/datos_tutoriales.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "packages" / "titirilquen_core" / "tests"))

import test_linea_base as base

from titirilquen_core.bienestar import (
    _dinero_del_modo,
    calcular_agregados,
    minutos_ponderados,
    vot_clp_hora,
)
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.constantes import MODOS, TOL_ACOPLADO_CLP_MES
from titirilquen_core.coupled_metrics import _theil
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    _agrupar_agentes,
    iter_msa_desde_suelo,
)
from titirilquen_core.land_use.accesibilidad import T_flujo_libre, lambda_desde_demanda
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.equilibrium import solve_subasta
from titirilquen_core.presets import POLICY_PRESETS
from titirilquen_core.serializacion import _dist_media_km

SALIDA = Path(__file__).parent / "tutoriales.json"
ESTRATOS = (1, 2, 3)
NOMBRES = ("alto", "medio", "bajo")


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "desconocido"


def _sim(cambios: dict | None = None) -> SimulationConfig:
    """La config de la app con `cambios` = {"ruta.con.puntos": valor}."""
    d = base._config_web().model_dump()
    for ruta, valor in (cambios or {}).items():
        *camino, hoja = ruta.split(".")
        nodo = d
        for k in camino:
            nodo = nodo[int(k) if k.isdigit() else k]
        nodo[hoja] = valor
    return SimulationConfig.model_validate(d)


# ---------------------------------------------------------------------------
# Transporte
# ---------------------------------------------------------------------------


def _corre(sim: SimulationConfig) -> tuple[dict, ConvergenceTrace]:
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, base._land_use_web(), trace, localizacion="original"):
        pass
    a = calcular_agregados(sim, trace)
    assert a is not None
    return a, trace


def _tiempos(snap, i: int) -> TiemposObservados:
    return TiemposObservados(
        auto_total=float(snap.t_auto[i]),
        bici_total=float(snap.t_bici[i]),
        bici_libre=float(snap.t_bici_libre[i]),
        tren_acceso=float(snap.t_tren_acceso[i]),
        tren_espera=float(snap.t_tren_espera[i]),
        tren_viaje=float(snap.t_tren_viaje[i]),
    )


def _cg_min_equiv(sim: SimulationConfig, trace: ConvergenceTrace) -> dict:
    """Costo generalizado percibido en minutos-equivalentes por viaje: los
    minutos ponderados como la utilidad del estrato más el dinero pasado a
    minutos con el VoT del estrato. Las mismas piezas que `calcular_agregados`
    usa para el costo en pesos, pero sin pesos: así se suman estratos con
    VoT distintos sin que el ingreso pondere."""
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    snap = trace.iteraciones[-1]
    assert trace.demanda_estrato is not None
    num = dict.fromkeys(MODOS, 0.0)
    den = dict.fromkeys(MODOS, 0.0)
    for i in range(ciudad.n_celdas):
        dist = abs(ciudad.cbd_index - i) * ciudad.ancho_celda_km
        t_cam = dist / sim.demand.globales.v_caminata * 60.0
        tiempos = _tiempos(snap, i)
        for h in ESTRATOS:
            b = sim.demand.estratos[h].betas
            bt = abs(b.b_tiempo_viaje)
            vot = vot_clp_hora(sim, h)
            for k, modo in enumerate(MODOS):
                d = float(trace.demanda_estrato[h - 1, k, i])
                if d <= 0:
                    continue
                m = minutos_ponderados(
                    modo,
                    tiempos,
                    t_cam,
                    w_espera=abs(b.b_tiempo_espera) / bt,
                    w_acceso=abs(b.b_tiempo_acceso) / bt,
                    w_caminata=abs(b.b_tiempo_caminata) / bt,
                )
                num[modo] += d * (m + 60.0 * _dinero_del_modo(modo, sim, dist) / vot)
                den[modo] += d
    return {
        "medio": round(sum(num.values()) / sum(den.values()), 2),
        "por_modo": {m: round(num[m] / den[m], 2) for m in MODOS if den[m] > 0},
    }


def _fila(sim: SimulationConfig) -> dict:
    a, trace = _corre(sim)
    snap = trace.iteraciones[-1]
    n = a["viajeros"]
    assert trace.demanda_estrato is not None
    metro = trace.demanda_estrato[:, MODOS.index("Metro"), :].sum(axis=0)
    return {
        "iteraciones": len(trace.iteraciones),
        "convergio": bool(trace.converged),
        "brecha_final_min": round(float(trace.gap_final_min), 3),
        "reparto_pct": {m: round(100.0 * a["viajes_por_modo"][m] / n, 2) for m in MODOS},
        "auto_por_estrato_pct": {
            NOMBRES[h - 1]: round(
                100.0
                * a["viajes_por_modo_estrato"][str(h)]["Auto"]
                / sum(a["viajes_por_modo_estrato"][str(h)].values()),
                2,
            )
            for h in ESTRATOS
        },
        "frecuencia_metro_tph": round(float(snap.frecuencia_metro), 2),
        "espera_metro_min": round(float(np.sum(metro * snap.t_tren_espera) / metro.sum()), 2),
        "cg_min_equiv": _cg_min_equiv(sim, trace),
    }


def limite_del_logit() -> dict:
    """El determinístico como logit con λ → ∞, a tiempos FIJOS (los del
    equilibrio de la app): reparto con las utilidades ×k contra el reparto con
    cada grupo en su mejor modo. Sin re-equilibrar, porque el determinístico no
    tiene punto fijo (D9b) y no habría contra qué medir."""
    sim = base._config_web()
    _, trace = _corre(sim)
    snap = trace.iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    grupos, _ = _agrupar_agentes(trace.agentes)
    V, w = [], []
    for g in grupos:
        u = calcular_utilidades(
            estrato=g.estrato,
            celda_origen=g.celda,
            tiene_auto=g.tiene_auto,
            ciudad=ciudad,
            config=sim.demand,
            tiempos_observados=_tiempos(snap, g.celda),
        )
        V.append([u[m].valor if u[m].feasible else -np.inf for m in MODOS])
        w.append(len(g.agentes))
    V, w = np.asarray(V), np.asarray(w, dtype=float)
    aon = np.zeros_like(V)
    aon[np.arange(len(V)), np.argmax(V, axis=1)] = 1.0
    r_aon = 100.0 * (w @ aon) / w.sum()
    filas = []
    for k in (1, 5, 20, 50):
        x = k * (V - V.max(axis=1, keepdims=True))
        p = np.exp(x)
        p /= p.sum(axis=1, keepdims=True)
        r = 100.0 * (w @ p) / w.sum()
        filas.append({"escala": k, "distancia_max_pp": round(float(np.max(np.abs(r - r_aon))), 2)})
    return {"grupos": len(grupos), "filas": filas}


def pistas() -> dict:
    """Downs-Thomson con los dos métodos, con la parada de la aplicación: lo
    que el usuario ve al mover el control de pistas. Al elegir todo o nada la
    interfaz lleva el tope a 100 iteraciones como mínimo (D-70)."""
    out = {}
    for metodo in ("expected", "todo_o_nada"):
        tope = (
            {"max_iter": max(base._config_web().max_iter, 100)} if metodo == "todo_o_nada" else {}
        )
        out[metodo] = [
            {
                "num_pistas": n,
                **_fila(_sim({"supply.car.num_pistas": n, "assignment": metodo, **tope})),
            }
            for n in (1, 2, 3, 4, 6)
        ]
    return out


def experimentos_transporte() -> dict:
    """Las actividades A, C y E de «Experimentar» (scenarios.ts)."""
    pro_bici = POLICY_PRESETS["Pro-Bici"]["cap_bici"]
    return {
        "parking": {
            str(v): _fila(_sim({"demand.globales.costo_parking": v}))
            for v in (0, base._config_web().demand.globales.costo_parking, 5000)
        },
        "bici": {
            str(v): _fila(_sim({"supply.bike.capacidad_pista": v}))
            for v in (base._config_web().supply.bike.capacidad_pista, pro_bici)
        },
        "msa": {str(v): _fila(_sim({"max_iter": v})) for v in (3, 40)},
    }


# ---------------------------------------------------------------------------
# Suelo (la página Uso de suelo: subasta standalone con T a flujo libre)
# ---------------------------------------------------------------------------


def _suelo(sim: SimulationConfig, lu: LandUseConfig | None = None) -> LandUseCity:
    """Lo mismo que `land_use_solve_from_json` del worker."""
    L = sim.city.n_celdas
    dx = sim.city.largo_ciudad_km / L
    T = T_flujo_libre(sim.demand, L, L // 2, dx, sim.modos_habilitados, supply=sim.supply)
    city = LandUseCity.build(
        L=L,
        CBD=L // 2,
        cfg=lu or base._land_use_web(),
        ancho_celda_km=dx,
        T=T,
        lambda_h=lambda_desde_demanda(sim.demand),
        rng=np.random.default_rng(42),
    )
    assert city.result is not None and city.result.converged
    return city


def _resumen_suelo(city: LandUseCity) -> dict:
    assert city.result is not None
    return {
        "dist_km": dict(zip(NOMBRES, (round(x, 2) for x in _dist_media_km(city)), strict=True)),
        "theil": round(float(_theil(city.result.Q, np.asarray(city.S, dtype=float))), 3),
    }


def _lu_rho(rho: float) -> LandUseConfig:
    d = base._land_use_web().model_dump()
    for e in d["estratos"]:
        e["rho"] = rho
    return LandUseConfig.model_validate(d)


def suelo() -> dict:
    s0 = base._config_web()
    b = {h: s0.demand.estratos[h].betas.b_costo for h in ESTRATOS}
    city = _suelo(s0)
    # μ = 1: contrafactual, la constante del núcleo no se configura (schema v7).
    lu = base._land_use_web()
    assert city.result is not None
    T = T_flujo_libre(
        s0.demand,
        city.L,
        city.cbd_index,
        city.ancho_celda_km,
        s0.modos_habilitados,
        supply=s0.supply,
    )
    r_mu1 = solve_subasta(
        H=np.asarray(lu.H_por_estrato, dtype=int),
        S=city.S,
        y=np.asarray([e.y for e in lu.estratos], dtype=float),
        T=T,
        rho=np.asarray([e.rho for e in lu.estratos], dtype=float),
        lambda_h=lambda_desde_demanda(s0.demand),
        mu=1.0,
        tol=lu.tol,
        max_iter=lu.max_iter,
    )

    # Umbral de inversión de ρ (común a los tres): bisección sobre «el alto
    # vive más lejos que el bajo».
    def invertido(rho: float) -> bool:
        d = _dist_media_km(_suelo(s0, _lu_rho(rho)))
        return d[0] > d[2]

    lo, hi = 0.0, 54.0
    assert not invertido(lo) and invertido(hi)
    while hi - lo > 0.25:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if invertido(mid) else (mid, hi)

    return {
        "mu": round(lu.mu, 4),
        "base": _resumen_suelo(city),
        "lambda_iguales": _resumen_suelo(
            _suelo(_sim({f"demand.estratos.{h}.betas.b_costo": b[2] for h in (1, 3)}))
        ),
        "lambda_alto_doble": _resumen_suelo(
            _suelo(_sim({"demand.estratos.1.betas.b_costo": 2 * b[1]}))
        ),
        "lambda_alto_mitad": _resumen_suelo(
            _suelo(_sim({"demand.estratos.1.betas.b_costo": 0.5 * b[1]}))
        ),
        "theil_mu_1": round(float(_theil(r_mu1.Q, np.asarray(city.S, dtype=float))), 3),
        "rho_54": _resumen_suelo(_suelo(s0, _lu_rho(54.0))),
        "rho_umbral_inversion": round((lo + hi) / 2),
    }


def parametros() -> dict:
    sim = base._config_web()
    lu = base._land_use_web()
    H = lu.H_por_estrato
    return {
        "share_estratos_pct": {
            n: round(100.0 * h / sum(H)) for n, h in zip(NOMBRES, H, strict=True)
        },
        "ingreso_clp_mes": {n: e.y for n, e in zip(NOMBRES, lu.estratos, strict=True)},
        "hogares_por_km": sum(H) / sim.city.largo_ciudad_km,
        "tolerancia_msa_min": sim.tolerance,
        "max_iter": sim.max_iter,
        "max_iter_tope": next(
            m.le for m in SimulationConfig.model_fields["max_iter"].metadata if hasattr(m, "le")
        ),
        "tol_acoplado_clp_hogar_mes": TOL_ACOPLADO_CLP_MES,
        "vot_clp_hora": {
            n: round(vot_clp_hora(sim, h)) for n, h in zip(NOMBRES, ESTRATOS, strict=True)
        },
        "costo_parking": sim.demand.globales.costo_parking,
        "cap_bici": sim.supply.bike.capacidad_pista,
        "cap_bici_pro_bici": POLICY_PRESETS["Pro-Bici"]["cap_bici"],
    }


def main() -> None:
    datos = {
        "_meta": {
            "generado": datetime.now(UTC).strftime("%Y-%m-%d"),
            "commit": _commit(),
            "configuracion": "config de la app (test_linea_base._config_web/_land_use_web)",
        },
        "parametros": parametros(),
        "limite_del_logit": limite_del_logit(),
        "pistas": pistas(),
        "experimentos_transporte": experimentos_transporte(),
        "suelo": suelo(),
    }
    SALIDA.write_text(json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in datos.items() if k != "_meta"}, ensure_ascii=False)[:6000])


if __name__ == "__main__":
    main()
