"""Presets de ciudad y políticas — portados verbatim del repo original.

Referencias: `titirilquen-repo/app.py:19-35`.
"""

from __future__ import annotations

from typing import TypedDict


class CityPreset(TypedDict, total=False):
    largo_ciudad: int
    # Concentración de la oferta de vivienda (sigma del perfil, land_use/supply):
    # la otra dimensión de «forma urbana» además de la extensión — dónde vive la
    # gente DENTRO de la ciudad. Sin ella el preset movía la mitad del efecto.
    sigma: float
    # Población total (ΣH). Presente solo en los presets que fijan la ESCALA;
    # si falta, el preset conserva la población vigente (iso-población). Ver el
    # bloque de CITY_PRESETS.
    poblacion: int
    # Pistas por sentido. Va en el preset de CIUDAD —y no solo en los de
    # política— porque a una escala dada la capacidad vial no es neutra: con
    # 144.000 habitantes las 2 pistas del default dejan el corredor en v/c 3,68
    # y el auto en 52 min, o sea saturado POR CONSTRUCCIÓN, y el escenario deja
    # de estar en la rodilla de la BPR donde las palancas responden. Lo declaran
    # los mismos presets que declaran `poblacion`: los que fijan la escala.
    num_pistas: int


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
    # densidad es la consecuencia (36.000/largo), no un input: desde sep-2026
    # ni siquiera es un campo (D-46).
    #
    # Rango ampliado respecto de la calibración original (12/20/30, sin sigma)
    # porque a iso-población ese rango movía la mitad del efecto: el contraste
    # compacta-dispersa pasa de -15,6 a -36,5 pp en metro y de +10,8 a +28,6 pp
    # en caminata. El v/c NO contrasta en ninguna calibración: en una ciudad
    # monocéntrica el tramo junto al CBD carga ~la mitad de los viajes en auto
    # sea cual sea el largo, así que responde a población/precios/capacidad y no
    # a la forma.
    "Compacta": {"largo_ciudad": 8, "sigma": 0.30},
    # `num_pistas` declarado por la misma razón que `poblacion`: para que el
    # viaje de VUELTA funcione. Sin esto, volver de Metrópolis dejaba la ciudad
    # de 36.000 habitantes con las 12 pistas de la metrópolis y un v/c de 0,25,
    # o sea un corredor vacío donde ninguna palanca de auto hace nada.
    "Base": {
        "largo_ciudad": 20,
        "sigma": 0.50,
        "poblacion": 36_000,
        "num_pistas": 2,
    },
    "Dispersa": {"largo_ciudad": 40, "sigma": 0.90},
    # ESCALA, no forma: misma geometría que Base (20 km, sigma 0.50) con 4x la
    # población. Es el único preset que rompe la iso-población de arriba, y a
    # propósito: aísla la dimensión que los otros tres mantienen fija.
    #
    # Régimen opuesto al default. Medido (wardrop, barrido de pistas 1->4):
    #   36.000 hab  -> f_op 7.1->4.7 tph, espera 4.1->6.0 min  (Mohring empinado)
    #  144.000 hab  -> f_op 40.0->38.3 tph, espera 1.1->1.2 min (Mohring plano)
    # porque espera = 30K/L_max: mas demanda => menos espera => nada que
    # degradar. Downs-Thomson NO se observa acá; lo que muerde es el andén
    # (rho = L_max/(f_max*K) pasa de 0.15 a 0.86, +27% sobre la espera).
    # Ver docs/CONTINUAR.md §4.1c.
    "Metrópolis": {
        "largo_ciudad": 20,
        "sigma": 0.50,
        "poblacion": 144_000,
        # 12 y no 2: es el número que deja el corredor en v/c 0,97 con esta
        # población, o sea la MISMA condición que las 2 pistas dan en Base. Con
        # el default de 2 el v/c era 3,68 y el auto tardaba 52,3 min: no competía
        # con el metro y agregar vialidad no movía nada porque la BPR ya estaba
        # muy pasada la rodilla. Medido (expected, ΣH 144.000):
        #
        #   pistas   v/c    auto%   metro%   t_auto
        #        2   3,68   11,33    47,54   52,3 min
        #        4   2,44   15,00    45,15   34,8
        #        8   1,41   17,30    43,37   24,5
        #       12   0,97   17,95    42,93   21,7   <- rodilla
        #
        # Ojo con leer las 12 pistas como un dato urbano: en la ciudad lineal
        # TODA la población atraviesa un único corredor, así que este número
        # agrega la capacidad vial completa de la ciudad, no la de una avenida.
        "num_pistas": 12,
    },
}

# REGLA GENERAL: los presets declaran valores ABSOLUTOS, no diffs. Cada vez que
# se recalibra un default hay que moverlos, o aplicar cualquier política revierte
# ese parámetro en silencio. Los valores neutros van al default; los deliberados
# se reescalan manteniendo su RAZÓN contra la base, que es lo que define su
# intensidad. Ya pasó dos veces (`frec_max: 20` y `parking: 6000`).
#
# Recalibración vigente — defaults: parking 2000 · 2 pistas · cap_bici 2500 ·
# frec_max 40. Deliberados reescalados: Tarificación Vial parking 2.5x (5000),
# Pro-Auto parking 0.5x (1000) y una pista más que la base (3), Ciclorrecreovía
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
        "parking": 2000,
        "num_pistas": 2,
        "num_estaciones": 10,
        "bencina": 120,
        "cap_bici": 2500,
        "frec_max": 40,
        "cap_tren": 1000,
        "factor_flota": 1.0,
    },
    "TP Gratis": {
        "tarifa": 0,
        "parking": 2000,
        "num_pistas": 2,
        "num_estaciones": 10,
        "bencina": 120,
        "cap_bici": 2500,
        "frec_max": 50,
        "cap_tren": 1000,
        # Sin declararlo, aplicar esta politica DESPUES de «Vehiculos
        # hibridos» dejaba la flota en 0.7 en silencio.
        "factor_flota": 1.0,
    },
    "Tarificación Vial": {
        "tarifa": 800,
        "parking": 5000,
        "num_pistas": 2,
        "num_estaciones": 10,
        "bencina": 120,
        "cap_tren": 1000,
        "cap_bici": 2500,
        "frec_max": 40,
        # Sin declararlo, aplicar esta politica DESPUES de «Vehiculos
        # hibridos» dejaba la flota en 0.7 en silencio.
        "factor_flota": 1.0,
    },
    "Pro-Auto": {
        "tarifa": 1000,
        "parking": 1000,
        "num_pistas": 3,
        "num_estaciones": 8,
        "bencina": 100,
        "cap_tren": 800,
        "cap_bici": 1250,
        "frec_max": 6,
        # Sin declararlo, aplicar esta politica DESPUES de «Vehiculos
        # hibridos» dejaba la flota en 0.7 en silencio.
        "factor_flota": 1.0,
    },
    "Pro-Bici": {
        "tarifa": 800,
        "parking": 2000,
        "num_pistas": 2,
        "cap_bici": 5000,
        "frec_max": 40,
        "bencina": 120,
        "cap_tren": 1000,
        "num_estaciones": 10,
        # Sin declararlo, aplicar esta politica DESPUES de «Vehiculos
        # hibridos» dejaba la flota en 0.7 en silencio.
        "factor_flota": 1.0,
    },
    "Vehículos híbridos": {
        # AHORA sí reduce la emisión por km: antes solo abarataba la bencina, o
        # sea abarataba el auto y terminaba SUBIENDO el CO2 (+1.6% medido).
        "num_pistas": 2,
        "bencina": 65,
        "tarifa": 800,
        "parking": 2000,
        "frec_max": 40,
        "cap_tren": 1000,
        "num_estaciones": 10,
        "cap_bici": 2500,
        "factor_flota": 0.7,
    },
    "Máx Metro": {
        "tarifa": 400,
        "num_estaciones": 20,
        "frec_max": 50,
        "cap_tren": 1000,
        "parking": 2000,
        "bencina": 120,
        "num_pistas": 2,
        "cap_bici": 2500,
        # Sin declararlo, aplicar esta politica DESPUES de «Vehiculos
        # hibridos» dejaba la flota en 0.7 en silencio.
        "factor_flota": 1.0,
    },
    "Ciclorrecreovía": {
        # `num_estaciones` faltaba (7 de 8 claves): la política heredaba el valor
        # vigente, así que aplicarla desde «Máx Metro» (20 est.) daba otro
        # escenario que aplicarla desde el default. Completada con 10 = default,
        # para que el preset sea reproducible.
        "num_pistas": 1,
        "cap_bici": 6000,
        "tarifa": 800,
        "parking": 2000,
        "bencina": 120,
        "frec_max": 40,
        "cap_tren": 1000,
        "num_estaciones": 10,
        # Sin declararlo, aplicar esta politica DESPUES de «Vehiculos
        # hibridos» dejaba la flota en 0.7 en silencio.
        "factor_flota": 1.0,
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
#  * El peso del tiempo caminando se PARTIO EN DOS, porque un solo coeficiente
#    pesaba el acceso al metro y el modo caminata completo, que no son lo mismo:
#      - `b_tiempo_acceso` = 2.0 x viaje. Valor de NORMA: Precios Sociales 2026
#        del SNI, Tabla 2.1, ponderador 2, acotado a «usuarios de transporte
#        publico mayor» y, en viajes combinados, «solo el tramo de transporte
#        publico» — o sea exactamente este termino.
#      - `b_tiempo_caminata` = 1.7 x viaje, para el viaje entero a pie. NO esta
#        cubierto por esa tabla; es un juicio, no una norma.
#    Antes ambos eran el mismo numero y daban 2.73 / 1.33 / 1.67, sin patron y
#    en los tres estratos POR ENCIMA de la espera.
#  * `b_costo` se despeja del valor del tiempo pedido (6.200 / 3.100 / 1.600
#    $/hora): b_costo = b_tiempo_viaje * 60 / VoT. En ago-2026 se ajusto SOLO el
#    coeficiente de costo, dejando `b_tiempo_viaje` en los valores heredados
#    (0.055 / 0.0331 / 0.015) para no mover los minutos-equivalentes. Eso dejo
#    un `b_costo` NO monotono (0.000532 / 0.000641 / 0.000563: el medio valoraba
#    mas un peso que el bajo), que no era una preferencia sino el residuo de
#    cuadrar el VoT sobre escalas heredadas. Corregido abajo (sep-2026).
#
# HOMOSCEDASTICO (sep-2026). `b_tiempo_viaje` = 0.0331 en los TRES estratos.
#
# Multiplicar TODO el bloque de betas de un estrato por una constante k (ASC,
# los cuatro tiempos, costo y penalizaciones) no cambia ninguna razon interna:
# conserva los minutos-equivalentes, el VoT y las ASC en minutos. Lo unico que
# cambia es la escala del ruido Gumbel de ese estrato (U' = k*V + eps es V + eps/k).
# O sea que `b_tiempo_viaje` distinto por estrato NO era una preferencia por el
# tiempo: era heteroscedasticidad — el alto elegia modo con un ruido 3.7x menor
# que el bajo, herencia del original que nadie decidio. Se reescalo el alto por
# k = 0.0331/0.055 y el bajo por k = 0.0331/0.015; el medio queda intacto.
#
# Consecuencias: (1) `b_costo` = 0.0331*60/VoT sale MONOTONO solo — 0.000320 /
# 0.000641 / 0.001241 — o sea la utilidad marginal del ingreso decrece con el
# ingreso, que es la unica pieza de esto con teoria detras; toda la
# heterogeneidad del VoT vive ahi. (2) Un hogar, una funcion de utilidad: el
# modulo de uso de suelo importa esta anatomia (alpha comun, lambda_h ∝
# b_costo_h), ver `land_use/config.py` y `tests/test_vot_consistente.py`.
# (3) La linea base se movio y esta declarada en `tests/test_linea_base.py`.
# Invariantes fijados en `tests/test_presets.py`.
#
# ASC SIN GRADIENTE DE INGRESO (ago-2026). Las cuatro constantes quedan fijadas
# como una ventaja COMUN a los tres estratos, medida en minutos de viaje sobre el
# metro: auto +20, bici -18, caminata 0, metro 0 por definicion.
#
# Antes llevaban un gradiente propio (auto +30.9/+20.7/-3.3, bici -12.7/-23.7/
# -43.3, caminata -5.5/-0.1/+10.0) que se SUMABA al del valor del tiempo. No era
# error de origen: venian de la calibracion hecha cuando la dispersion del VoT
# era 27.5x, donde el canal de gustos explicaba solo el 19% de la brecha
# auto-metro. Al comprimir esa dispersion a 3.9x (VoT 6.200/3.100/1.600) el mismo
# gradiente de gustos paso a explicar el 41%, o sea el ingreso entraba dos veces.
#
# Ahora el gradiente de uso del auto por estrato EMERGE del valor del tiempo y
# de la disponibilidad de auto, que es donde el ingreso debe entrar. Medido en
# sep-2026 con las escalas homoscedasticas, % de auto sobre los VIAJEROS del
# estrato (sin teletrabajo), corrida por defecto de la app sin uso de suelo:
# 47.7 / 22.6 / 3.7. (Aqui decia «46.3 / 19.2 / 6.4» sin denominador ni fecha y
# no se pudo reproducir; con las escalas heredadas daba 57.4 / 22.0 / 5.8.)
#
# Los valores comunes se eligieron para que el agregado no se moviera
# (auto 11.99 vs 12.16, v/c 0.97 vs 0.99): son neutrales respecto de la
# calibracion, NO estimados. Con una EOD que de reparto modal por estrato hay que
# reemplazarlos por el ajuste estandar ASC += ln(objetivo/modelo).
#
# La formula para leerlos: ventaja_min = -(asc_m - asc_metro) / b_tiempo_viaje.
# Antes de esto, las ASC pesaban 31 / 21 / 3 minutos-equivalentes en el
# auto y 13 / 24 / 43 en la bici, que es la razon de fondo de que la
# infraestructura mueva poco el reparto del estrato bajo.
DEFAULT_STRATA = {
    # Estratos alto y bajo reescalados por k = 0.0331/b_t_heredado (sep-2026, ver
    # HOMOSCEDASTICO arriba). Los comentarios "x viaje" y los minutos de las ASC
    # se conservan exactos porque todo el bloque se multiplico por el mismo k.
    1: {
        "prob_teletrabajo": 0.40,
        "prob_auto": 0.90,
        "betas": {
            "asc_auto": 0.54164,  # +20 min sobre el metro (era 0.9 con b_t 0.055)
            "asc_metro": -0.12036,
            "asc_bici": -0.71616,  # -18 min
            "asc_caminata": -0.12036,  # 0 min
            "b_tiempo_viaje": -0.0331,
            "b_costo": -0.000320323,  # VoT 6.200 $/h
            "b_tiempo_espera": -0.0662,  # 2.0 x viaje
            "b_tiempo_acceso": -0.0662,  # 2.0 x viaje (ponderador 2 del SNI)
            "b_tiempo_caminata": -0.05627,  # 1.7 x viaje
            "penalizaciones_fisicas": {
                "bici_10": -0.054164,
                "bici_20": -0.090273,
                "bici_30": -0.30091,
                "walk_5": -0.054164,
                "walk_15": -0.10833,
                "walk_25": -0.24073,
            },
        },
    },
    2: {
        "prob_teletrabajo": 0.20,
        "prob_auto": 0.60,
        "betas": {
            "asc_auto": 0.766,
            "asc_metro": 0.1040,
            "asc_bici": -0.4918,
            "asc_caminata": 0.104,
            "b_tiempo_viaje": -0.0331,
            "b_costo": -0.00064065,  # VoT 3.100 $/h
            "b_tiempo_espera": -0.0662,  # 2.0 x viaje
            "b_tiempo_acceso": -0.0662,  # 2.0 x viaje (ponderador 2 del SNI)
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
        "prob_auto": 0.25,
        "betas": {
            "asc_auto": 1.2137,  # +20 min sobre el metro (era 0.55 con b_t 0.015)
            "asc_metro": 0.55167,
            "asc_bici": -0.044133,  # -18 min
            "asc_caminata": 0.55167,  # 0 min
            "b_tiempo_viaje": -0.0331,
            "b_costo": -0.00124125,  # VoT 1.600 $/h
            "b_tiempo_espera": -0.0662,  # 2.0 x viaje
            "b_tiempo_acceso": -0.0662,  # 2.0 x viaje (ponderador 2 del SNI)
            "b_tiempo_caminata": -0.05627,  # 1.7 x viaje
            "penalizaciones_fisicas": {
                "bici_10": -0.0662,
                "bici_20": -0.11033,
                # Era -0.20 con b_t 0.015 (y antes -0.7, que rompia la pauta: en
                # las otras cinco celdas este estrato es ~0.49x el medio y ahi
                # era 1.75x; 0.49 x 0.40 = 0.196 -> -0.20). Reescalado por k.
                "bici_30": -0.44133,
                "walk_5": -0.055167,
                "walk_15": -0.088267,
                "walk_25": -0.17653,
            },
        },
    },
}
