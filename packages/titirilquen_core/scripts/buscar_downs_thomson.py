"""Busqueda SISTEMATICA de Downs-Thomson: escenarios x equilibrios x capacidad.

Que es la paradoja y que exige (derivado del modelo clasico de dos modos):
al expandir capacidad vial, usuarios migran del transporte publico al auto; si
el costo medio del transporte publico DECRECE con su patronato (economia de
escala: f_op = L_max/K => espera = 30K/L_max, elasticidad -1), la migracion lo
encarece y, si los usuarios arbitran hasta igualar costos, el costo comun del
equilibrio SUBE. Condiciones necesarias:

  C1. Ambos modos en uso (equilibrio interior) y sin terceros modos que
      absorban la sustitucion.
  C2. Arbitraje de costos: eleccion determinista (Wardrop). El logit deja al
      usuario del modo mejorado una ganancia sin arbitrar.
  C3. Decisores HOMOGENEOS: Wardrop iguala costos entre las alternativas de un
      decisor, no entre decisores. Estratos y distancias distintas rompen el
      arbitraje poblacional.
  C4. Frecuencia INTERIOR (ni f_min ni f_max mordiendo) y espera grande y
      sensible (K grande, f_op baja).
  C5. El diferencial de DINERO no puede dominar: no depende de la capacidad
      vial, asi que si decide la eleccion, las pistas no mueven a nadie.

El paper original (reference/overleaf_original/main.tex) usa logit multinomial
puro y NO menciona Downs-Thomson: la paradoja es un objetivo pedagogico del
proyecto, no una promesa de los autores.

Cada eje del disenio ataca un supuesto del modelo:
  - equilibrio: montecarlo / expected (logit) / wardrop  ....... ataca C2
  - poblacion: 3 estratos vs homogenea (todo = estrato medio) .. ataca C3
  - ciudad: normal vs bimodal concentrada (una sola distancia) . ataca C3
  - modos: 4 vs solo Auto+Metro ................................ ataca C1
  - dinero: calibrado vs cero (compiten solo por tiempo) ....... ataca C5
  - metro: K=300/f6 (default) vs K grande / f_min 1 / f_max 200  ataca C4
  - ASC: calibradas (auto +20) vs cero ......................... ataca C5

MEDIDA DE BIENESTAR (la leccion cara de esta busqueda): el tiempo fisico y el
costo tiempo+dinero dan FALSOS POSITIVOS por composicion. La medida correcta
depende del equilibrio, y ambas se convierten a minutos con /|b_tiempo_viaje|
(OJO signo: b_t < 0, utilidad mayor = bienestar mayor = MAS minutos de
bienestar; la paradoja es que el bienestar CAE al agregar pistas):
  - logit (mc/expected): logsum medio  E[ln sum e^V]
  - wardrop:             utilidad maxima media  E[max V]

DETECTOR: no basta el signo. Un tramo cuenta como paradoja solo si ademas el
mecanismo es el correcto: auto SUBE, metro BAJA, espera SUBE, y la fuga a
bici+caminata es menor que la mitad del alza del auto (el falso positivo ya
visto: el metro perdia pasajeros hacia la bici con el auto en 0%).

RESULTADO (ago-2026, verificado con max_iter=120 y tol=0.02): cero paradojas
bajo logit en los diez escenarios; ocho con mecanismo verificado bajo Wardrop.
En la CIUDAD REAL (3 estratos, 4 modos, calibracion vigente) aparece con
K=1000 y piso de frecuencia bajo: el bienestar cae monotonamente de 1 a 3
pistas (-0.63 min) y recien con ~6 recupera el punto de partida. En los
escenarios estilizados homogeneos toma la forma fuerte (espiral de muerte del
metro: participacion -> 0, espera -> 30/f_min, caidas de -10 a -33 min).
Detalle y receta de aula en docs/CONTINUAR.md, seccion Downs-Thomson.

Correr desde packages/titirilquen_core (demora varios minutos):

    uv run python scripts/buscar_downs_thomson.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from auditoria_transporte import base_sim

from titirilquen_core.city import CiudadLineal
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    TiemposObservados,
    iter_msa_desde_suelo,
)
from titirilquen_core.land_use import LandUseConfig

PISTAS = (1, 2, 4, 8)
MODOS = ("Auto", "Metro", "Bici", "Caminata")
ASC = ("asc_auto", "asc_metro", "asc_bici", "asc_caminata")
H_TOT = 36000.0


def lu_de(escenario: dict) -> LandUseConfig:
    forma = escenario.get("forma", "normal")
    kw = {}
    if forma == "bimodal":
        # Picos angostos a ~70% de la semi-ciudad: casi toda la poblacion a una
        # MISMA distancia del CBD (7 km en 20 km de ciudad). Es el analogo del
        # origen-destino unico del modelo clasico: caminata infactible, bici
        # castigada, y todos los decisores enfrentan los mismos costos.
        kw = {"oferta_sigma_frac": 0.2, "forma_param": 0.7}
    sh = (0.20, 0.50, 0.30)
    return LandUseConfig(H_por_estrato=[H_TOT * x for x in sh], forma=forma, **kw)


def config_de(escenario: dict, metodo: str, pistas: int):
    s = base_sim().model_copy(update={"assignment": metodo, "max_iter": 40})
    est = dict(s.demand.estratos)
    ref = est[2]
    for h in (1, 2, 3):
        c = est[h]
        upd: dict = {}
        if escenario.get("homogeneo"):
            b = ref.betas
            upd["betas"] = c.betas.model_copy(
                update={
                    campo: getattr(b, campo)
                    for campo in type(b).model_fields
                    if campo != "penalizaciones_fisicas"
                }
                | {"penalizaciones_fisicas": b.penalizaciones_fisicas}
            )
            upd["prob_teletrabajo"] = 0.2
        if escenario.get("asc_cero"):
            base_b = upd.get("betas", c.betas)
            upd["betas"] = base_b.model_copy(update=dict.fromkeys(ASC, 0.0))
        if "prob_auto" in escenario:
            upd["prob_auto"] = escenario["prob_auto"]
        est[h] = c.model_copy(update=upd)

    gl = s.demand.globales
    if escenario.get("dinero_cero"):
        gl = gl.model_copy(
            update={"costo_parking": 0.0, "costo_tarifa_metro": 0.0, "costo_combustible_km": 0.0}
        )

    # Sin override, cada campo cae al DEFAULT VIGENTE del core (no a un valor
    # congelado aca): asi el escenario {} siempre es la app tal cual esta.
    tr0 = s.supply.train
    train = tr0.model_copy(
        update={
            "capacidad_tren": escenario.get("k", tr0.capacidad_tren),
            "frec_min": escenario.get("fmin", tr0.frec_min),
            "frec_max": escenario.get("fmax", tr0.frec_max),
        }
    )
    upd_top: dict = {
        "demand": s.demand.model_copy(update={"estratos": est, "globales": gl}),
        "supply": s.supply.model_copy(
            update={
                "car": s.supply.car.model_copy(update={"num_pistas": pistas}),
                "train": train,
            }
        ),
    }
    if escenario.get("solo_am"):
        upd_top["modos_habilitados"] = ["Auto", "Metro"]
    return s.model_copy(update=upd_top)


def bienestar_min(sim, tr: ConvergenceTrace) -> tuple[float, float]:
    """(logsum medio, max medio) en minutos-equivalentes, ponderados por agente.

    Se recalculan las utilidades por grupo con los TIEMPOS FINALES, se pasa a
    minutos con /|b_tiempo_viaje| del estrato y se pondera por el tamanio del
    grupo. Positivo mayor = mejor. La paradoja es que CAE al agregar pistas.
    """
    last = tr.iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    tiempos = [
        TiemposObservados(
            auto_total=float(last.t_auto[i]),
            bici_total=float(last.t_bici[i]),
            tren_acceso=float(last.t_tren_acceso[i]),
            tren_espera=float(last.t_tren_espera[i]),
            tren_viaje=float(last.t_tren_viaje[i]),
        )
        for i in range(sim.city.n_celdas)
    ]
    grupos: dict[tuple, int] = {}
    for a in tr.agentes:
        if a.teletrabaja:
            continue
        k = (a.estrato, a.celda_origen, a.tiene_auto)
        grupos[k] = grupos.get(k, 0) + 1
    ls_num = mx_num = den = 0.0
    for (h, i, auto), n in grupos.items():
        u = calcular_utilidades(
            estrato=h,
            celda_origen=i,
            tiene_auto=auto,
            ciudad=ciudad,
            config=sim.demand,
            tiempos_observados=tiempos[i],
            modos_habilitados=sim.modos_habilitados,
        )
        vs = [u[m].valor for m in MODOS if m in u and u[m].feasible and np.isfinite(u[m].valor)]
        if not vs:
            continue
        b_t = abs(sim.demand.estratos[h].betas.b_tiempo_viaje)
        m = max(vs)
        ls = m + np.log(sum(np.exp(v - m) for v in vs))
        ls_num += n * ls / b_t
        mx_num += n * m / b_t
        den += n
    return ls_num / max(den, 1), mx_num / max(den, 1)


def corre(escenario: dict, metodo: str, pistas: int) -> dict:
    sim = config_de(escenario, metodo, pistas)
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu_de(escenario), tr, localizacion="equilibrio"):
        pass
    last = tr.iteraciones[-1]
    sp = last.modal_split
    tot = sum(sp.values()) or 1
    w_ls, w_mx = bienestar_min(sim, tr)
    return {
        "auto": 100 * sp.get("Auto", 0) / tot,
        "metro": 100 * sp.get("Metro", 0) / tot,
        "otros": 100 * (sp.get("Bici", 0) + sp.get("Caminata", 0)) / tot,
        "f_op": last.frecuencia_metro,
        "espera": float(last.t_tren_espera.max()),
        "vc": (
            float(tr.flujos_auto_veh_h.max()) / tr.capacidad_auto
            if tr.flujos_auto_veh_h is not None and tr.capacidad_auto
            else 0.0
        ),
        "w": w_mx if metodo == "todo_o_nada" else w_ls,
        "conv": tr.converged,
    }


ESCENARIOS: list[tuple[str, dict, tuple[str, ...]]] = [
    ("E01 base actual (4 modos, 3 estratos)", {}, ("montecarlo", "expected", "todo_o_nada")),
    (
        "E02 base, metro K=1000 f1/200",
        {"k": 1000, "fmin": 1, "fmax": 200},
        ("expected", "todo_o_nada"),
    ),
    (
        "E03 solo A+M, K=1000",
        {"solo_am": True, "k": 1000, "fmin": 1, "fmax": 200},
        ("expected", "todo_o_nada"),
    ),
    (
        "E04 homogenea, solo A+M, K=1000",
        {"homogeneo": True, "prob_auto": 1.0, "solo_am": True, "k": 1000, "fmin": 1, "fmax": 200},
        ("expected", "todo_o_nada"),
    ),
    (
        "E05 E04 + dinero cero",
        {
            "homogeneo": True,
            "prob_auto": 1.0,
            "solo_am": True,
            "dinero_cero": True,
            "k": 1000,
            "fmin": 1,
            "fmax": 200,
        },
        ("expected", "todo_o_nada"),
    ),
    (
        "E06 E05 + K=2500",
        {
            "homogeneo": True,
            "prob_auto": 1.0,
            "solo_am": True,
            "dinero_cero": True,
            "k": 2500,
            "fmin": 1,
            "fmax": 200,
        },
        ("expected", "todo_o_nada"),
    ),
    (
        "E07 bimodal concentrada + E05",
        {
            "forma": "bimodal",
            "homogeneo": True,
            "prob_auto": 1.0,
            "solo_am": True,
            "dinero_cero": True,
            "k": 1000,
            "fmin": 1,
            "fmax": 200,
        },
        ("expected", "todo_o_nada"),
    ),
    (
        "E08 bimodal + K=2500",
        {
            "forma": "bimodal",
            "homogeneo": True,
            "prob_auto": 1.0,
            "solo_am": True,
            "dinero_cero": True,
            "k": 2500,
            "fmin": 1,
            "fmax": 200,
        },
        ("expected", "todo_o_nada"),
    ),
    (
        "E09 E08 + ASC cero (clasico puro)",
        {
            "forma": "bimodal",
            "homogeneo": True,
            "asc_cero": True,
            "prob_auto": 1.0,
            "solo_am": True,
            "dinero_cero": True,
            "k": 2500,
            "fmin": 1,
            "fmax": 200,
        },
        ("expected", "todo_o_nada"),
    ),
    (
        "E10 E09 con cautivos (prob_auto .7)",
        {
            "forma": "bimodal",
            "homogeneo": True,
            "asc_cero": True,
            "prob_auto": 0.7,
            "solo_am": True,
            "dinero_cero": True,
            "k": 2500,
            "fmin": 1,
            "fmax": 200,
        },
        ("todo_o_nada",),
    ),
]


def main() -> None:
    veredictos = []
    for nombre, esc, metodos in ESCENARIOS:
        for metodo in metodos:
            print(f"\n### {nombre} · {metodo}")
            print(
                f"{'pistas':>7}{'auto':>8}{'metro':>8}{'otros':>8}{'f_op':>7}"
                f"{'espera':>8}{'v/c':>7}{'bienestar':>11}"
            )
            print("-" * 64)
            prev = None
            tramos = []
            for p in PISTAS:
                r = corre(esc, metodo, p)
                marca = ""
                if prev is not None:
                    d_w = r["w"] - prev["w"]
                    mecanismo = (
                        d_w < -0.01
                        and r["auto"] > prev["auto"] + 0.05
                        and r["metro"] < prev["metro"] - 0.05
                        and r["espera"] > prev["espera"]
                        and abs(r["otros"] - prev["otros"])
                        <= 0.5 * (r["auto"] - prev["auto"]) + 0.1
                    )
                    if mecanismo:
                        marca = f"  <<< PARADOJA ({d_w:+.3f} min)"
                        tramos.append((prev["p"], p, d_w))
                    elif d_w < -0.01:
                        marca = f"  (bienestar cae {d_w:+.3f} sin mecanismo)"
                print(
                    f"{p:>7}{r['auto']:>8.2f}{r['metro']:>8.2f}{r['otros']:>8.2f}"
                    f"{r['f_op']:>7.1f}{r['espera']:>8.2f}{r['vc']:>7.2f}{r['w']:>11.3f}{marca}"
                    + ("" if r["conv"] else "  [NO CONV]")
                )
                prev = {**r, "p": p}
            veredictos.append((nombre, metodo, tramos))

    print("\n" + "=" * 64)
    print("CONCLUSIONES")
    print("=" * 64)
    con = [v for v in veredictos if v[2]]
    if not con:
        print("Ningun escenario x metodo produce Downs-Thomson con mecanismo verificado.")
    for nombre, metodo, tramos in con:
        peor = min(tramos, key=lambda t: t[2])
        print(
            f"  {nombre} · {metodo}: paradoja en {len(tramos)} tramo(s); "
            f"peor {peor[0]}->{peor[1]} pistas ({peor[2]:+.3f} min)"
        )


if __name__ == "__main__":
    main()
