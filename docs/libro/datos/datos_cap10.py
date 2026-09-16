"""Datos del capítulo 10 — Consistencia entre módulos.

Produce `cap10.json`. Cada capítulo auditó un módulo contra su teoría; éste
audita las COSTURAS: si el hogar que elige modo es el que puja por suelo y el
que se cuenta en el bienestar, si la población es una sola en todas las
páginas, si los tres loops entienden lo mismo por «convergió», y si lo que la
documentación canónica dice de la línea base sigue siendo verdad.

Ocho bloques:

1. `un_hogar_una_utilidad` — el mismo logsum en demanda, accesibilidad y
   bienestar; el mismo VoT en transporte y suelo.
2. `una_poblacion` — cuántos hogares, agentes y viajeros cuenta cada módulo
   sobre la misma corrida.
3. `cuatro_repartos` — el reparto modal según quién lo calcula y con qué
   denominador.
4. `baselines` — los «sin congestión» que conviven: arranque del MSA, red vacía
   y estado convergido.
5. `geometria` — el CBD y el ancho de celda según cada módulo, para varias
   grillas.
6. `convergencias` — los tres loops, sus residuos, unidades y tolerancias.
7. `linea_base` — lo que fija el test, lo que cita `CLAUDE.md` y lo que da hoy.
8. `documentacion` — cifras citadas en los documentos canónicos contra las
   actuales, y las claves i18n de los dos idiomas.

Correr desde `packages/titirilquen_core` (~1 min):

    uv run python ../../docs/libro/datos/datos_cap10.py
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
NUCLEO = RAIZ / "packages" / "titirilquen_core"
WEB = RAIZ / "apps" / "web"
sys.path.insert(0, str(NUCLEO / "tests"))

import test_linea_base as base
from titirilquen_core.bienestar import (
    calcular_agregados,
    medidas_de_utilidad,
    vot_clp_hora,
)
from titirilquen_core.city import CiudadLineal
from titirilquen_core.coupled import iter_coupled
from titirilquen_core.demand.choice import probabilidades_logit
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.accesibilidad import logsum_por_celda, tiempos_red_vacia
from titirilquen_core.land_use.config import LandUseConfig

SALIDA = Path(__file__).parent / "cap10.json"
NOMBRES = {1: "alto", 2: "medio", 3: "bajo"}


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


def _corre(localizacion: str = "equilibrio"):
    sim = base._config_web()
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, base._land_use_web(), tr, localizacion=localizacion
    ):
        pass
    return sim, tr


def _tiempos_snapshot(snap, i: int) -> TiemposObservados:
    return TiemposObservados(
        auto_total=float(snap.t_auto[i]),
        bici_total=float(snap.t_bici[i]),
        tren_acceso=float(snap.t_tren_acceso[i]),
        tren_espera=float(snap.t_tren_espera[i]),
        tren_viaje=float(snap.t_tren_viaje[i]),
    )


# ---------------------------------------------------------------------------
# 1. Un hogar, una utilidad
# ---------------------------------------------------------------------------


def un_hogar_una_utilidad() -> dict:
    """Tres módulos calculan «la utilidad esperada del viaje»: `demand/choice`
    (implícita en las probabilidades), `land_use/accesibilidad` y `bienestar`.
    Sobre la misma celda, el mismo estrato y los mismos tiempos tienen que dar
    el mismo número. Y el VoT del suelo (`α/λ`) tiene que ser el de transporte."""
    sim, tr = _corre()
    ciudad = CiudadLineal(
        n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km
    )
    snap = tr.iteraciones[-1]
    tiempos = [_tiempos_snapshot(snap, i) for i in range(ciudad.n_celdas)]
    ls_acc = logsum_por_celda(sim.demand, ciudad, tiempos)
    lu = LandUseConfig()
    filas = []
    for h in (1, 2, 3):
        for i in (60, 100 + 25, 180):
            u = calcular_utilidades(
                estrato=h,  # type: ignore[arg-type]
                celda_origen=i,
                tiene_auto=True,
                ciudad=ciudad,
                config=sim.demand,
                tiempos_observados=tiempos[i],
            )
            v = np.array([b.valor for b in u.values() if b.feasible])
            ls_demanda = float(np.log(np.exp(v).sum()))
            p = probabilidades_logit(u)
            # `choice` no expone el logsum: se recupera de sus probabilidades,
            # ln P_m = V_m − logsum ⇒ logsum = V_m − ln P_m para cualquier m.
            m0 = next(m for m, pr in p.items() if pr > 0)
            ls_desde_choice = float(u[m0].valor - np.log(p[m0]))
            par = medidas_de_utilidad(h, i, True, ciudad, sim, tiempos[i])  # type: ignore[arg-type]
            ls_bienestar = par[0] if par else float("nan")
            # accesibilidad pondera por prob_auto; con prob_auto=1 coincidiría.
            # Se compara contra la rama con auto recalculada con peso 1.
            dem1 = sim.demand.model_copy(deep=True)
            dem1.estratos[h].prob_auto = 1.0  # type: ignore[index]
            ls_acc_con_auto = float(logsum_por_celda(dem1, ciudad, tiempos)[h - 1, i])
            filas.append(
                {
                    "estrato": NOMBRES[h],
                    "celda": i,
                    "logsum_demanda": round(ls_demanda, 9),
                    "logsum_desde_choice": round(ls_desde_choice, 9),
                    "logsum_bienestar": round(ls_bienestar, 9),
                    "logsum_accesibilidad_con_auto": round(ls_acc_con_auto, 9),
                    "coinciden": max(
                        abs(ls_demanda - ls_desde_choice),
                        abs(ls_demanda - ls_bienestar),
                        abs(ls_demanda - ls_acc_con_auto),
                    )
                    < 1e-9,
                }
            )
    vot = {}
    for h in (1, 2, 3):
        e = lu.estratos[h - 1]
        vt = vot_clp_hora(sim, h)  # type: ignore[arg-type]
        vs = e.alpha / e.lambda_ * abs(sim.demand.estratos[h].betas.b_tiempo_viaje) * 60  # type: ignore[index]
        vot[NOMBRES[h]] = {
            "transporte_clp_hora": round(vt, 3),
            "suelo_alpha_sobre_lambda_clp_hora": round(vs, 3),
            "iguales": abs(vt - vs) < 1e-6,
        }
    return {
        "filas": filas,
        "todas_coinciden": all(f["coinciden"] for f in filas),
        "vot": vot,
        "logsum_accesibilidad_pondera_por_prob_auto": {
            "estrato_medio_celda_125_ponderado": round(float(ls_acc[1, 125]), 6),
            "nota": "La accesibilidad es la esperanza sobre la tenencia de auto; el "
            "bienestar la calcula por rama y la mezcla con `prob_auto` aparte.",
        },
    }


# ---------------------------------------------------------------------------
# 2. Una población
# ---------------------------------------------------------------------------


def una_poblacion() -> dict:
    sim, tr = _corre("equilibrio")
    a = calcular_agregados(sim, tr)
    assert a is not None and tr.demanda_estrato is not None
    agentes = tr.agentes
    it0 = next(
        iter(
            iter_coupled(
                sim=sim,
                land_use_config=base._land_use_web(),
                outer_max_iter=1,
                outer_tol=1.0,
            )
        )
    )
    m = it0.metrics
    return {
        "hogares_H": int(sum(base._land_use_web().H_por_estrato)),
        "agentes_transporte": len(agentes),
        "teletrabajan": sum(1 for x in agentes if x.teletrabaja),
        "varados": sum(
            1 for x in agentes if not x.teletrabaja and x.modo_elegido is None
        ),
        "con_modo_elegido": sum(1 for x in agentes if x.modo_elegido is not None),
        "viajan_segun_agentes": sum(
            1 for x in agentes if not x.teletrabaja and x.modo_elegido is not None
        ),
        "tienen_auto": sum(1 for x in agentes if x.tiene_auto),
        "viajeros_segun_agregados": round(float(a["viajeros"]), 3),
        "viajeros_segun_demanda_estrato": round(float(tr.demanda_estrato.sum()), 3),
        "viajeros_segun_coupled_metrics": int(sum(e.n_viajeros for e in m.por_estrato)),
        "hogares_segun_coupled_metrics": round(
            float(sum(e.n_hogares for e in m.por_estrato)), 3
        ),
        "agentes_segun_coupled": len(it0.transport.agentes),
        "teletrabajan_segun_coupled": sum(
            1 for x in it0.transport.agentes if x.teletrabaja
        ),
        "tienen_auto_segun_coupled": sum(
            1 for x in it0.transport.agentes if x.tiene_auto
        ),
        "misma_realizacion_de_poblacion": [
            (x.estrato, x.celda_origen, x.teletrabaja, x.tiene_auto) for x in agentes
        ]
        == [
            (x.estrato, x.celda_origen, x.teletrabaja, x.tiene_auto)
            for x in it0.transport.agentes
        ],
        "nota": (
            "`viajeros` de los agregados y `demanda_estrato` son la demanda ESPERADA "
            "(probabilidades × agentes); los conteos de agentes son la realización "
            "con `assignment = expected`, donde cada agente que viaja cuenta 1."
        ),
    }


# ---------------------------------------------------------------------------
# 3. Cuatro repartos
# ---------------------------------------------------------------------------


def cuatro_repartos() -> dict:
    sim, tr = _corre("equilibrio")
    a = calcular_agregados(sim, tr)
    assert a is not None
    snap = tr.iteraciones[-1]
    it0 = next(
        iter(
            iter_coupled(
                sim=sim,
                land_use_config=base._land_use_web(),
                outer_max_iter=1,
                outer_tol=1.0,
            )
        )
    )
    s = snap.modal_split
    tot = sum(s.values())
    snapshot = {k: round(100.0 * v / tot, 3) for k, v in s.items()}
    agreg = {
        k: round(100.0 * v / a["viajeros"], 3) for k, v in a["viajes_por_modo"].items()
    }
    coupled = {
        k: round(100.0 * v, 3) for k, v in it0.metrics.sistema.reparto_modal.items()
    }
    # El snapshot de la MISMA corrida del acoplado, contado con la regla del MSA.
    sc = it0.transport.iteraciones[-1].modal_split
    tc = sum(sc.values())
    snapshot_coupled = {k: round(100.0 * v / tc, 3) for k, v in sc.items()}
    # Reconciliación: el snapshot sin teletrabajo, para compararlo con agregados.
    tot_v = sum(v for k, v in s.items() if k != "Teletrabajo")
    snapshot_sin_tt = {
        k: round(100.0 * v / tot_v, 3) for k, v in s.items() if k != "Teletrabajo"
    }
    modos = ("Auto", "Metro", "Bici", "Caminata")
    return {
        "snapshot_modal_split (agentes, con teletrabajo)": snapshot,
        "agregados_viajes_por_modo (demanda esperada, sin teletrabajo)": agreg,
        "coupled_reparto_modal (agentes, con teletrabajo y varado)": coupled,
        "snapshot_sin_teletrabajo": snapshot_sin_tt,
        "snapshot_de_la_corrida_del_acoplado": snapshot_coupled,
        "brecha_dentro_de_la_misma_corrida_pp": round(
            max(abs(snapshot_coupled.get(k, 0) - coupled.get(k, 0)) for k in modos), 3
        ),
        "brecha_entre_corridas_mismo_conteo_pp": round(
            max(abs(snapshot.get(k, 0) - snapshot_coupled.get(k, 0)) for k in modos), 3
        ),
        "brecha_snapshot_vs_coupled_pp": round(
            max(abs(snapshot.get(k, 0) - coupled.get(k, 0)) for k in modos), 3
        ),
        "brecha_esperado_vs_realizado_pp": round(
            max(abs(agreg[k] - snapshot_sin_tt[k]) for k in modos), 3
        ),
        "nota": (
            "Dos denominadores (con y sin teletrabajo) y dos numeradores (demanda "
            "esperada vs agentes realizados): cuatro repartos legítimos para la "
            "misma corrida, y ninguna tabla dice cuál usa."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Baselines
# ---------------------------------------------------------------------------


def baselines() -> dict:
    """El MSA arranca de un «flujo libre» ingenuo (`demand/utility.py::_tiempos_flujo_libre`:
    velocidades globales, 10 min de acceso y 5 de espera fijos); la accesibilidad
    del suelo y el ΔCS usan la red VACÍA configurada. Se miden ambos contra el
    estado convergido, celda a celda."""
    sim, tr = _corre("equilibrio")
    ciudad = CiudadLineal(
        n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km
    )
    gl = sim.demand.globales
    vacia = tiempos_red_vacia(sim, ciudad)
    snap = tr.iteraciones[-1]
    comp = {
        "auto_total": [],
        "bici_total": [],
        "tren_acceso": [],
        "tren_espera": [],
        "tren_viaje": [],
    }
    for i in range(ciudad.n_celdas):
        d = abs(ciudad.cbd_index - i) * ciudad.ancho_celda_km
        # Reconstrucción literal de `_tiempos_flujo_libre` (utility.py).
        ingenuo = TiemposObservados(
            auto_total=d / gl.v_auto * 60,
            bici_total=d / gl.v_bici * 60,
            tren_acceso=10.0,
            tren_espera=5.0,
            tren_viaje=d / gl.v_metro * 60,
        )
        v = vacia[i]
        c = _tiempos_snapshot(snap, i)
        for k, lista in comp.items():
            lista.append((getattr(ingenuo, k), getattr(v, k), getattr(c, k)))
    out = {}
    for k, filas in comp.items():
        arr = np.array(filas)
        out[k] = {
            "max_abs_ingenuo_vs_vacia_min": round(
                float(np.max(np.abs(arr[:, 0] - arr[:, 1]))), 3
            ),
            "max_abs_vacia_vs_convergido_min": round(
                float(np.max(np.abs(arr[:, 1] - arr[:, 2]))), 3
            ),
            "media_ingenuo_min": round(float(arr[:, 0].mean()), 3),
            "media_vacia_min": round(float(arr[:, 1].mean()), 3),
            "media_convergido_min": round(float(arr[:, 2].mean()), 3),
        }
    s0 = tr.iteraciones[0].modal_split
    t0 = sum(s0.values())
    sf = snap.modal_split
    tf = sum(sf.values())
    return {
        "por_componente": out,
        "reparto_iteracion_0_pct": {k: round(100.0 * v / t0, 3) for k, v in s0.items()},
        "reparto_final_pct": {k: round(100.0 * v / tf, 3) for k, v in sf.items()},
        "iteraciones": len(tr.iteraciones),
        "nota": (
            "D-30 documenta tres baselines; desde D-34/D-42 son dos: el arranque "
            "ingenuo del MSA y la red vacía, que sirve tanto al ΔCS como al suelo. "
            "La fila «arranque del acoplado en minutos a v_auto» de D-30 ya no "
            "describe el código."
        ),
    }


# ---------------------------------------------------------------------------
# 5. Geometría
# ---------------------------------------------------------------------------


def geometria() -> dict:
    filas = []
    for n in (51, 101, 201, 401, 801):
        sim = base._config_web().model_copy(
            update={"city": base._config_web().city.model_copy(update={"n_celdas": n})}
        )
        ciudad = CiudadLineal(n_celdas=n, largo_total_km=sim.city.largo_ciudad_km)
        tr = ConvergenceTrace()
        for _ in iter_msa_desde_suelo(
            sim, base._land_use_web(), tr, localizacion="original"
        ):
            pass
        snap = tr.iteraciones[-1]
        filas.append(
            {
                "n_celdas": n,
                "cbd_CiudadLineal": ciudad.cbd_index,
                "cbd_coupled (L//2)": n // 2,
                "cbd_segun_t_auto_minimo": int(np.argmin(snap.t_auto)),
                "cbd_segun_t_bici_minimo": int(np.argmin(snap.t_bici)),
                "ancho_celda_km": round(ciudad.ancho_celda_km, 6),
                "agentes": len(tr.agentes),
                "coinciden": ciudad.cbd_index
                == n // 2
                == int(np.argmin(snap.t_auto))
                == int(np.argmin(snap.t_bici)),
            }
        )
    return {"filas": filas, "todas_coinciden": all(f["coinciden"] for f in filas)}


# ---------------------------------------------------------------------------
# 6. Convergencias
# ---------------------------------------------------------------------------


def convergencias() -> dict:
    from titirilquen_core.config import SimulationConfig

    sim_core_tol = SimulationConfig.model_fields["tolerance"].default
    lu_tol = LandUseConfig().tol
    outer_tol = inspect.signature(iter_coupled).parameters["outer_tol"].default
    pagina = (WEB / "src" / "pages" / "CoupledPage.tsx").read_text(encoding="utf-8")
    m = re.search(r"outer_tol:\s*([\d.]+)", pagina)
    return {
        "loops": [
            {
                "loop": "MSA de transporte",
                "residuo": "max|t_n − t_{n−1}| del iterado AMORTIGUADO",
                "unidad": "minutos",
                "tolerancia_default": sim_core_tol,
                "tolerancia_app": base._config_web().tolerance,
                "brecha_honesta_publicada": "gap_final_min (D-39), sin lector en la UI (D-63)",
            },
            {
                "loop": "subasta de suelo",
                "residuo": "max|ū_n − ū_{n−1}| del punto fijo de utilidades de reserva",
                "unidad": "útiles del suelo",
                "tolerancia_default": lu_tol,
                "tolerancia_app": base._land_use_web().tol,
                "brecha_honesta_publicada": "balance Σ S_i Q_hi = H_h no exigido (cap. 5)",
            },
            {
                "loop": "acoplado suelo ↔ transporte",
                "residuo": "‖F(T_state) − T_state‖∞ (rezago del promedio, D-53)",
                "unidad": "útiles de transporte por mes",
                "tolerancia_default": outer_tol,
                "tolerancia_app": float(m.group(1)) if m else None,
                "brecha_honesta_publicada": "ninguna",
            },
        ],
        "convergio_compuesto_en_el_nucleo": "residual exterior ∧ MSA ∧ subasta (D-39)",
        "convergio_en_el_frontend_motor_local": "sólo residual < outer_tol (D-55)",
    }


# ---------------------------------------------------------------------------
# 7. Línea base
# ---------------------------------------------------------------------------


def linea_base() -> dict:
    claude = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    cuad = re.findall(
        r"auto (\d+,\d+) · metro (\d+,\d+) · bici (\d+,\d+) · caminata (\d+,\d+)",
        claude,
    )
    cuad2 = re.findall(r"\*\*(\d+,\d+) · (\d+,\d+) · (\d+,\d+) · (\d+,\d+)\*\*", claude)
    citado = {}
    if cuad:
        citado["original"] = [float(x.replace(",", ".")) for x in cuad[0]]
    if cuad2:
        citado["equilibrio"] = [float(x.replace(",", ".")) for x in cuad2[0]]
    modos = ("Auto", "Metro", "Bici", "Caminata")
    out = {"citado_en_CLAUDE_md": citado, "ramas": {}}
    for rama in ("original", "equilibrio"):
        pct, n_iter, conv = base._corre(rama)
        medido = [round(pct[m], 2) for m in modos]
        fijado = [base.ESPERADO[rama][m] for m in modos]
        cit = citado.get(rama)
        out["ramas"][rama] = {
            "fijado_en_test_linea_base": fijado,
            "medido_hoy": medido,
            "iteraciones": n_iter,
            "convergio": conv,
            "test_vs_medido_max_pp": round(
                max(abs(a - b) for a, b in zip(fijado, medido, strict=True)), 3
            ),
            "CLAUDE_md_vs_test_max_pp": None
            if cit is None
            else round(max(abs(a - b) for a, b in zip(cit, fijado, strict=True)), 3),
        }
    return out


# ---------------------------------------------------------------------------
# 8. Documentación
# ---------------------------------------------------------------------------


def _claves(d, prefijo: str = "") -> set[str]:
    out = set()
    for k, v in d.items():
        r = f"{prefijo}{k}"
        if isinstance(v, dict):
            out |= _claves(v, r + ".")
        else:
            out.add(r)
    return out


def documentacion() -> dict:
    claude = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    m_core = re.search(r"#\s*(\d+) tests del núcleo", claude)
    m_e2e = re.search(r"#\s*(\d+) e2e", claude)
    col = subprocess.run(
        ["uv", "run", "--extra", "dev", "pytest", "--collect-only", "-q"],
        cwd=NUCLEO,
        capture_output=True,
        text=True,
        check=False,
    )
    m_n = re.search(r"(\d+) tests? collected", col.stdout + col.stderr)
    try:
        pw = subprocess.run(
            ["npx", "playwright", "test", "--list"],
            cwd=WEB,
            capture_output=True,
            text=True,
            check=False,
        )
        m_pw = re.search(r"Total:\s*(\d+) tests?", pw.stdout + pw.stderr)
        e2e_hoy = int(m_pw.group(1)) if m_pw else None
    except Exception:  # noqa: BLE001
        e2e_hoy = None
    disc = (RAIZ / "docs" / "DISCREPANCIES.md").read_text(encoding="utf-8")
    i18n = {}
    for archivo in ("simulator.json", "common.json"):
        es = _claves(
            json.loads(
                (WEB / "src" / "i18n" / "locales" / "es" / archivo).read_text(
                    encoding="utf-8"
                )
            )
        )
        en = _claves(
            json.loads(
                (WEB / "src" / "i18n" / "locales" / "en" / archivo).read_text(
                    encoding="utf-8"
                )
            )
        )
        i18n[archivo] = {
            "claves_es": len(es),
            "claves_en": len(en),
            "solo_en_es": sorted(es - en),
            "solo_en_en": sorted(en - es),
        }
    return {
        "tests_nucleo": {
            "citados_en_CLAUDE_md": int(m_core.group(1)) if m_core else None,
            "recolectados_hoy": int(m_n.group(1)) if m_n else None,
        },
        "tests_e2e": {
            "citados_en_CLAUDE_md": int(m_e2e.group(1)) if m_e2e else None,
            "listados_hoy": e2e_hoy,
        },
        "discrepancias_registradas": len(re.findall(r"^## D-\d+", disc, re.MULTILINE)),
        "i18n": i18n,
    }


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap10.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web` y `_land_use_web`), "
                "rama «equilibrio» salvo donde se indica; el acoplado con una vuelta."
            ),
        },
        "un_hogar_una_utilidad": un_hogar_una_utilidad(),
        "una_poblacion": una_poblacion(),
        "cuatro_repartos": cuatro_repartos(),
        "baselines": baselines(),
        "geometria": geometria(),
        "convergencias": convergencias(),
        "linea_base": linea_base(),
        "documentacion": documentacion(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    u = datos["un_hogar_una_utilidad"]
    print(
        f"Un hogar, una utilidad: logsums coinciden en las 9 celdas: {u['todas_coinciden']}"
    )
    for n, v in u["vot"].items():
        print(
            f"  VoT {n:<6} transporte {v['transporte_clp_hora']:>9} · suelo {v['suelo_alpha_sobre_lambda_clp_hora']:>9} · {v['iguales']}"
        )
    p = datos["una_poblacion"]
    print("\nUna población:", {k: v for k, v in p.items() if k != "nota"})
    r = datos["cuatro_repartos"]
    print("\nCuatro repartos:")
    for k, v in r.items():
        if isinstance(v, dict):
            print(f"  {k}: {v}")
    print(
        f"  brecha snapshot vs coupled {r['brecha_snapshot_vs_coupled_pp']} pp · esperado vs realizado {r['brecha_esperado_vs_realizado_pp']} pp"
    )
    b = datos["baselines"]
    print("\nBaselines (max |Δ| min):")
    for k, v in b["por_componente"].items():
        print(
            f"  {k:<12} ingenuo↔vacía {v['max_abs_ingenuo_vs_vacia_min']:>7} · vacía↔convergido {v['max_abs_vacia_vs_convergido_min']:>7}"
        )
    print(
        f"  reparto it0 {b['reparto_iteracion_0_pct']} → final {b['reparto_final_pct']}"
    )
    print(f"\nGeometría: todas coinciden: {datos['geometria']['todas_coinciden']}")
    lb = datos["linea_base"]
    print(f"\nLínea base citada en CLAUDE.md: {lb['citado_en_CLAUDE_md']}")
    for rama, v in lb["ramas"].items():
        print(
            f"  {rama}: test {v['fijado_en_test_linea_base']} · hoy {v['medido_hoy']} · CLAUDE−test {v['CLAUDE_md_vs_test_max_pp']} pp"
        )
    d = datos["documentacion"]
    print(
        f"\nDocumentación: tests núcleo {d['tests_nucleo']} · e2e {d['tests_e2e']} · D registradas {d['discrepancias_registradas']}"
    )
    for a, v in d["i18n"].items():
        print(
            f"  i18n {a}: es {v['claves_es']} en {v['claves_en']} · sólo es {v['solo_en_es']} · sólo en {v['solo_en_en']}"
        )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
