"""Presets de ciudad y políticas — portados verbatim del repo original.

Referencias: `titirilquen-repo/app.py:19-35`.
"""

from __future__ import annotations

from typing import TypedDict


class CityPreset(TypedDict, total=False):
    largo_ciudad: int
    densidad: int
    # Concentración de la oferta de vivienda (sigma del perfil, land_use/supply):
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
    # Multiplicador de la emisión por km del auto (composición de la flota).
    factor_flota: float


CITY_PRESETS: dict[str, CityPreset] = {
    "Personalizado": {},
    # Calibración ISO-POBLACIÓN (ΣH = 36.000): los tres presets comparan FORMA
    # urbana —extensión (largo) y concentración (sigma)— con la misma gente. La
    # densidad es la consecuencia (36.000/largo), no un input independiente.
    #
    # Rango ampliado respecto de la calibración original (12/20/30, sin sigma)
    # porque a iso-población ese rango movía la mitad del efecto: el contraste
    # compacta-dispersa pasa de -15,6 a -36,5 pp en metro y de +10,8 a +28,6 pp
    # en caminata. El v/c NO contrasta en ninguna calibración: en una ciudad
    # monocéntrica el tramo junto al CBD carga ~la mitad de los viajes en auto
    # sea cual sea el largo, así que responde a población/precios/capacidad y no
    # a la forma.
    "Compacta": {"largo_ciudad": 8, "densidad": 4500, "sigma": 0.30},
    "Base": {"largo_ciudad": 20, "densidad": 1800, "sigma": 0.50},
    "Dispersa": {"largo_ciudad": 40, "densidad": 900, "sigma": 0.90},
}

# REGLA GENERAL: los presets declaran valores ABSOLUTOS, no diffs. Cada vez que
# se recalibra un default hay que moverlos, o aplicar cualquier política revierte
# ese parámetro en silencio. Los valores neutros van al default; los deliberados
# se reescalan manteniendo su RAZÓN contra la base, que es lo que define su
# intensidad. Ya pasó dos veces (`frec_max: 20` y `parking: 6000`).
#
# Recalibración vigente — defaults: parking 4000 · 2 pistas · cap_bici 2500 ·
# frec_max 40. Deliberados reescalados: Tarificación Vial parking 2.5x (10000),
# Pro-Auto parking 0.5x (2000) y una pista más que la base (3), Ciclorrecreovía
# una menos (1). Sin reescalar, Pro-Auto habría quedado más caro que la base y
# con menos pistas, invirtiendo su sentido.
#
# `frec_max` de las metro-friendly (TP Gratis y Máx Metro) queda en 50, por
# encima del default: un tope PERMISIVO es inocuo si no muerde, mientras que uno
# restrictivo degrada en silencio. Pro-Auto conserva 6 porque estrangular el
# metro es justamente su política.
#
# PRECEDENTE (por qué existe la regla de arriba): cuatro políticas declaraban
# `frec_max: 20`, el default ANTIGUO. D-18 recalibró el rango y no se
# actualizaron, así que ese 20 quedó capando el metro POR DEBAJO del default en
# políticas que ni siquiera son sobre el metro — degradación no declarada: la
# espera máxima se cuadruplicaba (6.98 vs 1.78 min en Tarificación Vial).
POLICY_PRESETS: dict[str, PolicyPreset] = {
    "Personalizado": {},
    # Política de referencia: TODOS los parámetros en su default. No es lo mismo
    # que «Personalizado», que es el dict vacío y por lo tanto hereda lo que
    # haya vigente. «Base» es reproducible: aplicarla desde cualquier escenario
    # deja siempre la misma ciudad, y da la fila de referencia de la tabla.
    "Base": {
        "tarifa": 800,
        "parking": 4000,
        "num_pistas": 2,
        "num_estaciones": 10,
        "bencina": 120,
        "cap_bici": 2500,
        "frec_max": 40,
        "cap_tren": 300,
        "factor_flota": 1.0,
    },
    "TP Gratis": {
        "tarifa": 0,
        "parking": 4000,
        "num_pistas": 2,
        "num_estaciones": 10,
        "bencina": 120,
        "cap_bici": 2500,
        "frec_max": 50,
        "cap_tren": 300,
    },
    "Tarificación Vial": {
        "tarifa": 800,
        "parking": 10000,
        "num_pistas": 2,
        "num_estaciones": 10,
        "bencina": 120,
        "cap_tren": 300,
        "cap_bici": 2500,
        "frec_max": 40,
    },
    "Pro-Auto": {
        "tarifa": 1000,
        "parking": 2000,
        "num_pistas": 3,
        "num_estaciones": 8,
        "bencina": 100,
        "cap_tren": 250,
        "cap_bici": 1250,
        "frec_max": 6,
    },
    "Pro-Bici": {
        "tarifa": 800,
        "parking": 4000,
        "num_pistas": 2,
        "cap_bici": 5000,
        "frec_max": 40,
        "bencina": 120,
        "cap_tren": 300,
        "num_estaciones": 10,
    },
    "Vehículos híbridos": {
        # AHORA sí reduce la emisión por km: antes solo abarataba la bencina, o
        # sea abarataba el auto y terminaba SUBIENDO el CO2 (+1.6% medido).
        "num_pistas": 2,
        "bencina": 65,
        "tarifa": 800,
        "parking": 4000,
        "frec_max": 40,
        "cap_tren": 300,
        "num_estaciones": 10,
        "cap_bici": 2500,
        "factor_flota": 0.7,
    },
    "Máx Metro": {
        "tarifa": 400,
        "num_estaciones": 20,
        "frec_max": 50,
        "cap_tren": 300,
        "parking": 4000,
        "bencina": 120,
        "num_pistas": 2,
        "cap_bici": 2500,
    },
    "Ciclorrecreovía": {
        # `num_estaciones` faltaba (7 de 8 claves): la política heredaba el valor
        # vigente, así que aplicarla desde «Máx Metro» (20 est.) daba otro
        # escenario que aplicarla desde el default. Completada con 10 = default,
        # para que el preset sea reproducible.
        "num_pistas": 1,
        "cap_bici": 6000,
        "tarifa": 800,
        "parking": 4000,
        "bencina": 120,
        "frec_max": 40,
        "cap_tren": 300,
        "num_estaciones": 10,
    },
}


# RECALIBRACION ago-2026. Ver scripts/diagnostico_calibracion.py, que imprime
# los coeficientes en minutos-equivalentes (= util / b_tiempo_viaje, donde la
# escala de utilidad de cada estrato se cancela y recien ahi son comparables).
# Tres correcciones, todas sobre razones INTERNAS de cada estrato:
#
#  * `b_tiempo_espera` = 2.0 x `b_tiempo_viaje`. Antes daba 0.91 / 0.73 / 1.00,
#    o sea el modelo afirmaba que esperar en un anden molesta MENOS que ir
#    sentado. Ademas subvaluaba el efecto Mohring, que opera justamente por la
#    espera: mas frecuencia -> menos espera -> mas demanda -> mas frecuencia.
#  * `b_tiempo_caminata` = 1.7 x `b_tiempo_viaje`. Antes 2.73 / 1.33 / 1.67, sin
#    patron, y en los tres estratos POR ENCIMA de la espera. Queda el orden
#    viaje < caminata < espera. Ojo: este beta pesa el acceso al metro Y el modo
#    caminata completo (utility.py), asi que mueve dos cosas a la vez.
#  * `b_costo` se despeja del valor del tiempo pedido (6.200 / 3.100 / 1.600
#    $/hora): b_costo = b_tiempo_viaje * 60 / VoT. Se ajusta el coeficiente de
#    COSTO y no el de tiempo a proposito: `b_tiempo_viaje` es el denominador de
#    los minutos-equivalentes, asi que dejarlo fijo preserva el significado de
#    las ASC y de las penalizaciones, que quedaron pendientes de revisar.
#    Efecto lateral grande: el estrato alto pasa a ser 6.7x mas sensible al
#    dinero, o sea las palancas de precio recien empiezan a morder.
#
# Las ASC NO se tocaron. Siguen pesando 31 / 21 / 3 minutos-equivalentes en el
# auto y 13 / 24 / 43 en la bici, que es la razon de fondo de que la
# infraestructura mueva poco el reparto del estrato bajo.
DEFAULT_STRATA = {
    1: {
        "prob_teletrabajo": 0.40,
        "prob_auto": 0.90,
        "prob_jornada_flexible": 0.50,
        "prob_part_time": 0.05,
        "jornada": {"horas_rigido": 9.0, "horas_flexible": 8.0, "horas_part_time": 4.0},
        "betas": {
            "asc_auto": 1.5,
            "asc_metro": -0.2,
            "asc_bici": -0.9,
            "asc_caminata": -0.5,
            "b_tiempo_viaje": -0.055,
            "b_costo": -0.00053226,  # VoT 6.200 $/h
            "b_tiempo_espera": -0.11,  # 2.0 x viaje
            "b_tiempo_caminata": -0.0935,  # 1.7 x viaje
            "penalizaciones_fisicas": {
                "bici_10": -0.09,
                "bici_20": -0.15,
                "bici_30": -0.5,
                "walk_5": -0.09,
                "walk_15": -0.18,
                "walk_25": -0.4,
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
            "asc_auto": 0.7889,
            "asc_metro": 0.1040,
            "asc_bici": -0.6818,
            "asc_caminata": 0.1,
            "b_tiempo_viaje": -0.0331,
            "b_costo": -0.00064065,  # VoT 3.100 $/h
            "b_tiempo_espera": -0.0662,  # 2.0 x viaje
            "b_tiempo_caminata": -0.05627,  # 1.7 x viaje
            "penalizaciones_fisicas": {
                "bici_10": -0.0634,
                "bici_20": -0.1,
                "bici_30": -0.4,
                "walk_5": -0.05,
                "walk_15": -0.09,
                "walk_25": -0.2,
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
            "asc_auto": 0.2,
            "asc_metro": 0.25,
            "asc_bici": -0.4,
            "asc_caminata": 0.4,
            "b_tiempo_viaje": -0.0150,
            "b_costo": -0.0005625,  # VoT 1.600 $/h
            "b_tiempo_espera": -0.03,  # 2.0 x viaje
            "b_tiempo_caminata": -0.0255,  # 1.7 x viaje
            "penalizaciones_fisicas": {
                "bici_10": -0.0300,
                "bici_20": -0.0500,
                # -0.20 (antes -0.7). El -0.7 rompia la pauta: en las otras
                # cinco celdas este estrato es ~0.49x el medio, y ahi era 1.75x.
                # Con su b_tiempo_viaje chico eso daba 46.7 minutos-equivalentes
                # contra 9.1 y 12.1 de los otros dos, o sea un viaje en bici de
                # 31 min se evaluaba como uno de 83 y mataba el modo justo en el
                # estrato que mas lo usa. 0.49 x 0.40 = 0.196 -> -0.20.
                "bici_30": -0.20,
                "walk_5": -0.0250,
                "walk_15": -0.0400,
                "walk_25": -0.08,
            },
        },
    },
}
