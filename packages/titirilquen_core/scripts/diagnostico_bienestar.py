"""Diagnóstico de la medida de bienestar: cuánto separa al logsum del máximo.

El núcleo calcula las DOS medidas del excedente en toda corrida —logsum bajo los
métodos logit, utilidad máxima bajo `todo_o_nada`— y declara cuál corresponde en
`medida_bienestar`. Este script las pone lado a lado.

Responde tres preguntas:

1. BRECHA. `G = ln Σ e^{V_m} − max_m V_m`, sobre el MISMO equilibrio. Medir así
   la aísla: comparar dos corridas distintas mezclaría la brecha con el cambio
   de equilibrio. Por log-sum-exp, `G ∈ [0, ln J]` con `J` = alternativas
   factibles, y es el valor que el logit le atribuye a la dispersión de gustos.

2. ¿SE CANCELA EN EL Δ? Si `G` fuera constante entre escenarios, restar dos
   corridas la eliminaría y las medidas serían intercambiables para comparar
   políticas. No lo es: depende de cuántas alternativas hay y de cuán parecidas
   son sus utilidades, y las dos cosas se mueven. Lo que este script imprime es
   cuánto se mueve.

3. COBERTURA. Los agentes sin NINGÚN modo factible quedan fuera del promedio y
   del denominador de población (ver el docstring de `bienestar.py`). Acá se
   cuenta cuántos son: si dejara de ser cero, el excedente estaría escondiendo a
   quien se quedó sin alternativas en vez de contarlo como bienestar bajo.

El desarrollo matemático completo está en `docs/informe-bienestar.html`.

Nota de estilo: **lo que se IMPRIME va en ASCII**, como en el resto de
`scripts/`. No es descuido — la consola de Windows usa cp1252 y un `print` con
«Δ» o «ó» aborta con `UnicodeEncodeError` a mitad de la corrida. Los docstrings
y comentarios sí llevan acentos: nunca pasan por stdout.

Correr desde packages/titirilquen_core:

    uv run python scripts/diagnostico_bienestar.py
"""

from __future__ import annotations

import math

from _comun import base_lu, base_sim, con_city, corre_trace, minutos_equivalentes, resumen

from titirilquen_core.bienestar import calcular_agregados, medidas_de_utilidad
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.constantes import MODOS
from titirilquen_core.demand.utility import TiemposObservados

METODOS = ("expected", "todo_o_nada")
ESTRATOS = ("1", "2", "3")
NOMBRE = {"1": "alto", "2": "medio", "3": "bajo"}


def _con_metodo(metodo: str) -> SimulationConfig:
    sim = base_sim()
    sim.assignment = metodo
    return sim


def brecha_por_estrato() -> dict[str, dict]:
    """Las dos medidas sobre el mismo equilibrio, para cada método."""
    salida = {}
    for metodo in METODOS:
        sim = _con_metodo(metodo)
        tr = corre_trace(sim)
        agg = calcular_agregados(sim, tr)
        if agg is None:
            continue
        salida[metodo] = {"agg": agg, "sim": sim, "resumen": resumen(tr)}
    return salida


def imprime_brecha(datos: dict) -> None:
    print("\n### 1. Brecha entre las dos medidas, sobre el MISMO equilibrio")
    print(f"  techo teorico: ln({len(MODOS)}) = {math.log(len(MODOS)):.4f} utiles\n")
    print(
        f"{'metodo':<14} {'estrato':<8} {'logsum':>10} {'max':>10} "
        f"{'brecha G':>10} {'G en $':>10} {'G en min':>10} {'% techo':>9}"
    )
    print("-" * 88)
    for metodo, d in datos.items():
        agg = d["agg"]
        betas = d["sim"].demand.estratos
        for h in ESTRATOS:
            ls = agg["logsum_por_estrato"][h]
            mx = agg["util_maxima_por_estrato"][h]
            g = ls - mx
            g_clp = agg["excedente_por_estrato_clp"][h] - agg["excedente_max_por_estrato_clp"][h]
            g_min = minutos_equivalentes(g, betas[int(h)].betas.b_tiempo_viaje)
            pct = 100 * g / math.log(len(MODOS))
            print(
                f"{metodo:<14} {NOMBRE[h]:<8} {ls:>10.4f} {mx:>10.4f} "
                f"{g:>10.4f} {g_clp:>10,.0f} {abs(g_min):>10.1f} {pct:>8.1f}%"
            )
    print("\n  G en min = minutos-equivalentes de viaje en vehiculo (utiles / b_tiempo_viaje).")
    print("  Es la unica unidad comparable ENTRE estratos: la escala de la utilidad")
    print("  se cancela en el cociente.")


def imprime_totales(datos: dict) -> None:
    print("\n### 2. Se cancela la brecha al comparar escenarios?")
    print(
        f"\n{'metodo':<14} {'exc. logsum':>18} {'exc. max':>18} {'variedad':>16} {'emparejada':>16}"
    )
    print("-" * 86)
    variedades = {}
    for metodo, d in datos.items():
        agg = d["agg"]
        var = agg["excedente_total_clp"] - agg["excedente_max_total_clp"]
        variedades[metodo] = var
        print(
            f"{metodo:<14} {agg['excedente_total_clp']:>18,.0f} "
            f"{agg['excedente_max_total_clp']:>18,.0f} {var:>16,.0f} "
            f"{agg['medida_bienestar']:>16}"
        )
    if len(variedades) == len(METODOS):
        a, b = METODOS
        delta = variedades[b] - variedades[a]
        print(f"\n  El 'valor de la variedad' se movio {delta:+,.0f} $ entre los dos")
        print("  escenarios. Si fuera constante se cancelaria al restar y las medidas")
        print("  serian intercambiables para comparar politicas. NO lo es: por eso el")
        print("  delta entre metodos distintos no significa nada.")
        print("  Ver docs/informe-bienestar.html seccion 6.3.")
    print("\n  Los NIVELES no son interpretables (cero arbitrario por las ASC); lo que")
    print("  importa aca es la diferencia entre columnas, no su magnitud.")


def imprime_cobertura() -> None:
    """Cuántos agentes quedan fuera del excedente por no tener modo factible."""
    print("\n### 3. Cobertura: agentes sin ninguna alternativa factible")
    print(f"\n{'escenario':<22} {'en el excedente':>18} {'excluidos':>12} {'%':>8}")
    print("-" * 64)
    escenarios = [
        ("base (20 km)", base_sim()),
        ("dispersa (40 km)", con_city(base_sim(), largo_ciudad_km=40)),
    ]
    for etiqueta, sim in escenarios:
        tr = corre_trace(sim)
        snap = tr.iteraciones[-1]
        ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
        dentro = fuera = 0.0
        for i in range(ciudad.n_celdas):
            tiempos = TiemposObservados(
                auto_total=float(snap.t_auto[i]),
                bici_total=float(snap.t_bici[i]),
                tren_acceso=float(snap.t_tren_acceso[i]),
                tren_espera=float(snap.t_tren_espera[i]),
                tren_viaje=float(snap.t_tren_viaje[i]),
            )
            for h in (1, 2, 3):
                if tr.demanda_estrato is None:
                    continue
                n = float(tr.demanda_estrato[h - 1, :, i].sum())
                if n <= 0:
                    continue
                p = sim.demand.estratos[h].prob_auto
                con = medidas_de_utilidad(h, i, True, ciudad, sim, tiempos)
                sin = medidas_de_utilidad(h, i, False, ciudad, sim, tiempos)
                peso = (p if con is not None else 0.0) + ((1 - p) if sin is not None else 0.0)
                if peso > 0:
                    dentro += n
                else:
                    fuera += n
        total = dentro + fuera or 1
        print(f"{etiqueta:<22} {dentro:>18,.0f} {fuera:>12,.0f} {100 * fuera / total:>7.2f}%")
    print("\n  Cero excluidos es lo esperado con el default: el metro sigue siendo")
    print("  factible en casi toda la ciudad. Si esta columna deja de ser cero, el")
    print("  excedente esta omitiendo a quien se quedo sin alternativas en vez de")
    print("  contarlo como bienestar bajo.")


def main() -> None:
    print("=" * 88)
    print("DIAGNOSTICO DE LA MEDIDA DE BIENESTAR - logsum vs utilidad maxima")
    print("=" * 88)
    print(f"  ciudad por defecto de la app - {base_lu().H_por_estrato} hogares por estrato")

    datos = brecha_por_estrato()
    for metodo, d in datos.items():
        r = d["resumen"]
        print(
            f"  {metodo:<12} auto {r['Auto']:.2f} - metro {r['Metro']:.2f} - "
            f"bici {r['Bici']:.2f} - caminata {r['Caminata']:.2f} - {r['iters']} iter"
        )

    imprime_brecha(datos)
    imprime_totales(datos)
    imprime_cobertura()
    print()


if __name__ == "__main__":
    main()
