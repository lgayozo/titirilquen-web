"""Los dos regímenes del metro: cuándo manda el Mohring y cuándo el andén.

El metro tiene DOS canales por los que su nivel de servicio se degrada, y con la
ciudad por defecto sólo uno está operativo:

    espera = 30/f_op  ×  (1 + α·ρ^β)
             ~~~~~~~~     ~~~~~~~~~~~
             Mohring       andén

* **Mohring**: `f = carga/K`, así que menos demanda ⇒ menos trenes ⇒ más espera.
  Es un canal de RETROALIMENTACIÓN NEGATIVA y es el que hace posible
  Downs-Thomson: al agregar pistas el metro pierde pasajeros y empeora.
* **Andén**: `ρ = carga/(frec_max·K)`. Con la población por defecto vale 0,13 y
  el recargo es ×1,0001 — inactivo. Se activa recién con mucha más demanda.

Los dos regímenes son **mutuamente excluyentes**, y ése es el punto: para que el
andén muerda hay que subir tanto la población que `f_op` topa en `frec_max`, y
sin frecuencia endógena el Mohring se apaga. Este script mide ambos lados.

Correr desde packages/titirilquen_core:

    uv run python scripts/regimenes_metro.py

Nota de estilo: la salida va en ASCII (ver `diagnostico_bienestar.py`), porque la
consola de Windows usa cp1252 y un `print` con «ρ» aborta la corrida.
"""

from __future__ import annotations

import sys

from _comun import base_sim, corre_trace, resumen, vc_auto

from titirilquen_core.land_use.config import LandUseConfig

#: Los dos escenarios del contraste, con las pistas que dejan a CADA UNO en la
#: rodilla de la BPR (v/c ~ 1). No es un detalle: con 2 pistas la metrópolis
#: arranca en v/c 3,68 y el auto no compite, así que el contraste mediría la
#: saturación del auto y no el régimen del metro.
ESCENARIOS = (
    ("BASE 36k", 1800, 36_000, 2),
    ("METROPOLIS 144k", 7200, 144_000, 12),
)

PISTAS_BARRIDO = (1, 2, 4)


def _land_use(poblacion: int) -> LandUseConfig:
    h = (int(poblacion * 0.20), int(poblacion * 0.50), int(poblacion * 0.30))
    return LandUseConfig(H_por_estrato=h, forma="normal", oferta_sigma_frac=0.5)


def corrida(densidad: int, poblacion: int, pistas: int, metodo: str) -> dict:
    sim = base_sim()
    sim.city.densidad_hab_km = densidad
    sim.supply.car.num_pistas = pistas
    sim.assignment = metodo
    tr = corre_trace(sim, _land_use(poblacion))
    r = resumen(tr)
    it = tr.iteraciones[-1]
    K = sim.supply.train.capacidad_tren
    fmax = sim.supply.train.frec_max
    cm = getattr(tr, "carga_metro", None)
    carga = float(max(cm)) if cm is not None and len(cm) else 0.0
    rho = carga / (fmax * K) if fmax * K else 0.0
    factor = 1 + sim.supply.train.anden_alpha * (rho**sim.supply.train.anden_beta)
    esperas = [float(v) for v in it.t_tren_espera if v > 0]
    return {
        "metro": r["Metro"],
        "auto": r["Auto"],
        "f_op": r["f_op"],
        "espera": max(esperas) if esperas else 0.0,
        "rho": rho,
        "factor": factor,
        "vc_auto": vc_auto(tr),
        "variacion": (
            (max(esperas) - min(esperas)) / max(esperas) if esperas and max(esperas) else 0.0
        ),
    }


def seccion_1() -> None:
    print("\n### 1. El punto de partida de cada escenario")
    print("  Las pistas de cada uno son las que lo dejan en la rodilla (v/c ~ 1).\n")
    print(f"{'escenario':<18}{'pistas':>7}{'v/c auto':>10}{'auto%':>8}{'metro%':>9}{'f_op':>8}")
    print("-" * 60)
    for nombre, dens, pob, pistas in ESCENARIOS:
        d = corrida(dens, pob, pistas, "expected")
        print(
            f"{nombre:<18}{pistas:>7}{d['vc_auto']:>10.2f}"
            f"{d['auto']:>8.2f}{d['metro']:>9.2f}{d['f_op']:>8.1f}"
        )


def seccion_2() -> None:
    print("\n### 2. Que canal opera en cada regimen")
    print(f"\n{'escenario':<18}{'espera':>9}{'rho anden':>11}{'factor':>9}{'var esp':>9}  canal")
    print("-" * 70)
    for nombre, dens, pob, pistas in ESCENARIOS:
        d = corrida(dens, pob, pistas, "expected")
        canal = "anden" if d["factor"] > 1.01 else "solo Mohring"
        print(
            f"{nombre:<18}{d['espera']:>9.2f}{d['rho']:>11.3f}"
            f"{d['factor']:>9.4f}{100 * d['variacion']:>8.1f}%  {canal}"
        )
    print("\n  'var esp' es cuanto varia la espera ENTRE estaciones. Con el anden")
    print("  inactivo es 0%: una sola frecuencia para toda la linea, o sea una")
    print("  constante. Por eso la vista de espera es una cifra y no un perfil.")


def seccion_3() -> None:
    print("\n### 3. Downs-Thomson: agregar pistas, en cada regimen")
    print("  Metodo determinstico (todo_o_nada), que es donde la paradoja aparece.\n")
    for nombre, dens, pob, _ in ESCENARIOS:
        print(f"  {nombre}")
        print(f"    {'pistas':>7}{'metro%':>9}{'auto%':>8}{'f_op':>8}{'espera':>9}")
        base_esp = None
        for pistas in PISTAS_BARRIDO:
            d = corrida(dens, pob, pistas, "todo_o_nada")
            if base_esp is None:
                base_esp = d["espera"]
            print(
                f"    {pistas:>7}{d['metro']:>9.2f}{d['auto']:>8.2f}"
                f"{d['f_op']:>8.1f}{d['espera']:>9.2f}"
            )
            ultima = d["espera"]
        signo = "SUBE" if ultima > base_esp else "BAJA"
        print(f"    -> al agregar pistas la espera {signo} ({base_esp:.2f} -> {ultima:.2f} min)\n")
    print("  En BASE la espera SUBE: el metro pierde pasajeros, baja la frecuencia")
    print("  y empeora. Eso es Downs-Thomson. En METROPOLIS la espera BAJA: f_op")
    print("  esta topada en frec_max, asi que el Mohring no opera, y perder")
    print("  pasajeros solo descongestiona el anden. El signo se da vuelta.")


def main() -> None:
    print("=" * 70)
    print("LOS DOS REGIMENES DEL METRO - Mohring vs anden")
    print("=" * 70)
    seccion_1()
    seccion_2()
    seccion_3()
    print()


if __name__ == "__main__":
    sys.exit(main())
