"""Presets de ciudad y políticas — portados verbatim del repo original.

Referencias: `titirilquen-repo/app.py:19-35`.
"""

from __future__ import annotations

from typing import TypedDict


class CityPreset(TypedDict, total=False):
    largo_ciudad: int
    densidad: int
    # Concentración de la oferta de vivienda (σ del perfil, land_use/supply.py):
    # la otra dimensión de «forma urbana» además de la extensión — dónde vive la
    # gente DENTRO de la ciudad. Sin ella el preset movía la mitad del efecto.
    sigma: float


class PolicyPreset(TypedDict, total=False):
    tarifa: int
    parking: int
    num_pistas: int
    num_estaciones: int
    bencina: int
    cap_bici: int
    frec_max: int
    cap_tren: int


CITY_PRESETS: dict[str, CityPreset] = {
    "Personalizado": {},
    # Calibración ISO-POBLACIÓN (ΣH = 36.000): los tres presets comparan FORMA
    # urbana —extensión (largo) y concentración (sigma)— con la misma gente. La
    # densidad es la consecuencia (36.000/largo), no un input independiente.
    #
    # Rango ampliado respecto de la calibración original (12/20/30, sin sigma)
    # porque a iso-población ese rango movía la mitad del efecto: el contraste
    # compacta↔dispersa pasa de −15,6 a −36,5 pp en metro y de +10,8 a +28,6 pp
    # en caminata. El v/c NO contrasta en ninguna calibración: en una ciudad
    # monocéntrica el tramo junto al CBD carga ~la mitad de los viajes en auto
    # sea cual sea el largo, así que responde a población/precios/capacidad y no
    # a la forma.
    "Compacta": {"largo_ciudad": 8, "densidad": 4500, "sigma": 0.30},
    "Base": {"largo_ciudad": 20, "densidad": 1800, "sigma": 0.50},
    "Dispersa": {"largo_ciudad": 40, "densidad": 900, "sigma": 0.90},
}

POLICY_PRESETS: dict[str, PolicyPreset] = {
    "Personalizado": {},
    "TP Gratis": {
        "tarifa": 0, "parking": 6000, "num_pistas": 2, "num_estaciones": 10,
        "bencina": 120, "cap_bici": 800, "frec_max": 35, "cap_tren": 300,
    },
    "Tarificación Vial": {
        "tarifa": 800, "parking": 15000, "num_pistas": 2, "num_estaciones": 10,
        "bencina": 120, "cap_tren": 300, "cap_bici": 800, "frec_max": 20,
    },
    "Pro-Auto": {
        "tarifa": 1000, "parking": 3000, "num_pistas": 3, "num_estaciones": 8,
        "bencina": 100, "cap_tren": 250, "cap_bici": 500, "frec_max": 6,
    },
    "Pro-Bici": {
        "tarifa": 800, "parking": 6000, "num_pistas": 2, "cap_bici": 5000,
        "frec_max": 20, "bencina": 120, "cap_tren": 300, "num_estaciones": 10,
    },
    "Vehículos híbridos": {
        "num_pistas": 2, "bencina": 65, "tarifa": 800, "parking": 6000,
        "frec_max": 20, "cap_tren": 300, "num_estaciones": 10, "cap_bici": 800,
    },
    "Máx Metro": {
        "tarifa": 400, "num_estaciones": 20, "frec_max": 50, "cap_tren": 300,
        "parking": 6000, "bencina": 120, "num_pistas": 2, "cap_bici": 800,
    },
    "Ciclorrecreovía": {
        # `num_estaciones` faltaba (7 de 8 claves): la política heredaba el valor
        # vigente, así que aplicarla desde «Máx Metro» (20 est.) daba otro
        # escenario que aplicarla desde el default. Completada con 10 = default,
        # para que el preset sea reproducible.
        "num_pistas": 1, "cap_bici": 6000, "tarifa": 800, "parking": 6000,
        "bencina": 120, "frec_max": 20, "cap_tren": 300, "num_estaciones": 10,
    },
}


DEFAULT_STRATA = {
    1: {
        "prob_teletrabajo": 0.40,
        "prob_auto": 0.90,
        "prob_jornada_flexible": 0.50,
        "prob_part_time": 0.05,
        "jornada": {"horas_rigido": 9.0, "horas_flexible": 8.0, "horas_part_time": 4.0},
        "betas": {
            "asc_auto": 1.5, "asc_metro": -0.2, "asc_bici": -0.9, "asc_caminata": -0.5,
            "b_tiempo_viaje": -0.055, "b_costo": -0.00008, "b_tiempo_espera": -0.05,
            "b_tiempo_caminata": -0.15,
            "penalizaciones_fisicas": {
                "bici_10": -0.09, "bici_20": -0.15, "bici_30": -0.5,
                "walk_5": -0.09, "walk_15": -0.18, "walk_25": -0.4,
            },
        },
    },
    2: {
        "prob_teletrabajo": 0.20,
        "prob_auto": 0.60,
        "prob_jornada_flexible": 0.30,
        "prob_part_time": 0.10,
        "jornada": {"horas_rigido": 9.0, "horas_flexible": 8.5, "horas_part_time": 4.5},
        "betas": {
            "asc_auto": 0.7889, "asc_metro": 0.1040, "asc_bici": -0.6818, "asc_caminata": 0.1,
            "b_tiempo_viaje": -0.0331, "b_costo": -0.0002, "b_tiempo_espera": -0.0243,
            "b_tiempo_caminata": -0.0440,
            "penalizaciones_fisicas": {
                "bici_10": -0.0634, "bici_20": -0.1, "bici_30": -0.4,
                "walk_5": -0.05, "walk_15": -0.09, "walk_25": -0.2,
            },
        },
    },
    3: {
        "prob_teletrabajo": 0.05,
        "prob_auto": 0.30,
        "prob_jornada_flexible": 0.10,
        "prob_part_time": 0.15,
        "jornada": {"horas_rigido": 9.5, "horas_flexible": 9.0, "horas_part_time": 5.0},
        "betas": {
            "asc_auto": 0.2, "asc_metro": 0.25, "asc_bici": -0.4, "asc_caminata": 0.4,
            "b_tiempo_viaje": -0.0150, "b_costo": -0.0006, "b_tiempo_espera": -0.0150,
            "b_tiempo_caminata": -0.0250,
            "penalizaciones_fisicas": {
                "bici_10": -0.0300, "bici_20": -0.0500, "bici_30": -0.7,
                "walk_5": -0.0250, "walk_15": -0.0400, "walk_25": -0.08,
            },
        },
    },
}
