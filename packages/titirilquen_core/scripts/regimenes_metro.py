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

from titirilquen_core.bienestar import calcular_agregados
from titirilquen_core.land_use.config import LandUseConfig

#: Los dos escenarios del contraste, con las pistas que dejan a CADA UNO en la
#: rodilla de la BPR (v/c ~ 1). No es un detalle: con 2 pistas la metrópolis
#: arranca en v/c 3,68 y el auto no compite, así que el contraste mediría la
#: saturación del auto y no el régimen del metro.
ESCENARIOS = (
    ("BASE 36k", 1800, 36_000, 2),
    ("METROPOLIS 144k", 7200, 144_000, 12),
)

PISTAS_BARRIDO = (1, 2, 4, 8, 12)


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
    f_teo = carga / K if K else 0.0
    return {
        "tope": "MAX" if f_teo >= fmax - 1e-6 else "-",
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
    print("\n### 3. Que le pasa a la espera del metro al agregar pistas")
    print("  Metodo determinstico (todo_o_nada). La columna 'tope' es la clave:")
    print("  con f_op topada en frec_max el Mohring no puede operar.\n")
    for nombre, dens, pob, _ in ESCENARIOS:
        print(f"  {nombre}")
        print(
            f"    {'pistas':>7}{'metro%':>9}{'auto%':>8}{'f_op':>8}"
            f"{'tope':>6}{'espera':>9}{'vs 1 pista':>12}"
        )
        base_esp = None
        for pistas in PISTAS_BARRIDO:
            d = corrida(dens, pob, pistas, "todo_o_nada")
            if base_esp is None:
                base_esp = d["espera"]
            print(
                f"    {pistas:>7}{d['metro']:>9.2f}{d['auto']:>8.2f}"
                f"{d['f_op']:>8.1f}{d['tope']:>6}{d['espera']:>9.2f}"
                f"{d['espera'] - base_esp:>+12.2f}"
            )
        print()
    print("  En BASE la espera SUBE monotonamente: el metro pierde pasajeros, baja")
    print("  la frecuencia y empeora. Ese es el canal de Downs-Thomson.")
    print()
    print("  En METROPOLIS hay que leer la columna 'tope'. Mientras f_op esta")
    print("  TOPADA en frec_max el Mohring no opera -la frecuencia no puede caer-")
    print("  y perder pasajeros solo descongestiona el anden, asi que la espera")
    print("  BAJA. En cuanto f_op se despega del tope el Mohring vuelve y la espera")
    print("  empieza a subir de nuevo. O sea que el signo NO lo decide la poblacion")
    print("  sino si el tope muerde; con las 12 pistas del preset ya no muerde.")
    print()
    print("  Y bajo logit (expected) el metro empeora SIEMPRE, en los dos")
    print("  escenarios: ahi la frecuencia nunca topa y el Mohring gana.")


def seccion_4() -> None:
    """El signo del BIENESTAR, en las dos unidades."""
    print("\n### 4. El bienestar, en las dos unidades")
    print("  Costo generalizado que sube NO prueba la paradoja: quien cambia de")
    print("  modo voluntariamente puede pagar mas y estar mejor. Decide el")
    print("  excedente. Pero el excedente depende de en que se agregue:\n")
    print("  lambda_h : VoT conductual por estrato -> eficiencia, disposicion a pagar")
    print("  social   : VoT unico de norma         -> evaluacion social (SNI)\n")
    print(
        f"  {'pistas':>7}{'metro%':>9}{'exc lambda_h':>15}{'delta':>9}"
        f"{'exc SOCIAL':>13}{'delta':>9}"
    )
    print("  " + "-" * 62)
    b_h = b_s = None
    for pistas in (1, 2, 3, 4, 6):
        sim = base_sim()
        sim.supply.car.num_pistas = pistas
        sim.assignment = "todo_o_nada"
        sim.tolerance = 0.02
        sim.max_iter = 120
        tr = corre_trace(sim, _land_use(36_000))
        agg = calcular_agregados(sim, tr)
        r = resumen(tr)
        n = max(agg["viajeros"], 1)
        e_h = agg["excedente_max_total_clp"] / n
        e_s = agg["excedente_social_total_clp"] / n
        if b_h is None:
            b_h, b_s = e_h, e_s
        marca = "  <-- PEOR" if e_s - b_s < -1 else ""
        print(
            f"  {pistas:>7}{r['Metro']:>9.2f}{e_h:>15,.0f}{e_h - b_h:>+9,.0f}"
            f"{e_s:>13,.0f}{e_s - b_s:>+9,.0f}{marca}"
        )
    print("\n  Con lambda_h el bienestar SUBE monotonamente: no hay paradoja.")
    print("  Con lambda social CAE entre 3 y 4 pistas: la paradoja aparece.")
    print("  La causa es el peso implicito de cada estrato: 1/|beta_t| vale")
    print("  18,2 / 30,2 / 66,7 (3,7x entre extremos) y 1/lambda_h vale")
    print("  1.879 / 1.560 / 1.776, casi plano. Agregar en minutos -o al VoT")
    print("  social, que es lo mismo salvo un factor- pondera a favor del")
    print("  estrato bajo, que es el que mas usa el metro.")


def main() -> None:
    print("=" * 70)
    print("LOS DOS REGIMENES DEL METRO - Mohring vs anden")
    print("=" * 70)
    seccion_1()
    seccion_2()
    seccion_3()
    seccion_4()
    print()


if __name__ == "__main__":
    sys.exit(main())
