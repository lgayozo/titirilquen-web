"""Diagnostico de la CALIBRACION del logit: los betas contra su teoria.

Los 42 coeficientes estan en utiles, una unidad sin escala propia: un
`b_tiempo_espera = -0.0243` no se puede juzgar solo ni comparar entre estratos,
porque cada estrato tiene su propia escala de utilidad. Este script los pasa a
dos unidades que si son juzgables, y contrasta cada una contra la direccion que
predice la teoria:

  * MINUTOS-EQUIVALENTES: cualquier termino dividido por `b_tiempo_viaje` dice
    cuantos minutos de viaje en vehiculo equivale. Es la unidad natural para
    comparar penalizaciones y constantes ENTRE estratos, porque la escala de
    utilidad se cancela en el cociente.

  * PESOS: dividido por `b_costo`, cuanto dinero equivale.

Lo que se contrasta (cada bloque imprime OK o el desvio):

  1. Razon espera/viaje. Esperar en un anden es mas oneroso que ir sentado:
     el peso de la espera deberia ser MAYOR que el del tiempo en vehiculo.
  2. Razon caminata/viaje, misma logica para el acceso.
  3. Valor del tiempo creciente en el ingreso, y con una dispersion entre
     estratos que no sea absurda.
  4. Penalizaciones fisicas: signo, monotonia por umbral y magnitud en
     minutos-equivalentes.
  5. Constantes especificas: cuanto pesan en minutos-equivalentes.

OJO con lo que este script NO hace: no valida los betas contra ninguna
estimacion externa. Los rangos de referencia estan declarados arriba como
constantes para que se puedan cambiar; el veredicto empirico lo pone quien
tenga la fuente a mano.

Correr desde packages/titirilquen_core:

    uv run python scripts/diagnostico_calibracion.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from auditoria_transporte import base_sim

from titirilquen_core.config import StratumBetas, StratumConfig

# Rangos de referencia. NO son un resultado de este modelo ni una cita: son el
# supuesto contra el que se contrasta, puesto aca para que sea facil cambiarlo.
RAZON_ESPERA_MIN = 1.5
RAZON_ESPERA_MAX = 2.5
RAZON_CAMINATA_MIN = 1.5
RAZON_CAMINATA_MAX = 2.5

NOMBRES = {1: "alto", 2: "medio", 3: "bajo"}
UMBRALES_BICI = (10, 20, 30)
UMBRALES_WALK = (5, 15, 25)


def linea(c: str = "-") -> None:
    print(c * 78)


def fmt_clp(v: float) -> str:
    return f"${v:>10,.0f}".replace(",", ".")


def veredicto(ok: bool) -> str:
    return "OK  " if ok else "**  "


def minutos_equivalentes(utiles: float, b: StratumBetas) -> float:
    """Utiles -> minutos de viaje en vehiculo. La escala de utilidad se cancela."""
    return utiles / b.b_tiempo_viaje


def razones(estratos: dict[int, StratumConfig]) -> None:
    print("\n1-2. PESO RELATIVO DE CADA COMPONENTE DEL TIEMPO")
    print("     (= beta del componente / beta del tiempo en vehiculo)")
    linea()
    print(f"{'estrato':<10}{'espera/viaje':>16}{'caminata/viaje':>18}   veredicto")
    linea()
    for h, s in sorted(estratos.items()):
        b = s.betas
        r_esp = b.b_tiempo_espera / b.b_tiempo_viaje
        r_cam = b.b_tiempo_caminata / b.b_tiempo_viaje
        ok_esp = RAZON_ESPERA_MIN <= r_esp <= RAZON_ESPERA_MAX
        ok_cam = RAZON_CAMINATA_MIN <= r_cam <= RAZON_CAMINATA_MAX
        marcas = []
        if not ok_esp:
            marcas.append(f"espera {r_esp:.2f} fuera de [{RAZON_ESPERA_MIN}, {RAZON_ESPERA_MAX}]")
        if not ok_cam:
            marcas.append(
                f"caminata {r_cam:.2f} fuera de [{RAZON_CAMINATA_MIN}, {RAZON_CAMINATA_MAX}]"
            )
        print(
            f"{NOMBRES[h]:<10}{r_esp:>16.2f}{r_cam:>18.2f}   "
            f"{veredicto(ok_esp and ok_cam)}{'; '.join(marcas)}"
        )
    linea()
    print("     ** razon < 1 significa que el modelo afirma que esperar (o caminar)")
    print("        molesta MENOS que ir sentado en el vehiculo.")


def valor_del_tiempo(estratos: dict[int, StratumConfig]) -> None:
    print("\n3. VALOR DEL TIEMPO (= b_tiempo_viaje / b_costo, en $/hora)")
    linea()
    vots = {}
    for h, s in sorted(estratos.items()):
        b = s.betas
        vot = (b.b_tiempo_viaje / b.b_costo) * 60
        vots[h] = vot
        print(f"{NOMBRES[h]:<10}{fmt_clp(vot)} /h")
    linea()
    disp = vots[1] / vots[3]
    print(f"{'dispersion alto/bajo':<28}{disp:>8.1f}x   {veredicto(disp <= 10)}")
    creciente = vots[1] > vots[2] > vots[3]
    marca = "si" if creciente else "NO"
    print(f"{'creciente en el ingreso':<28}{marca:>8}     {veredicto(creciente)}")


def penalizaciones(estratos: dict[int, StratumConfig]) -> None:
    print("\n4. PENALIZACIONES FISICAS, en minutos-equivalentes de viaje")
    print("   (acumulativas: un viaje de 25 min en bici carga la de 10 y la de 20)")
    linea()
    encabezado = f"{'estrato':<10}" + "".join(f"{f'>{u} min':>12}" for u in UMBRALES_BICI)
    print(f"BICI      {encabezado[10:]}      acumulado a 30+")
    linea()
    for h, s in sorted(estratos.items()):
        b = s.betas
        p = b.penalizaciones_fisicas
        vals = [minutos_equivalentes(x, b) for x in (p.bici_10, p.bici_20, p.bici_30)]
        print(f"{NOMBRES[h]:<10}" + "".join(f"{v:>12.1f}" for v in vals) + f"{sum(vals):>18.1f}")
    linea()
    encabezado = "".join(f"{f'>{u} min':>12}" for u in UMBRALES_WALK)
    print(f"CAMINATA  {encabezado}      acumulado a 25+")
    linea()
    for h, s in sorted(estratos.items()):
        b = s.betas
        p = b.penalizaciones_fisicas
        vals = [minutos_equivalentes(x, b) for x in (p.walk_5, p.walk_15, p.walk_25)]
        print(f"{NOMBRES[h]:<10}" + "".join(f"{v:>12.1f}" for v in vals) + f"{sum(vals):>18.1f}")
    linea()

    # La penalizacion mas dura deberia ser la del umbral mas alto, y el estrato
    # con menos alternativas no deberia ser el que mas castiga el modo barato.
    for h, s in sorted(estratos.items()):
        b = s.betas
        p = b.penalizaciones_fisicas
        bici = [p.bici_10, p.bici_20, p.bici_30]
        walk = [p.walk_5, p.walk_15, p.walk_25]
        mono_b = abs(bici[0]) <= abs(bici[1]) <= abs(bici[2])
        mono_w = abs(walk[0]) <= abs(walk[1]) <= abs(walk[2])
        signo = all(x <= 0 for x in bici + walk)
        print(
            f"{NOMBRES[h]:<10}signo negativo {veredicto(signo)}"
            f"  monotona bici {veredicto(mono_b)}  monotona caminata {veredicto(mono_w)}"
        )


def constantes(estratos: dict[int, StratumConfig]) -> None:
    print("\n5. CONSTANTES ESPECIFICAS, en minutos-equivalentes de viaje")
    print("   (solo importan las DIFERENCIAS; se toma el metro como referencia)")
    linea()
    print(f"{'estrato':<10}{'auto':>12}{'metro':>12}{'bici':>12}{'caminata':>12}")
    linea()
    for h, s in sorted(estratos.items()):
        b = s.betas
        base = b.asc_metro
        vals = [
            minutos_equivalentes(x - base, b)
            for x in (b.asc_auto, b.asc_metro, b.asc_bici, b.asc_caminata)
        ]
        print(f"{NOMBRES[h]:<10}" + "".join(f"{v:>12.1f}" for v in vals))
    linea()
    print("     Positivo = el modo arranca con VENTAJA sobre el metro, medida en")
    print("     minutos de viaje que el usuario aceptaria de mas por elegirlo.")


def main() -> None:
    sim = base_sim()
    estratos = sim.demand.estratos

    print("=" * 78)
    print("DIAGNOSTICO DE CALIBRACION DEL LOGIT")
    print("=" * 78)
    print("Coeficientes crudos (utiles):")
    linea()
    print(f"{'estrato':<10}{'b_viaje':>12}{'b_espera':>12}{'b_caminata':>12}{'b_costo':>12}")
    linea()
    for h, s in sorted(estratos.items()):
        b = s.betas
        print(
            f"{NOMBRES[h]:<10}{b.b_tiempo_viaje:>12.4f}{b.b_tiempo_espera:>12.4f}"
            f"{b.b_tiempo_caminata:>12.4f}{b.b_costo:>12.5f}"
        )

    razones(estratos)
    valor_del_tiempo(estratos)
    penalizaciones(estratos)
    constantes(estratos)

    print("\n" + "=" * 78)
    print("Nota estructural: `b_tiempo_viaje` pesa auto, tren en vehiculo Y BICI;")
    print("`b_tiempo_caminata` pesa el acceso al metro Y el modo caminata completo.")
    print("Ver demand/utility.py lineas 89-140.")
    print("=" * 78)


if __name__ == "__main__":
    main()
