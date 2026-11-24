"""¿Se ven Downs-Thomson y Braess en este modelo?

BRAESS exige elección de RUTA: agregar un enlace reencamina el equilibrio y
empeora a todos. Este modelo es un corredor lineal monocentrico — todos viajan
de su celda al CBD por el unico corredor, sin rutas alternativas. Braess NO
puede aparecer, y no es una limitacion de calibracion sino de topologia.

DOWNS-THOMSON si es posible, porque la frecuencia del metro es ENDOGENA:

    f_op = carga / K   =>   espera = 30/f_op = 30·K/carga

o sea la espera es HIPERBOLICA en la carga. Ampliar la via atrae usuarios del
metro, el metro pierde carga, baja la frecuencia, sube la espera, y eso empuja a
mas gente al auto. Si ese lazo es fuerte, agregar pistas puede empeorar el
tiempo medio del SISTEMA aunque mejore el del auto.

La sensibilidad del lazo es d(espera)/d(carga) = -30·K/carga^2, asi que crece
con K: trenes mas grandes (y por lo tanto menos frecuentes) hacen el efecto mas
violento. Este barrido busca la region de parametros donde se ve.

Correr desde packages/titirilquen_core:

    uv run python scripts/paradojas.py
"""

from __future__ import annotations

import numpy as np
from _comun import base_lu, base_sim

from titirilquen_core.config import SimulationConfig
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo


def agregados(sim: SimulationConfig) -> dict:
    """Corre el equilibrio y devuelve agregados de CIUDAD COMPLETA.

    `tiempo_total_min` son persona-minutos de todos los viajeros; `t_medio` es
    el tiempo por viajero. Son las cifras que faltan en la tabla de resultados:
    hoy solo se muestran maximos y promedios por modo, que no permiten decir si
    una politica mejora al SISTEMA.
    """
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, base_lu(), tr, localizacion="equilibrio"):
        pass
    s = tr.iteraciones[-1]

    n = sim.city.n_celdas
    cbd = n // 2
    dx = sim.city.largo_ciudad_km / n
    dist = np.abs(np.arange(n) - cbd) * dx
    t_cam = dist / sim.demand.globales.v_caminata * 60

    t_metro = s.t_tren_acceso + s.t_tren_espera + s.t_tren_viaje
    pares = [
        (s.demanda_auto, s.t_auto),
        (s.demanda_metro, t_metro),
        (s.demanda_bici, s.t_bici),
        (s.demanda_caminata, t_cam),
    ]
    total_min = float(sum((d * t).sum() for d, t in pares))
    viajeros = float(sum(d.sum() for d, _ in pares))

    split = s.modal_split
    tot_split = sum(split.values()) or 1
    return {
        "t_total": total_min,
        "t_medio": total_min / max(viajeros, 1),
        "auto": 100 * split.get("Auto", 0) / tot_split,
        "metro": 100 * split.get("Metro", 0) / tot_split,
        "f_op": s.frecuencia_metro,
        "espera": float(s.t_tren_espera.max()),
        "vc": (
            float(tr.flujos_auto_veh_h.max()) / tr.capacidad_auto
            if tr.flujos_auto_veh_h is not None and tr.capacidad_auto
            else 0.0
        ),
    }


def con(
    sim: SimulationConfig,
    *,
    pistas=None,
    k=None,
    fmin=None,
    fmax=None,
    solo_am=False,
    parking=None,
    espera_x=None,
):
    car = sim.supply.car.model_copy(update={"num_pistas": pistas} if pistas else {})
    upd = {}
    if k is not None:
        upd["capacidad_tren"] = k
    if fmin is not None:
        upd["frec_min"] = fmin
    if fmax is not None:
        upd["frec_max"] = fmax
    train = sim.supply.train.model_copy(update=upd)
    out = sim.model_copy(
        update={"supply": sim.supply.model_copy(update={"car": car, "train": train})}
    )
    if solo_am:
        # Escenario estilizado: sin bici ni caminata, toda la sustitucion ocurre
        # entre auto y metro — que es lo que exige el lazo de Downs-Thomson.
        out = out.model_copy(update={"modos_habilitados": ["Auto", "Metro"]})
    if espera_x is not None:
        # Reescala b_tiempo_espera a `espera_x` veces b_tiempo_viaje. La espera
        # es el UNICO canal por el que el metro se degrada al perder pasajeros,
        # asi que su ponderacion decide si el lazo de Downs-Thomson tiene fuerza.
        estratos = {}
        for h, cfg in out.demand.estratos.items():
            b = cfg.betas
            estratos[h] = cfg.model_copy(
                update={
                    "betas": b.model_copy(update={"b_tiempo_espera": b.b_tiempo_viaje * espera_x})
                }
            )
        out = out.model_copy(
            update={"demand": out.demand.model_copy(update={"estratos": estratos})}
        )
    if parking is not None:
        out = out.model_copy(
            update={
                "demand": out.demand.model_copy(
                    update={
                        "globales": out.demand.globales.model_copy(
                            update={"costo_parking": parking}
                        )
                    }
                )
            }
        )
    return out


def barrido(titulo: str, **kw) -> None:
    print(f"\n### {titulo}")
    print(
        f"{'pistas':<8} {'auto%':>7} {'metro%':>7} {'f_op':>6} {'espera':>7} "
        f"{'v/c':>6} {'t_medio':>8} {'t_total':>12}"
    )
    print("-" * 72)
    peor = None
    base_t = None
    for p in (1, 2, 3, 4, 6, 10):
        r = agregados(con(base_sim(), pistas=p, **kw))
        if base_t is None:
            base_t = r["t_medio"]
        marca = ""
        if peor is not None and r["t_medio"] > peor + 1e-9:
            marca = "  <== EMPEORA al agregar pistas"
        peor = r["t_medio"]
        print(
            f"{p:<8} {r['auto']:>7.2f} {r['metro']:>7.2f} {r['f_op']:>6.1f} "
            f"{r['espera']:>7.2f} {r['vc']:>6.2f} {r['t_medio']:>8.2f} "
            f"{r['t_total']:>12,.0f}{marca}"
        )


def main() -> None:
    print("PARADOJAS — Downs-Thomson y Braess")
    print("Braess: IMPOSIBLE por topologia (corredor unico, sin eleccion de ruta).")
    print("Downs-Thomson: posible via frecuencia endogena. Se busca donde se ve.")

    barrido("A. Calibracion actual (K=300, frec 6-40)")
    barrido("B. Trenes grandes: K=1500 (frecuencia baja y muy sensible)", k=1500)
    barrido("C. K=1500 y sin piso de frecuencia (frec_min=0.5)", k=1500, fmin=0.5)
    barrido("D. K=3000 y sin piso (lazo maximo)", k=3000, fmin=0.5)
    barrido(
        "E. Estilizado Auto vs Metro (sin bici ni caminata), K=1500", k=1500, fmin=0.5, solo_am=True
    )
    barrido(
        "F. Estilizado + auto barato (parking 0) + K=3000: lazo maximo posible",
        k=3000,
        fmin=0.5,
        solo_am=True,
        parking=0,
    )
    # ¿Y si la espera se valora como manda la evidencia (~2x el tiempo en
    # vehiculo) en vez de ~0.7-1.0x como esta hoy?
    for x in (2.0, 4.0):
        barrido(
            f"G. Espera x{x} el tiempo en vehiculo (K=1500, estilizado)",
            k=1500,
            fmin=0.5,
            solo_am=True,
            espera_x=x,
        )
    barrido(
        "H. Espera x4 + K=3000 + parking 0 (lazo maximo)",
        k=3000,
        fmin=0.5,
        solo_am=True,
        parking=0,
        espera_x=4.0,
    )


if __name__ == "__main__":
    main()
