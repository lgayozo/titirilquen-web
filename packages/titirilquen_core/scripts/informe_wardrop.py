"""Genera los datos del informe de auditoria del metodo DETERMINISTICO.

Corre los experimentos y escribe `docs/_datos_informe/wardrop.json`, que consume
`docs/informe-wardrop.html`. Separado de `auditoria_wardrop.py` (que imprime en
consola para trabajar) porque este emite el dato estructurado del informe.

    uv run python scripts/informe_wardrop.py

Experimentos:

  1. BARRIDO DE PISTAS 1..6, con logit y con deterministico. Es la receta de
     Downs-Thomson de docs/CONTINUAR.md §5 y el contraste central del informe.
  2. ESTABILIDAD: cuantos grupos cambian de modo entre iteraciones consecutivas.
     En un equilibrio de verdad tiende a 0; si no baja, el punto final es un
     promedio de estados que siguen rotando (flip-flop), no un punto fijo.
  3. ESCALA DE LOS BETAS: multiplicar todas las utilidades por c lleva el logit
     al reparto deterministico. Verifica a nivel de SISTEMA lo que
     `test_es_el_limite_del_logit_al_escalar_las_utilidades` verifica en la
     funcion pura.
  4. SENSIBILIDAD AL CORTE: tolerancia x max_iter. Si el reparto depende de
     donde se corta, el residuo no esta yendo a cero.
"""

from __future__ import annotations

import json
from pathlib import Path

from _comun import base_lu, base_sim

from titirilquen_core.city import CiudadLineal
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo

SALIDA = Path(__file__).parent.parent.parent.parent / "docs" / "_datos_informe"
MODOS = ("Auto", "Metro", "Bici", "Caminata")


def corre(sim, promediar_flujos: bool = False) -> ConvergenceTrace:
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, base_lu(), tr, localizacion="equilibrio", promediar_flujos=promediar_flujos
    ):
        pass
    return tr


def _tiempos(snap, n) -> list[TiemposObservados]:
    return [
        TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        for i in range(n)
    ]


def _grupos(tr: ConvergenceTrace) -> dict[tuple, int]:
    pesos: dict[tuple, int] = {}
    for a in tr.agentes:
        if a.teletrabaja:
            continue
        k = (a.estrato, a.celda_origen, a.tiene_auto)
        pesos[k] = pesos.get(k, 0) + 1
    return pesos


def _mejor_por_grupo(tr: ConvergenceTrace, sim, snap) -> dict[tuple, tuple[str, float]]:
    """Modo de maxima utilidad de cada grupo con los tiempos de `snap`, y su
    costo generalizado en minutos-equivalentes."""
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    ts = _tiempos(snap, ciudad.n_celdas)
    out = {}
    for estrato, celda, tiene_auto in _grupos(tr):
        utils = calcular_utilidades(
            estrato=estrato,
            celda_origen=celda,
            tiene_auto=tiene_auto,
            ciudad=ciudad,
            config=sim.demand,
            tiempos_observados=ts[celda],
        )
        vivos = [(m, u.valor) for m, u in utils.items() if u.feasible]
        if not vivos:
            continue
        m, v = max(vivos, key=lambda t: t[1])
        b = sim.demand.estratos[estrato].betas.b_tiempo_viaje
        out[(estrato, celda, tiene_auto)] = (m, v / b)
    return out


def reparto(tr: ConvergenceTrace) -> dict:
    last = tr.iteraciones[-1]
    d = {
        "Auto": float(last.demanda_auto.sum()),
        "Metro": float(last.demanda_metro.sum()),
        "Bici": float(last.demanda_bici.sum()),
        "Caminata": float(last.demanda_caminata.sum()),
    }
    tot = sum(d.values()) or 1.0
    vc = (
        float(tr.flujos_auto_veh_h.max()) / tr.capacidad_auto
        if tr.flujos_auto_veh_h is not None and tr.capacidad_auto
        else 0.0
    )
    return {
        **{k: 100 * v / tot for k, v in d.items()},
        "vc": vc,
        "espera_metro": float(last.t_tren_espera.max()),
        "f_op": last.frecuencia_metro,
        "t_auto": float(last.t_auto.max()),
        "iters": len(tr.iteraciones),
        "residuo": last.residuo,
        "converged": tr.converged,
    }


def cg_medio(tr: ConvergenceTrace, sim) -> float:
    """Costo generalizado percibido medio (min-equiv), ponderado por agentes.
    Es la medida de bienestar EMPAREJADA con el deterministico: bajo logit la
    correcta es el logsum, y por eso el informe no compara niveles entre
    metodos, solo la DIRECCION dentro de cada uno."""
    pesos = _grupos(tr)
    mejores = _mejor_por_grupo(tr, sim, tr.iteraciones[-1])
    num = sum(mejores[k][1] * n for k, n in pesos.items() if k in mejores)
    den = sum(n for k, n in pesos.items() if k in mejores)
    return num / den if den else float("nan")


def barrido_pistas() -> list[dict]:
    filas = []
    for metodo in ("expected", "todo_o_nada"):
        for pistas in range(1, 7):
            sim = base_sim()
            sim.assignment = metodo
            sim.supply.car.num_pistas = pistas
            tr = corre(sim)
            filas.append(
                {"metodo": metodo, "pistas": pistas, **reparto(tr), "cg": cg_medio(tr, sim)}
            )
            print(f"  pistas={pistas} {metodo:9s} metro={filas[-1]['Metro']:.2f}")
    return filas


def estabilidad() -> list[dict]:
    """Cuantos grupos cambian de modo entre iteraciones consecutivas."""
    out = []
    for metodo in ("expected", "todo_o_nada"):
        sim = base_sim()
        sim.assignment = metodo
        sim.max_iter = 40
        sim.tolerance = 0.0  # sin corte: se ven las 40
        tr = corre(sim)
        pesos = _grupos(tr)
        total = sum(pesos.values())
        prev = None
        serie = []
        for snap in tr.iteraciones:
            act = _mejor_por_grupo(tr, sim, snap)
            if prev is not None:
                movidos = sum(n for k, n in pesos.items() if k in act and act[k][0] != prev[k][0])
                serie.append(
                    {
                        "iter": snap.iter,
                        "residuo": None if snap.residuo == float("inf") else snap.residuo,
                        "pct_cambian": 100 * movidos / total,
                    }
                )
            prev = act
        out.append({"metodo": metodo, "serie": serie})
        print(f"  estabilidad {metodo}: ultimo pct_cambian={serie[-1]['pct_cambian']:.2f}")
    return out


def _escala_en_sitio(obj, c: float) -> None:
    """Multiplica por `c` TODOS los terminos numericos de la utilidad, bajando a
    los sub-objetos.

    Bajar es imprescindible: `penalizaciones_fisicas` es un `PhysicalPenalties`
    anidado, y dejarlo sin escalar no re-escala el logit — cambia el MODELO,
    porque las penalizaciones quedan `c` veces mas debiles frente al resto. Un
    primer intento de este experimento tenia ese defecto y producia una falsa
    anomalia: el metro se alejaba del deterministico en vez de acercarse.
    """
    for campo in type(obj).model_fields:
        v = getattr(obj, campo)
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            setattr(obj, campo, v * c)
        elif hasattr(type(v), "model_fields"):
            _escala_en_sitio(v, c)


def escala_betas() -> list[dict]:
    """El logit tiende al deterministico cuando la escala de las utilidades
    crece: es el mismo limite que verifica
    `test_es_el_limite_del_logit_al_escalar_las_utilidades` en la funcion pura,
    pero medido sobre el EQUILIBRIO, donde ademas hay retroalimentacion."""
    ref = reparto(corre(_sim_wardrop()))
    filas = [{"escala": None, "metodo": "todo_o_nada", **ref}]
    for c in (1, 2, 5, 10, 20, 50):
        sim = base_sim()
        sim.assignment = "expected"
        # `max_iter` mas alto: al crecer `c` el reparto se vuelve casi
        # todo-o-nada y necesita tantas iteraciones como el deterministico.
        sim.max_iter = 60
        for est in sim.demand.estratos.values():
            _escala_en_sitio(est.betas, c)
        tr = corre(sim)
        r = reparto(tr)
        dist = max(abs(r[m] - ref[m]) for m in MODOS)
        filas.append({"escala": c, "metodo": "expected", **r, "dist_a_wardrop": dist})
        print(f"  escala x{c:<3d} dist a wardrop = {dist:.2f} pp")
    return filas


def _sim_wardrop():
    sim = base_sim()
    sim.assignment = "todo_o_nada"
    return sim


def sensibilidad_corte() -> list[dict]:
    filas = []
    for metodo in ("expected", "todo_o_nada"):
        for tol, mi in ((0.5, 20), (0.1, 20), (0.02, 60), (0.0, 60)):
            sim = base_sim()
            sim.assignment = metodo
            sim.tolerance = tol
            sim.max_iter = mi
            r = reparto(corre(sim))
            filas.append({"metodo": metodo, "tol": tol, "max_iter": mi, **r})
            print(f"  {metodo:9s} tol={tol:<5} iters={r['iters']:3d} metro={r['Metro']:.2f}")
    return filas


def esquemas_msa() -> list[dict]:
    filas = []
    for metodo in ("expected", "todo_o_nada", "montecarlo"):
        for flujos in (False, True):
            sim = base_sim()
            sim.assignment = metodo
            r = reparto(corre(sim, promediar_flujos=flujos))
            filas.append({"metodo": metodo, "esquema": "flujos" if flujos else "tiempos", **r})
    return filas


if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("1. barrido de pistas")
    pistas = barrido_pistas()
    print("2. estabilidad")
    estab = estabilidad()
    print("3. escala de betas")
    escala = escala_betas()
    print("4. sensibilidad al corte")
    corte = sensibilidad_corte()
    print("5. esquemas de MSA")
    esquemas = esquemas_msa()

    datos = {
        "_": "Generado por scripts/informe_wardrop.py. NO editar a mano.",
        "base": {
            "n_celdas": 201,
            "largo_km": 20,
            "densidad_hab_km": 1800,
            "poblacion": 36000,
            "seed": 42,
            "tolerance": 0.1,
            "max_iter": 20,
        },
        "barrido_pistas": pistas,
        "estabilidad": estab,
        "escala_betas": escala,
        "sensibilidad_corte": corte,
        "esquemas_msa": esquemas,
    }
    (SALIDA / "wardrop.json").write_text(
        json.dumps(datos, indent=1, default=float) + "\n", encoding="utf-8"
    )
    print(f"\nEscrito: {SALIDA / 'wardrop.json'}")
