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
arbitraje fuera poblacional. Este script lo mide, en tres cortes:

  A. Dispersion del costo generalizado del modo elegido ENTRE grupos. Si el
     arbitraje fuera poblacional, seria ~0.
  B. Costo generalizado medio por modo elegido. Si los modos "usados" se
     igualaran, las filas coincidirian.
  C. Brecha entre el modo elegido y el segundo mejor, DENTRO de cada grupo. Mide
     si el equilibrio es interior (brecha ~0, la condicion de Corollary 4.1
     mordiendo) o de esquina (brecha grande, la condicion satisfecha al vacio
     por tener una sola alternativa usada — el caso de la p. 92 del libro).

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

MODOS = ("Auto", "Metro", "Bici", "Caminata")


def corre(assignment: str) -> tuple[ConvergenceTrace, object]:
    sim = base_sim()
    sim.assignment = assignment
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, base_lu(), tr, localizacion="equilibrio"):
        pass
    return tr, sim


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


if __name__ == "__main__":
    for metodo in ("wardrop", "expected"):
        reporta(metodo.upper(), cortes(*corre(metodo)))
