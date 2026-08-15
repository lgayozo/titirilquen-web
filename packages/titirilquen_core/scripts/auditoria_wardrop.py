"""Audita el equilibrio bajo `assignment="wardrop"` contra la definicion formal.

La pregunta la instala el docstring de `probabilidades_wardrop`, que afirma:
"el punto fijo es un equilibrio de Wardrop: todo modo usado termina con el mismo
costo generalizado". La definicion formal (Boyles, Lownes & Unnikrishnan,
"Transportation Network Analysis", Corollary 4.1, p. 89) dice:

    Every used route connecting an origin and destination has equal and minimal
    travel time.

y aclara que rutas usadas de pares origen-destino DISTINTOS pueden tener tiempos
distintos. Acá cada celda es un origen distinto y cada estrato una clase de
usuario distinta, asi que la afirmacion del docstring solo valdria si el
arbitraje fuera poblacional. Este script lo mide, en cuatro cortes mas una
comparacion de esquemas de promediado del MSA:

  A. Dispersion del costo generalizado del modo elegido ENTRE grupos. Si el
     arbitraje fuera poblacional, seria ~0.
  B. Costo generalizado medio por modo elegido. Si los modos "usados" se
     igualaran, las filas coincidirian.
  C. Brecha entre el modo elegido y el segundo mejor, DENTRO de cada grupo. Mide
     si el equilibrio es interior (brecha ~0, la condicion de Corollary 4.1
     mordiendo) o de esquina (brecha grande, la condicion satisfecha al vacio
     por tener una sola alternativa usada — el caso de la p. 92 del libro).
  D. PODER DE MERCADO: cuanto encarece el modo destino si un grupo se muda
     ENTERO, contra la brecha que tendria que cerrar. Es el termino que en el
     ejemplo del libro (p. 91) hace que `t1(h1) = t2(7000−h1)` tenga solucion
     interior. Responde por que no se igualan costos dentro de un par OD.

Y `compara_msa()` corre los tres metodos con los dos esquemas de promediado
(tiempos, el actual; flujos, el estandar) para ver si el punto fijo cambia.

Unidad: minutos-equivalentes, `utiles / b_tiempo_viaje`, la misma convencion de
`diagnostico_calibracion.py` (b_tiempo_viaje es negativo, asi que un costo sale
positivo).

Correr desde packages/titirilquen_core:

    uv run python scripts/auditoria_wardrop.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from auditoria_transporte import base_lu, base_sim

from titirilquen_core.city import CiudadLineal
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.supply.bike import demora_bici_tramo
from titirilquen_core.supply.car import demora_auto_tramo
from titirilquen_core.supply.train import oferta_tren

MODOS = ("Auto", "Metro", "Bici", "Caminata")


def corre(assignment: str, promediar_flujos: bool = False) -> tuple[ConvergenceTrace, object]:
    sim = base_sim()
    sim.assignment = assignment
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, base_lu(), tr, localizacion="equilibrio", promediar_flujos=promediar_flujos
    ):
        pass
    return tr, sim


def resumen(tr: ConvergenceTrace) -> dict:
    """Reparto modal y diagnostico del equilibrio, leidos de la demanda que
    efectivamente se le paso a la oferta (bajo `promediar_flujos` esa es la
    promediada, que es la magnitud comparable entre los dos esquemas)."""
    last = tr.iteraciones[-1]
    d = {
        "Auto": float(last.demanda_auto.sum()),
        "Metro": float(last.demanda_metro.sum()),
        "Bici": float(last.demanda_bici.sum()),
        "Caminata": float(last.demanda_caminata.sum()),
    }
    total = sum(d.values()) or 1.0
    vc = (
        float(tr.flujos_auto_veh_h.max()) / tr.capacidad_auto
        if tr.flujos_auto_veh_h is not None and tr.capacidad_auto
        else 0.0
    )
    return {
        **{k: 100 * v / total for k, v in d.items()},
        "vc": vc,
        "f_op": last.frecuencia_metro,
        "t_auto": float(last.t_auto.max()),
        "iters": len(tr.iteraciones),
        "residuo": last.residuo,
        "conv": tr.converged,
    }


def compara_msa() -> None:
    """H2: el MSA promedia TIEMPOS; el algoritmo estandar promedia FLUJOS."""
    print(f"\n{'=' * 78}")
    print("H2 · PROMEDIAR TIEMPOS (actual) vs PROMEDIAR FLUJOS (estandar, §6.2 p.159)")
    print(f"{'=' * 78}")
    cols = ("Auto", "Metro", "Bici", "Caminata", "vc", "f_op", "t_auto", "iters", "residuo")
    print(f"{'metodo · esquema':28s}" + "".join(f"{c:>9s}" for c in cols))
    for metodo in ("expected", "wardrop", "montecarlo"):
        base = None
        for flujos in (False, True):
            r = resumen(corre(metodo, flujos)[0])
            etq = f"{metodo} · {'flujos' if flujos else 'tiempos'}"
            fila = "".join(
                f"{r[c]:9.2f}" if isinstance(r[c], float) else f"{r[c]:>9d}" for c in cols
            )
            print(f"{etq:28s}{fila}{'' if r['conv'] else '  NO CONVERGE'}")
            if base is None:
                base = r
            else:
                dif = max(abs(r[m] - base[m]) for m in ("Auto", "Metro", "Bici", "Caminata"))
                print(f"{'  -> maxima dif. de reparto':28s}{dif:9.2f} pp")


def cortes(tr: ConvergenceTrace, sim) -> dict:
    """Recalcula las utilidades de cada grupo con los tiempos del equilibrio."""
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
        for i in range(ciudad.n_celdas)
    ]

    # Peso de cada grupo = agentes que lo componen. Los teletrabajadores no
    # eligen modo: quedan fuera.
    pesos: dict[tuple, int] = {}
    for a in tr.agentes:
        if getattr(a, "teletrabaja", False):
            continue
        key = (a.estrato, a.celda_origen, a.tiene_auto)
        pesos[key] = pesos.get(key, 0) + 1

    filas = []
    for (estrato, celda, tiene_auto), peso in pesos.items():
        utils = calcular_utilidades(
            estrato=estrato,
            celda_origen=celda,
            tiene_auto=tiene_auto,
            ciudad=ciudad,
            config=sim.demand,
            tiempos_observados=tiempos[celda],
        )
        vivos = [(m, u.valor) for m, u in utils.items() if u.feasible]
        if not vivos:
            continue
        vivos.sort(key=lambda t: -t[1])
        b = sim.demand.estratos[estrato].betas.b_tiempo_viaje
        mejor_modo, mejor = vivos[0]
        cg = mejor / b  # minutos-equivalentes, positivo
        brecha = (vivos[1][1] - mejor) / b if len(vivos) > 1 else float("nan")
        filas.append((mejor_modo, cg, brecha, peso))

    return {"filas": filas, "iters": len(tr.iteraciones), "conv": tr.converged}


def _pond(vals: np.ndarray, w: np.ndarray) -> tuple[float, float]:
    media = float(np.average(vals, weights=w))
    var = float(np.average((vals - media) ** 2, weights=w))
    return media, var**0.5


def reporta(nombre: str, res: dict) -> None:
    filas = res["filas"]
    cg = np.array([f[1] for f in filas])
    br = np.array([f[2] for f in filas])
    w = np.array([f[3] for f in filas], dtype=float)
    modos = [f[0] for f in filas]

    print(f"\n{'=' * 72}\n{nombre}  ({res['iters']} iter, converged={res['conv']})\n{'=' * 72}")
    print(f"grupos: {len(filas)}  ·  agentes: {int(w.sum()):,}")

    media, sd = _pond(cg, w)
    qs = np.percentile(cg, [0, 25, 50, 75, 100])
    print("\nA. COSTO GENERALIZADO DEL MODO ELEGIDO, ENTRE GRUPOS (min-equiv)")
    print(f"   media {media:7.2f}   desv.est {sd:6.2f}   rango {qs[0]:.2f} .. {qs[4]:.2f}")
    print(f"   p25 {qs[1]:.2f}  ·  mediana {qs[2]:.2f}  ·  p75 {qs[3]:.2f}")
    print("   -> si el arbitraje fuera poblacional, la desv.est seria ~0")

    # OJO con la fila de `expected`: "modo elegido" es acá el de MAXIMA utilidad
    # del grupo, no su reparto logit — bajo logit el grupo se reparte entre los
    # cuatro. Los conteos de esa corrida NO son su modal split; van solo como
    # referencia para leer la dispersion de wardrop contra algo.
    print("\nB. COSTO GENERALIZADO MEDIO POR MODO ELEGIDO (min-equiv)")
    for m in MODOS:
        sel = [i for i, mm in enumerate(modos) if mm == m]
        if not sel:
            continue
        mm_media, mm_sd = _pond(cg[sel], w[sel])
        print(f"   {m:9s} {mm_media:7.2f}  (sd {mm_sd:5.2f}, {int(w[sel].sum()):>6,} agentes)")

    finita = ~np.isnan(br)
    print("\nC. BRECHA CON EL SEGUNDO MEJOR MODO, DENTRO DEL GRUPO (min-equiv)")
    bm, bsd = _pond(br[finita], w[finita])
    print(f"   media {bm:7.2f}   desv.est {bsd:6.2f}")
    for umbral in (0.1, 0.5, 1.0, 5.0):
        frac = float(w[finita][br[finita] < umbral].sum()) / float(w[finita].sum())
        print(f"   grupos con brecha < {umbral:4.1f} min: {100 * frac:5.1f}% de los agentes")
    print("   -> equilibrio interior = brecha ~0; de esquina = brecha grande")


def _oferta(sim, ciudad, d_auto, d_metro, d_bici):
    """Recalcula los tres modos congestionables para una demanda dada."""
    car_p, bike_p, train_p = sim.supply.car, sim.supply.bike, sim.supply.train
    car = demora_auto_tramo(
        ubicacion_centro_km=ciudad.cbd_km,
        demanda=d_auto,
        v_max_kmh=car_p.v_max_kmh,
        ancho_pista_m=car_p.ancho_pista_m,
        largo_vehiculo_m=car_p.largo_vehiculo_m,
        gap_m=car_p.gap_m,
        L_ciudad_km=ciudad.largo_total_km,
        num_pistas=car_p.num_pistas,
        alpha_bpr=car_p.alpha_bpr,
        beta_bpr=car_p.beta_bpr,
        capacidad_pista=car_p.capacidad_pista,
    )
    bici = demora_bici_tramo(
        ubicacion_centro_km=ciudad.cbd_km,
        capacidad=bike_p.capacidad_pista,
        demanda=d_bici,
        v_media=bike_p.v_media_kmh,
        L_ciudad_km=ciudad.largo_total_km,
        alpha=bike_p.alpha_bpr,
        beta=bike_p.beta_bpr,
        pendiente_porcentaje=sim.city.pendiente_porcentaje,
        v_caminata=sim.demand.globales.v_caminata,
    )
    tren = oferta_tren(
        demanda=d_metro,
        L_ciudad_km=ciudad.largo_total_km,
        x_centro_km=ciudad.cbd_km,
        v_tren_kmh=train_p.v_tren_kmh,
        capacidad_tren=train_p.capacidad_tren,
        num_estaciones=train_p.num_estaciones,
        v_caminata_kmh=train_p.v_caminata_kmh,
        tasa_carga=train_p.tasa_carga,
        tiempo_detencion_min=train_p.tiempo_detencion_min,
        frec_min=train_p.frec_min,
        frec_max=train_p.frec_max,
        anden_alpha=train_p.anden_alpha,
        anden_beta=train_p.anden_beta,
    )
    return car, bici, tren


def _t_modo(car, bici, tren, modo: str, i: int) -> float:
    if modo == "Auto":
        return float(car.t_usuarios_min[i])
    if modo == "Bici":
        return float(bici.t_usuarios_min[i])
    if modo == "Metro":
        return float(tren.t_acceso_min[i] + tren.t_espera_min[i] + tren.t_viaje_min[i])
    return float("nan")  # la caminata no congestiona


def poder_de_mercado(tr: ConvergenceTrace, sim) -> None:
    """D: por que no se igualan costos DENTRO de un par origen-destino.

    La igualacion de Corollary 4.1 necesita que el reparto de un par OD mueva
    los costos QUE ESE PAR OD ENFRENTA — como en el ejemplo del libro (p. 91),
    donde h1 aparece a ambos lados de `t1(h1) = t2(7000−h1)` y por eso hay
    solucion interior. Acá se mide el termino equivalente: cuanto cambia el
    costo del modo destino si un grupo se muda ENTERO.
    """
    last = tr.iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    d0 = (last.demanda_auto.copy(), last.demanda_metro.copy(), last.demanda_bici.copy())
    base = _oferta(sim, ciudad, *d0)
    idx = {"Auto": 0, "Metro": 1, "Bici": 2}

    # Grupos ordenados por tamaño: el mas grande es el caso MAS favorable a que
    # la igualacion sea posible. Si ni ese mueve su costo, ninguno lo hace.
    pesos: dict[tuple, int] = {}
    for a in tr.agentes:
        if a.teletrabaja:
            continue
        pesos[(a.estrato, a.celda_origen, a.tiene_auto)] = (
            pesos.get((a.estrato, a.celda_origen, a.tiene_auto), 0) + 1
        )
    # Candidatos: el segundo mejor tiene que ser un modo CONGESTIONABLE, o el
    # experimento no tiene sentido (mudarse a la caminata no encarece nada).
    cands = []
    for (estrato, celda, tiene_auto), n in pesos.items():
        utils = calcular_utilidades(
            estrato=estrato,
            celda_origen=celda,
            tiene_auto=tiene_auto,
            ciudad=ciudad,
            config=sim.demand,
            tiempos_observados=TiemposObservados(
                auto_total=float(last.t_auto[celda]),
                bici_total=float(last.t_bici[celda]),
                tren_acceso=float(last.t_tren_acceso[celda]),
                tren_espera=float(last.t_tren_espera[celda]),
                tren_viaje=float(last.t_tren_viaje[celda]),
            ),
        )
        vivos = sorted(((m, u.valor) for m, u in utils.items() if u.feasible), key=lambda t: -t[1])
        if len(vivos) < 2 or vivos[1][0] not in idx:
            continue
        b = sim.demand.estratos[estrato].betas.b_tiempo_viaje
        cands.append(
            (
                n,
                estrato,
                celda,
                tiene_auto,
                vivos[0][0],
                vivos[1][0],
                (vivos[1][1] - vivos[0][1]) / b,
            )
        )
    # El grupo mas grande es el caso MAS favorable a la igualacion: si ni ese
    # mueve su propio costo, ninguno lo hace.
    top = sorted(cands, key=lambda c: -c[0])[:4]

    print(f"\n{'=' * 78}")
    print("D · PODER DE MERCADO DEL GRUPO: por que no hay igualacion dentro del par OD")
    print(f"{'=' * 78}")
    print(
        f"{'grupo (estrato,celda,auto)':26s}{'n':>6s}{'% del modo':>11s}"
        f"{'m1->m2':>14s}{'brecha':>9s}{'Δcosto':>9s}{'razon':>8s}"
    )

    def razon_de(n, celda, m1, m2, brecha) -> tuple[float, float]:
        """Mudanza completa del grupo: m1 pierde n viajes en su celda, m2 los
        gana. Devuelve (Δcosto del destino, Δcosto/brecha)."""
        d1 = [x.copy() for x in d0]
        if m1 in idx:
            d1[idx[m1]][celda] -= n
        d1[idx[m2]][celda] += n
        alt = _oferta(sim, ciudad, *d1)
        delta = _t_modo(*alt, m2, celda) - _t_modo(*base, m2, celda)
        return delta, (abs(delta) / brecha if brecha else float("nan"))

    for n, estrato, celda, tiene_auto, m1, m2, brecha in top:
        delta, razon = razon_de(n, celda, m1, m2, brecha)
        cuota = 100 * n / max(float(d0[idx[m2]].sum()), 1.0)
        print(
            f"({estrato},{celda:3d},{str(tiene_auto)[0]}){'':10s}{n:6d}{cuota:10.2f}%"
            f"{m1[:4] + '->' + m2[:4]:>14s}{brecha:9.2f}{delta:9.4f}{razon:8.4f}"
        )
    print("\n   brecha = lo que habria que cerrar para igualar (min-equiv)")
    print("   Δcosto = lo que el modo destino encarece al recibir al grupo ENTERO")
    print("   razon  = Δcosto / brecha. Interior exige razon >= 1; ~0 significa")
    print("            que el grupo no tiene poder para mover su propio costo.")

    # Los 4 de arriba son los mas GRANDES, no los tipicos. La distribucion sobre
    # todos los candidatos es la que decide, y hay que ponderarla por agentes.
    razones, brechas, ws = [], [], []
    for n, _e, celda, _ta, m1, m2, brecha in cands:
        _, r = razon_de(n, celda, m1, m2, brecha)
        razones.append(r)
        brechas.append(brecha)
        ws.append(n)
    r_arr, b_arr, w_arr = np.array(razones), np.array(brechas), np.array(ws, dtype=float)
    ok = np.isfinite(r_arr)
    print(f"\n   Distribucion sobre los {len(cands)} grupos con destino congestionable")
    print(f"   ({int(w_arr[ok].sum()):,} agentes, ponderada por agentes):")
    for u in (0.5, 1.0):
        frac = float(w_arr[ok][r_arr[ok] >= u].sum()) / float(w_arr[ok].sum())
        print(f"     razon >= {u:.1f}: {100 * frac:5.1f}% de los agentes")
    med, sd = _pond(r_arr[ok], w_arr[ok])
    print(f"     media {med:.3f} · mediana {float(np.median(r_arr[ok])):.3f} · desv.est {sd:.3f}")
    marg = b_arr[ok] < 1.0
    if marg.any():
        mm, _ = _pond(r_arr[ok][marg], w_arr[ok][marg])
        print(f"     entre los MARGINALES (brecha < 1 min): razon media {mm:.3f}")
    lejos = b_arr[ok] >= 5.0
    if lejos.any():
        ml, _ = _pond(r_arr[ok][lejos], w_arr[ok][lejos])
        print(f"     entre los LEJANOS   (brecha >= 5 min): razon media {ml:.3f}")


if __name__ == "__main__":
    for metodo in ("wardrop", "expected"):
        reporta(metodo.upper(), cortes(*corre(metodo)))
    compara_msa()
    tr_w, sim_w = corre("wardrop")
    poder_de_mercado(tr_w, sim_w)
