"""Datos del capítulo 2 — Oferta de transporte.

Produce `cap02.json`. El capítulo tiene que sostener tres cosas: que las
funciones de costo son las que dicen ser (Greenshields, BPR, Mohring), que sus
salvaguardas —el piso de la bicicleta, los topes de frecuencia, la congestión de
andén— hacen lo que prometen, y que los tres modos ven la misma geometría que el
capítulo 1 describió.

Seis bloques:

1. `geometria_compartida` — dónde pone el CBD cada modo. Es la consistencia con
   el capítulo 1: si los tres no coinciden, todo lo demás se mide contra
   distancias distintas.
2. `auto` — Greenshields (capacidad desde el fundamental) y BPR (demora contra
   grado de saturación), contrastados con la fórmula cerrada.
3. `bici` — el piso de caminata (D-15) y el efecto de la pendiente (D-01, AT-05).
4. `metro` — el efecto Mohring (más demanda ⇒ más frecuencia ⇒ menos espera), y
   si los topes `frec_min`/`frec_max` están mordiendo (AT-08/AT-09).
5. `anden` — cuánto pesa realmente la congestión de andén (D-12, D-16).
6. `red_vacia` — el contrafactual que usan el ΔCS del acoplado y, desde D-42, la
   accesibilidad del suelo.

Correr desde `packages/titirilquen_core` (~1 min):

    uv run python ../../docs/libro/datos/datos_cap02.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "packages" / "titirilquen_core" / "tests"))

import test_linea_base as base
from titirilquen_core.city import CiudadLineal
from titirilquen_core.supply.bike import demora_bici_tramo
from titirilquen_core.supply.car import demora_auto_tramo
from titirilquen_core.supply.oferta import resolver_oferta, resolver_red_vacia
from titirilquen_core.supply.train import oferta_tren

SALIDA = Path(__file__).parent / "cap02.json"


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


def _ciudad():
    c = base._config_web()
    return c, CiudadLineal(
        n_celdas=c.city.n_celdas, largo_total_km=c.city.largo_ciudad_km
    )


def geometria_compartida() -> dict:
    """¿Los tres modos ponen el CBD en la misma celda que el capítulo 1?

    Auto y bici reconvierten `cbd_km` con `int(cbd_km/L·N)`; el tren hace lo
    mismo para la parcela del CBD pero además construye sus estaciones sobre
    **centroides** (`arange(N)·dx + dx/2`). Se comprueba que la celda coincida y
    se anota la diferencia de convención.
    """
    filas = []
    # Sólo impares: desde sep-2026 `CiudadLineal` rechaza n par (D-45).
    for n in (201, 101, 51, 1001):
        c = CiudadLineal(n_celdas=n, largo_total_km=20.0)
        idx_reconvertido = max(0, min(int((c.cbd_km / c.largo_total_km) * n), n - 1))
        filas.append(
            {
                "n_celdas": n,
                "cbd_index_cap1": c.cbd_index,
                "idx_centro_auto_bici": idx_reconvertido,
                "idx_cbd_parcela_tren": int((c.cbd_km / c.largo_total_km) * n),
                "coinciden": idx_reconvertido == c.cbd_index,
            }
        )
    return {
        "filas": filas,
        "nota": (
            "int(L/2 / L · n) == n//2 para todo n > 0: los tres modos usan la celda "
            "del capítulo 1 (y desde sep-2026 n es impar por schema). El tren, además, sitúa sus "
            "estaciones sobre centroides (x_i = (i+½)·Δx), que es la convención "
            "continua de `CiudadLineal` — coherente, porque el acceso a la estación "
            "es una distancia física, no un conteo de celdas."
        ),
    }


def auto() -> dict:
    """Greenshields y BPR contra su fórmula cerrada."""
    cfg, ciudad = _ciudad()
    p = cfg.supply.car
    k_j = 1000 / (p.largo_vehiculo_m + p.gap_m)
    factor_ancho = (
        1.0 if p.ancho_pista_m >= 3.5 else (0.9 if p.ancho_pista_m >= 3.0 else 0.75)
    )
    v_l = p.v_max_kmh * factor_ancho
    cap_teorica = (k_j * v_l) / 4 * max(1, p.num_pistas)

    r = demora_auto_tramo(
        ubicacion_centro_km=ciudad.cbd_km,
        demanda=np.zeros(ciudad.n_celdas),
        v_max_kmh=p.v_max_kmh,
        ancho_pista_m=p.ancho_pista_m,
        largo_vehiculo_m=p.largo_vehiculo_m,
        gap_m=p.gap_m,
        L_ciudad_km=ciudad.largo_total_km,
        num_pistas=p.num_pistas,
        alpha_bpr=p.alpha_bpr,
        beta_bpr=p.beta_bpr,
        capacidad_pista=p.capacidad_pista,
    )

    # BPR: demora relativa contra grado de saturación, con demanda uniforme.
    curva = []
    for vc in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        # Demanda uniforme tal que el flujo máximo (junto al CBD) sea vc·C.
        n_media = ciudad.n_celdas // 2
        d = np.full(ciudad.n_celdas, vc * r.capacidad_direccion / max(n_media, 1))
        rr = demora_auto_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            demanda=d,
            v_max_kmh=p.v_max_kmh,
            ancho_pista_m=p.ancho_pista_m,
            largo_vehiculo_m=p.largo_vehiculo_m,
            gap_m=p.gap_m,
            L_ciudad_km=ciudad.largo_total_km,
            num_pistas=p.num_pistas,
            alpha_bpr=p.alpha_bpr,
            beta_bpr=p.beta_bpr,
            capacidad_pista=p.capacidad_pista,
        )
        libre = float(r.t_usuarios_min[0])
        curva.append(
            {
                "vc_borde": round(
                    float(rr.flujos_veh_por_hora.max() / rr.capacidad_direccion), 4
                ),
                "t_borde_min": round(float(rr.t_usuarios_min[0]), 3),
                "razon_vs_flujo_libre": round(float(rr.t_usuarios_min[0] / libre), 4)
                if libre > 0
                else None,
            }
        )

    return {
        "densidad_embotellamiento_veh_km": round(k_j, 3),
        "factor_ancho": factor_ancho,
        "v_libre_kmh": round(v_l, 2),
        "capacidad_teorica_veh_h": round(cap_teorica, 1),
        "capacidad_del_codigo_veh_h": round(float(r.capacidad_direccion), 1),
        "capacidad_explicita_configurada": p.capacidad_pista,
        "alpha_bpr": p.alpha_bpr,
        "beta_bpr": p.beta_bpr,
        "t_flujo_libre_borde_min": round(float(r.t_usuarios_min[0]), 3),
        "curva_bpr": curva,
    }


def bici() -> dict:
    """El piso de caminata (D-15) y la pendiente (D-01, AT-05)."""
    cfg, ciudad = _ciudad()
    p = cfg.supply.bike
    v_cam = cfg.demand.globales.v_caminata
    dx = ciudad.ancho_celda_km

    def corre(demanda_por_celda: float, pendiente: float = 0.0):
        return demora_bici_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            capacidad=p.capacidad_pista,
            demanda=np.full(ciudad.n_celdas, demanda_por_celda),
            v_media=p.v_media_kmh,
            L_ciudad_km=ciudad.largo_total_km,
            alpha=p.alpha_bpr,
            beta=p.beta_bpr,
            pendiente_porcentaje=pendiente,
            v_caminata=v_cam,
        )

    t_tramo_walk = (dx / v_cam) * 60
    t0 = (dx / p.v_media_kmh) * 60
    saturacion = []
    for d in (0.0, 5.0, 20.0, 50.0, 200.0, 1000.0):
        r = corre(d)
        # El piso actúa TRAMO A TRAMO, no sobre el acumulado: se cuenta en
        # cuántos tramos la BPR cruda habría superado el tiempo de caminar.
        crudo = t0 * (
            1
            + p.alpha_bpr * ((r.flujos_bici_por_hora / p.capacidad_pista) ** p.beta_bpr)
        )
        saturacion.append(
            {
                "demanda_por_celda": d,
                "flujo_max_bici_h": round(float(r.flujos_bici_por_hora.max()), 1),
                "t_borde_min": round(float(r.t_usuarios_min[0]), 3),
                "tramos_con_piso_activo": int(np.sum(crudo > t_tramo_walk)),
                "tramos_totales": int(ciudad.n_celdas),
            }
        )

    pendientes = []
    for pend in (-6.0, -3.0, 0.0, 3.0, 6.0):
        r = corre(20.0, pend)
        pendientes.append(
            {"pendiente_pct": pend, "t_borde_min": round(float(r.t_usuarios_min[0]), 3)}
        )

    return {
        "v_media_kmh": p.v_media_kmh,
        "capacidad_pista": p.capacidad_pista,
        "v_caminata_kmh": v_cam,
        "t_tramo_caminando_min": round(t_tramo_walk, 4),
        "saturacion": saturacion,
        "pendiente": pendientes,
        "pendiente_es_simetrica": None,  # se completa abajo
    }


def metro() -> dict:
    """Mohring, los topes de frecuencia y la congestión de andén."""
    cfg, ciudad = _ciudad()
    p = cfg.supply.train

    def corre(demanda_por_celda: float, **kw):
        args = {
            "demanda": np.full(ciudad.n_celdas, demanda_por_celda),
            "L_ciudad_km": ciudad.largo_total_km,
            "x_centro_km": ciudad.cbd_km,
            "v_tren_kmh": p.v_tren_kmh,
            "capacidad_tren": p.capacidad_tren,
            "num_estaciones": p.num_estaciones,
            "v_caminata_kmh": p.v_caminata_kmh,
            "tiempo_detencion_min": p.tiempo_detencion_min,
            "frec_min": p.frec_min,
            "frec_max": p.frec_max,
            "anden_alpha": p.anden_alpha,
            "anden_beta": p.anden_beta,
        }
        args.update(kw)
        return oferta_tren(**args)

    mohring = []
    for d in (0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0):
        r = corre(d)
        mohring.append(
            {
                "demanda_por_celda": d,
                "carga_max_pax": round(
                    float(r.carga_por_tramo.max()) if r.carga_por_tramo.size else 0.0, 1
                ),
                "frecuencia_teorica_tph": round(float(r.frecuencia_teorica), 3),
                "frecuencia_operativa_tph": round(float(r.frecuencia_operativa), 3),
                "topada_en": (
                    "frec_min"
                    if r.frecuencia_teorica < p.frec_min
                    else ("frec_max" if r.frecuencia_teorica > p.frec_max else "no")
                ),
                "espera_media_min": round(float(np.mean(r.t_espera_min)), 3),
                "acceso_medio_min": round(float(np.mean(r.t_acceso_min)), 3),
            }
        )

    # ¿Cuánto pesa la BPR de andén? Se compara con anden_alpha = 0.
    anden = []
    for d in (10.0, 40.0, 80.0, 160.0):
        con = corre(d)
        sin = corre(d, anden_alpha=0.0)
        e_con, e_sin = (
            float(np.mean(con.t_espera_min)),
            float(np.mean(sin.t_espera_min)),
        )
        anden.append(
            {
                "demanda_por_celda": d,
                "espera_con_anden_min": round(e_con, 4),
                "espera_sin_anden_min": round(e_sin, 4),
                "sobrecosto_pct": round(100.0 * (e_con / e_sin - 1.0), 4)
                if e_sin > 0
                else None,
            }
        )

    # Estaciones: más estaciones acortan el acceso pero agregan detenciones.
    # `num_estaciones` no es el número de estaciones: la construcción parte del
    # CBD hacia ambos lados con paso L/n y luego filtra a [0, L], así que el
    # conteo real depende de si los bordes caen exactos (ver §6).
    conteo_estaciones = []
    for n_est in (2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 30):
        r = corre(0.0, num_estaciones=n_est)
        conteo_estaciones.append(
            {
                "pedidas": n_est,
                "reales": len(r.estaciones_km),
                "diferencia": len(r.estaciones_km) - n_est,
                "separacion_km": round(ciudad.largo_total_km / n_est, 4),
            }
        )

    # Rango amplio: el óptimo interior que promete la interfaz existe, pero
    # está lejos del default (ver §4).
    estaciones = []
    for n_est in (2, 4, 6, 8, 10, 14, 20, 30, 40, 60, 80, 120):
        r = corre(20.0, num_estaciones=n_est)
        estaciones.append(
            {
                "num_estaciones": n_est,
                "estaciones_reales": len(r.estaciones_km),
                "acceso_medio_min": round(float(np.mean(r.t_acceso_min)), 3),
                "viaje_medio_min": round(float(np.mean(r.t_viaje_min)), 3),
                "suma_min": round(float(np.mean(r.t_acceso_min + r.t_viaje_min)), 3),
            }
        )

    return {
        "capacidad_tren_pax": p.capacidad_tren,
        "num_estaciones": p.num_estaciones,
        "frec_min_tph": p.frec_min,
        "frec_max_tph": p.frec_max,
        "anden_alpha": p.anden_alpha,
        "anden_beta": p.anden_beta,
        "tiempo_detencion_min": p.tiempo_detencion_min,
        "mohring": mohring,
        "anden": anden,
        "conteo_estaciones": conteo_estaciones,
        "estaciones": estaciones,
    }


def red_vacia() -> dict:
    """El contrafactual: la red sin nadie encima."""
    cfg, ciudad = _ciudad()
    r = resolver_red_vacia(cfg, ciudad)
    cero = np.zeros(ciudad.n_celdas)
    cargada = resolver_oferta(cfg, ciudad, cero + 30.0, cero + 20.0, cero + 20.0)
    return {
        "vacia": {
            "auto_borde_min": round(float(r.auto.t_usuarios_min[0]), 3),
            "bici_borde_min": round(float(r.bici.t_usuarios_min[0]), 3),
            "metro_borde_min": round(
                float(
                    r.tren.t_acceso_min[0]
                    + r.tren.t_espera_min[0]
                    + r.tren.t_viaje_min[0]
                ),
                3,
            ),
            "frecuencia_tph": round(float(r.tren.frecuencia_operativa), 3),
        },
        "cargada": {
            "auto_borde_min": round(float(cargada.auto.t_usuarios_min[0]), 3),
            "bici_borde_min": round(float(cargada.bici.t_usuarios_min[0]), 3),
            "metro_borde_min": round(
                float(
                    cargada.tren.t_acceso_min[0]
                    + cargada.tren.t_espera_min[0]
                    + cargada.tren.t_viaje_min[0]
                ),
                3,
            ),
            "frecuencia_tph": round(float(cargada.tren.frecuencia_operativa), 3),
        },
    }


def main() -> None:
    b = bici()
    # AT-05: con la topografía monocéntrica, +p y −p NO pueden dar lo mismo.
    por_pend = {f["pendiente_pct"]: f["t_borde_min"] for f in b["pendiente"]}
    b["pendiente_es_simetrica"] = bool(
        abs(por_pend[3.0] - por_pend[-3.0]) < 1e-9
        and abs(por_pend[6.0] - por_pend[-6.0]) < 1e-9
    )

    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap02.py",
            "configuracion": (
                "Oferta de la aplicación (`test_linea_base._config_web().supply`) sobre "
                "la ciudad por defecto: 201 celdas, 20 km. Las demandas son uniformes "
                "y sintéticas — el capítulo mide las funciones de costo, no el "
                "equilibrio, que es el capítulo 4."
            ),
        },
        "geometria_compartida": geometria_compartida(),
        "auto": auto(),
        "bici": b,
        "metro": metro(),
        "red_vacia": red_vacia(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    a = datos["auto"]
    print(
        f"Auto: k_j={a['densidad_embotellamiento_veh_km']} veh/km · v_l={a['v_libre_kmh']} km/h"
    )
    print(
        f"  capacidad teórica {a['capacidad_teorica_veh_h']} vs código {a['capacidad_del_codigo_veh_h']}"
    )
    print("\nMetro (Mohring):")
    for m in datos["metro"]["mohring"]:
        print(
            f"  d={m['demanda_por_celda']:>6}  f_teo={m['frecuencia_teorica_tph']:>8.3f}  "
            f"f_op={m['frecuencia_operativa_tph']:>6.3f}  topada={m['topada_en']:>8}  "
            f"espera={m['espera_media_min']:>6.3f}"
        )
    print("\nAndén (sobrecosto sobre la espera):")
    for x in datos["metro"]["anden"]:
        print(f"  d={x['demanda_por_celda']:>6}  {x['sobrecosto_pct']}%")
    print(f"\nBici: pendiente simétrica = {b['pendiente_es_simetrica']}")
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
