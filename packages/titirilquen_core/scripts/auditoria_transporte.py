"""Auditoría de sensibilidad del módulo de TRANSPORTE.

Barre cada parámetro de `SimulationConfig` por la MISMA ruta que usa la app
(`iter_msa_desde_suelo`) y reporta dirección y magnitud del efecto, para
verificar que el modelo responde como la teoría predice.

Correr desde packages/titirilquen_core:

    uv run python scripts/auditoria_transporte.py
"""

from __future__ import annotations

from _comun import (
    base_sim,
    con_bike,
    con_car,
    con_city,
    con_globales,
    con_train,
    corre,
    valida,
)

from titirilquen_core.config import SimulationConfig
from titirilquen_core.land_use.config import LandUseConfig


def encabezado(titulo: str) -> None:
    print(f"\n### {titulo}")
    print(
        f"{'escenario':<24} {'auto':>6} {'metro':>6} {'bici':>6} {'camin':>6} "
        f"{'tele':>6} {'v/c':>5} {'t_auto':>7} {'f_op':>6} {'CO2':>7} {'it':>3}"
    )
    print("-" * 100)


def fila(etiqueta: str, r: dict) -> None:
    print(
        f"{etiqueta:<24} {r['Auto']:>6.2f} {r['Metro']:>6.2f} {r['Bici']:>6.2f} "
        f"{r['Caminata']:>6.2f} {r['Teletrabajo']:>6.2f} {r['vc']:>5.2f} "
        f"{r['t_auto']:>7.1f} {r['f_op']:>6.1f} {r['co2']:>7.0f} {r['iters']:>3}"
        f"{'' if r['conv'] else '  SIN CONVERGER'}"
    )


def barrer(titulo: str, casos) -> None:
    encabezado(titulo)
    for caso in casos:
        # Un caso es (etiqueta, sim) y, opcionalmente, su uso de suelo: casi
        # ninguno lo cambia, así que exigirlo obligaba a arrastrar un `None`.
        etiqueta, sim, lu = (*caso, None)[:3]
        try:
            fila(etiqueta, corre(sim, lu))
        except Exception as e:
            print(f"{etiqueta:<24} ERROR {type(e).__name__}: {e}")


def con_raiz(**kw) -> SimulationConfig:
    """Parámetros de la raíz de `SimulationConfig` (max_iter, tolerance...).
    No está en `_comun` porque es el único caso donde `model_copy` sí valida:
    los campos son del propio modelo raíz."""
    return base_sim().model_copy(update=valida(base_sim(), kw))


def main() -> None:
    print("AUDITORÍA — MÓDULO DE TRANSPORTE")
    print("Base: 201 celdas · 20 km · ΣH=36.000 · expected · seed 42 · tol 0.1")

    b = base_sim()
    barrer("0. baseline", [("default", b)])

    barrer(
        "1. OFERTA AUTO",
        [(f"v_max {v}", con_car(v_max_kmh=v)) for v in (15, 31, 50, 80)]
        + [(f"pistas {n}", con_car(num_pistas=n)) for n in (1, 2, 4, 6)]
        + [(f"ancho {a}", con_car(ancho_pista_m=a)) for a in (2.5, 3.0, 3.5, 4.0)]
        + [(f"alpha_bpr {a}", con_car(alpha_bpr=a)) for a in (0.0, 0.8, 3.0)]
        + [(f"beta_bpr {a}", con_car(beta_bpr=a)) for a in (1.0, 2.0, 5.0)]
        + [(f"cap_pista {c}", con_car(capacidad_pista=c)) for c in (600, 1107, 2500)],
    )

    barrer(
        "2. OFERTA BICI",
        [(f"v_media {v}", con_bike(v_media_kmh=v)) for v in (8, 14, 25)]
        + [(f"capacidad {c}", con_bike(capacidad_pista=c)) for c in (400, 800, 2500, 6000)]
        + [(f"alpha_bpr {a}", con_bike(alpha_bpr=a)) for a in (0.0, 0.5, 3.0)]
        + [(f"beta_bpr {a}", con_bike(beta_bpr=a)) for a in (1.0, 2.0, 5.0)],
    )

    barrer(
        "3. OFERTA METRO",
        [(f"estaciones {n}", con_train(num_estaciones=n)) for n in (3, 10, 20, 30)]
        + [(f"v_tren {v}", con_train(v_tren_kmh=v)) for v in (15, 35, 70)]
        + [(f"cap_tren {c}", con_train(capacidad_tren=c)) for c in (100, 300, 1000)]
        + [(f"frec_min {f}", con_train(frec_min=f)) for f in (2, 6, 15)]
        + [(f"frec_max {f}", con_train(frec_max=f)) for f in (10, 30, 60)]
        + [(f"anden_alpha {a}", con_train(anden_alpha=a)) for a in (0.0, 0.5, 3.0)]
        + [(f"anden_beta {a}", con_train(anden_beta=a)) for a in (1.0, 4.0, 8.0)],
    )

    barrer(
        "4. ECONOMÍA / GLOBALES",
        [(f"parking {p}", con_globales(costo_parking=p)) for p in (0, 3000, 6000, 15000, 30000)]
        + [(f"bencina {c}", con_globales(costo_combustible_km=c)) for c in (50, 120, 300)]
        + [(f"tarifa {t}", con_globales(costo_tarifa_metro=t)) for t in (0, 800, 2000)]
        + [(f"v_caminata {v}", con_globales(v_caminata=v)) for v in (3.5, 4.8, 7.0)]
        + [(f"v_auto glob {v}", con_globales(v_auto=v)) for v in (31, 80)]
        + [(f"factor_flota {f}", con_globales(factor_flota_auto=f)) for f in (0.15, 1.0, 2.0)]
        + [(f"em_metro {f}", con_globales(factor_emision_metro_tren_km=f)) for f in (2.5, 10.0)],
    )

    barrer(
        "5. CIUDAD",
        [(f"largo {k}", con_city(largo_ciudad_km=k)) for k in (8, 20, 40)]
        + [(f"celdas {n}", con_city(n_celdas=n)) for n in (51, 201, 501)]
        + [(f"pendiente {p}", con_city(pendiente_porcentaje=p)) for p in (-8, 0, 8)]
        + [(f"tele_factor {f}", con_city(teletrabajo_factor=f)) for f in (0, 1, 2)]
        + [(f"densidad {d}", con_city(densidad_hab_km=d)) for d in (500, 1800, 5000)],
    )

    barrer(
        "6. EQUILIBRIO / RAÍZ",
        [(f"max_iter {n}", con_raiz(max_iter=n)) for n in (3, 20, 50)]
        + [(f"tolerance {t}", con_raiz(tolerance=t)) for t in (0.0, 0.1, 1.0)]
        + [
            ("assignment montecarlo", con_raiz(assignment="montecarlo")),
            ("modos sin bici", con_raiz(modos_habilitados=["Auto", "Metro", "Caminata"])),
            ("modos sin auto", con_raiz(modos_habilitados=["Metro", "Bici", "Caminata"])),
        ],
    )

    barrer(
        "7. ESCALA DE POBLACIÓN (ΣH del suelo)",
        [
            (
                f"ΣH={n}",
                base_sim(),
                LandUseConfig(
                    H_por_estrato=(int(n * 0.1), int(n * 0.4), int(n * 0.5)),
                    forma="normal",
                    oferta_sigma_frac=0.5,
                ),
            )
            for n in (9000, 36000, 72000)
        ],
    )


if __name__ == "__main__":
    main()
