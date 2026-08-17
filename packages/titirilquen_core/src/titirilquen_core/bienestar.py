"""Agregados de bienestar de la ciudad completa.

Responde la pregunta que el reparto modal no contesta: ¿esta política mejora al
sistema? Un modo puede mejorar mientras el conjunto empeora.

Por qué está acá y no en el frontend
------------------------------------
Hasta agosto de 2026 esto vivía íntegro en `apps/web/src/lib/agregados.ts`, en
TypeScript, apoyado en una reimplementación a mano de la función de utilidad
del núcleo. O sea: los indicadores de bienestar que el estudiante compara entre
escenarios se calculaban con 250 líneas de matemática duplicada, sin un solo
test. Acá corren una vez por simulación —no hay restricción de interactividad—
y son la misma implementación que ya decide la elección de modo.

Tres medidas separadas a propósito, porque responden preguntas distintas:

1. **Tiempo total** (persona-minutos): el agregado físico, sin supuestos de
   valoración.

2. **Costo generalizado**, en dos versiones que no son intercambiables:

   * *percibido*: valora el tiempo con el VoT CONDUCTUAL de cada estrato
     (β_tiempo/β_costo). Es el único consistente con el modelo — es literalmente
     el trade-off con que el logit elige.
   * *social*: valor del tiempo ÚNICO. El conductual implica que un minuto del
     estrato alto vale varias veces el del bajo; eso es un juicio distributivo,
     no un dato técnico, y en evaluación social se reemplaza por un valor de
     norma para no sesgar hacia proyectos que sirven a los de mayor ingreso.

3. **Excedente del consumidor**, en la medida que corresponda al método de
   asignación. Ambas se dividen por λ = −β_costo para quedar en pesos, y ambas
   reemplazan a la "utilidad media", que no significa nada: promediar utilidades
   entre personas no es bienestar.

   * *logsum*: `ln Σ_m e^{V_m}`. Es `E[max_m (V_m + ε_m)]` con ε Gumbel iid — o
     sea, el bienestar del agente que el LOGIT describe (`montecarlo` y
     `expected`).
   * *utilidad máxima*: `max_m V_m`. Bajo `todo_o_nada` no hay ε: el agente toma
     determinísticamente el mejor modo, y su `E[max]` es simplemente el máximo.

   **No son intercambiables, y la diferencia no es un desplazamiento constante.**
   Por log-sum-exp `ln Σ e^{V_m} ≥ max_m V_m`, con brecha acotada por
   `ln(nº modos factibles)`: es el valor que el logit le atribuye a la dispersión
   de gustos. Como el número de modos factibles cambia entre escenarios (una
   política puede volver infactible la bici), la brecha también cambia, y usar el
   logsum bajo `todo_o_nada` contamina justamente el Δ. De ahí `medida_bienestar`
   — el núcleo dice cuál está emparejada con el método, y la UI no reimplementa
   esa regla.

   **El nivel tiene cero arbitrario** (incluye las constantes específicas), así
   que sólo la DIFERENCIA contra otro escenario es interpretable. Este módulo
   entrega el nivel; quién resta contra qué es decisión de cada consumidor —el
   Sandbox contra el escenario que el usuario fija como referencia, la página
   acoplada contra la red vacía (`coupled_metrics._tiempos_red_vacia`). Las dos
   lecturas son válidas y responden preguntas distintas; lo que no puede haber
   es dos implementaciones de la matemática.

   La página acoplada todavía calcula su propio logsum en `coupled_metrics.py` y
   NO aplica este emparejamiento: quedó fuera del alcance a propósito.
"""

from __future__ import annotations

from typing import Literal, TypedDict

import numpy as np

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig, StratumId
from titirilquen_core.constantes import MODOS, VOT_SOCIAL_CLP_HORA
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace

#: Los estratos como llegan al JSON. Las claves de un objeto JSON son strings,
#: así que `dict[StratumId, ...]` de Python cruza como "1"/"2"/"3"; declararlo
#: exacto le dice a TypeScript que están las tres y no hace falta chequear.
EstratoKey = Literal["1", "2", "3"]


class AgregadosDict(TypedDict):
    """Indicadores de ciudad completa para la tabla de resultados."""

    #: Persona-minutos de todos los viajeros.
    tiempo_total_min: float
    #: Viajeros físicos (excluye teletrabajo).
    viajeros: float
    tiempo_medio_min: float
    #: Tiempo valorado al VoT conductual de cada estrato, más dinero.
    costo_generalizado_percibido_clp: float
    #: Ídem con un VoT único (evaluación social).
    costo_generalizado_social_clp: float
    #: Valor del tiempo conductual por estrato ($/hora) = β_t/β_c · 60.
    vot_por_estrato_clp_hora: dict[EstratoKey, float]
    #: Logsum medio por estrato (útiles) y su equivalente en pesos (÷ λ_h).
    #: Emparejado con `montecarlo` y `expected`.
    logsum_por_estrato: dict[EstratoKey, float]
    excedente_por_estrato_clp: dict[EstratoKey, float]
    #: Utilidad máxima media por estrato (útiles) y en pesos. Emparejada con
    #: `todo_o_nada`, donde no hay término aleatorio que promediar.
    util_maxima_por_estrato: dict[EstratoKey, float]
    excedente_max_por_estrato_clp: dict[EstratoKey, float]
    viajeros_por_estrato: dict[EstratoKey, float]
    #: Σ_h viajeros_h · excedente_h. Cero arbitrario: sólo el Δ es interpretable.
    excedente_total_clp: float
    excedente_max_total_clp: float
    #: Cuál de las dos medidas corresponde al `assignment` de esta corrida. La
    #: regla se decide acá y no en la UI: es matemática, no presentación.
    medida_bienestar: Literal["logsum", "utilidad_maxima"]
    #: Recaudación de estacionamiento. Es TRANSFERENCIA, no consumo de recursos:
    #: alguien la recibe. La bencina NO entra — ésa sí se consume.
    recaudacion_parking_clp: float
    recaudacion_tarifa_clp: float
    #: Tren-km por hora del servicio (f_op · largo de línea · 2).
    tren_km_hora: float
    #: Costo de operación del metro. A diferencia de la tarifa, sí es consumo.
    costo_operador_clp: float
    #: Costo del operador − recaudación por tarifa. Negativo ⇒ superávit.
    subsidio_metro_clp: float
    #: Excedente + recaudación − costo del operador, con el excedente **de la
    #: medida emparejada** (`medida_bienestar`): sumarle recaudación a un logsum
    #: bajo `todo_o_nada` mezclaría dos supuestos de comportamiento distintos.
    #:
    #: Es la función objetivo estándar en evaluación de políticas de precio, y
    #: sin ella el simulador estaba SESGADO contra ellas: subir el
    #: estacionamiento bajaba el excedente sin acreditar que la ciudad recauda,
    #: así que toda tarificación parecía empeorar el bienestar.
    bienestar_social_clp: float


def vot_clp_hora(cfg: SimulationConfig, estrato: StratumId) -> float:
    """Valor del tiempo conductual del estrato, en $/hora."""
    b = cfg.demand.estratos[estrato].betas
    return 0.0 if b.b_costo == 0 else (b.b_tiempo_viaje / b.b_costo) * 60


def _dinero_del_modo(modo: str, cfg: SimulationConfig, dist_km: float) -> float:
    g = cfg.demand.globales
    if modo == "Auto":
        return dist_km * g.costo_combustible_km + g.costo_parking
    if modo == "Metro":
        return g.costo_tarifa_metro
    return 0.0  # bici y caminata no cuestan dinero en el modelo


def _medidas(
    estrato: StratumId,
    celda: int,
    tiene_auto: bool,
    ciudad: CiudadLineal,
    cfg: SimulationConfig,
    tiempos: TiemposObservados,
) -> tuple[float, float] | None:
    """`(ln Σ_m e^{V_m}, max_m V_m)` sobre los modos FACTIBLES.

    Las dos medidas salen del mismo set de utilidades a propósito: calcularlas
    por separado significaría llamar dos veces a `calcular_utilidades`, que es lo
    caro de este módulo, y abriría la puerta a que una filtre por factibilidad y
    la otra no.

    `calcular_utilidades` ya marca infactible lo que quede fuera de
    `modos_habilitados`, así que basta filtrar por `feasible`: sin ese filtro,
    deshabilitar un modo no cambiaría el logsum y el excedente saldría inflado.
    """
    utils = calcular_utilidades(
        estrato=estrato,
        celda_origen=celda,
        tiene_auto=tiene_auto,
        ciudad=ciudad,
        config=cfg.demand,
        tiempos_observados=tiempos,
        modos_habilitados=cfg.modos_habilitados,
    )
    valores = [u.valor for m, u in utils.items() if u.feasible and np.isfinite(u.valor)]
    if not valores:
        return None
    mx = max(valores)
    logsum = mx + float(np.log(sum(np.exp(v - mx) for v in valores)))
    return logsum, mx


def calcular_agregados(
    cfg: SimulationConfig,
    trace: ConvergenceTrace,
    vot_social_clp_hora: float = VOT_SOCIAL_CLP_HORA,
) -> AgregadosDict | None:
    """Agregados del estado final de la corrida. `None` si no hay iteraciones."""
    if not trace.iteraciones:
        return None
    snap = trace.iteraciones[-1]
    if trace.demanda_estrato is None:
        # Sin la demanda desagregada no se puede aplicar un VoT por estrato: el
        # snapshot agregado sólo trae demanda por modo.
        return None

    ciudad = CiudadLineal(n_celdas=cfg.city.n_celdas, largo_total_km=cfg.city.largo_ciudad_km)
    estratos: list[StratumId] = [1, 2, 3]
    vot = {h: vot_clp_hora(cfg, h) for h in estratos}

    tiempo_total = viajeros = cg_percibido = cg_social = 0.0
    rec_parking = rec_tarifa = 0.0
    ls_suma = dict.fromkeys(estratos, 0.0)
    mx_suma = dict.fromkeys(estratos, 0.0)
    ls_n = dict.fromkeys(estratos, 0.0)

    for i in range(ciudad.n_celdas):
        dist_km = abs(ciudad.cbd_index - i) * ciudad.ancho_celda_km
        t_cam = (dist_km / cfg.demand.globales.v_caminata) * 60
        tiempos = TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        minutos_por_modo = {
            "Auto": tiempos.auto_total,
            "Metro": tiempos.tren_acceso + tiempos.tren_espera + tiempos.tren_viaje,
            "Bici": tiempos.bici_total,
            "Caminata": t_cam,
        }

        for h in estratos:
            for m_idx, modo in enumerate(MODOS):
                d = float(trace.demanda_estrato[h - 1, m_idx, i])
                if d <= 0:
                    continue
                minutos = minutos_por_modo[modo]
                dinero = _dinero_del_modo(modo, cfg, dist_km)
                tiempo_total += d * minutos
                viajeros += d
                cg_percibido += d * ((minutos / 60) * vot[h] + dinero)
                cg_social += d * ((minutos / 60) * vot_social_clp_hora + dinero)
                # Sólo las TRANSFERENCIAS cuentan como recaudación. La bencina se
                # excluye a propósito: es consumo real de recursos, no ingreso.
                if modo == "Auto":
                    rec_parking += d * cfg.demand.globales.costo_parking
                elif modo == "Metro":
                    rec_tarifa += d * cfg.demand.globales.costo_tarifa_metro

            n_estrato = float(trace.demanda_estrato[h - 1, :, i].sum())
            if n_estrato <= 0:
                continue
            # El conjunto de alternativas depende de tener auto, así que el
            # logsum del estrato es la mezcla de ambos casos ponderada por
            # `prob_auto`. Usar `True` para todos sobreestimaría el excedente de
            # quienes no tienen auto.
            p_auto = cfg.demand.estratos[h].prob_auto
            partes = [
                (_medidas(h, i, True, ciudad, cfg, tiempos), p_auto),
                (_medidas(h, i, False, ciudad, cfg, tiempos), 1 - p_auto),
            ]
            vivas = [(v, w) for v, w in partes if v is not None]
            peso = sum(w for _, w in vivas)
            if peso > 0:
                ls = sum(v[0] * w for v, w in vivas) / peso
                mx = sum(v[1] * w for v, w in vivas) / peso
                ls_suma[h] += ls * n_estrato
                mx_suma[h] += mx * n_estrato
                ls_n[h] += n_estrato

    # Tren-km del servicio. Se despeja de las emisiones del metro en vez de
    # recalcular `f_op · span · 2`: esa fórmula vive en `emissions.py` y
    # duplicarla acá sería otro espejo.
    factor_em = cfg.demand.globales.factor_emision_metro_tren_km
    tren_km = trace.emisiones_metro_kg / factor_em if factor_em > 0 else 0.0
    # El factor día/punta lleva el costo de la hora punta a base comparable con
    # el ingreso: sin él, el autofinanciamiento se lee sobre la hora más cargada
    # del día y sale optimista por construcción.
    costo_operador = (
        tren_km * cfg.supply.train.costo_operacion_tren_km * cfg.supply.train.factor_dia_punta
    )

    logsum: dict[str, float] = {}
    excedente: dict[str, float] = {}
    util_max: dict[str, float] = {}
    excedente_max: dict[str, float] = {}
    excedente_total = 0.0
    excedente_max_total = 0.0
    for h in estratos:
        n = ls_n[h]
        logsum[str(h)] = ls_suma[h] / n if n > 0 else 0.0
        util_max[str(h)] = mx_suma[h] / n if n > 0 else 0.0
        # λ_h = −β_costo (utilidad marginal del ingreso): pasa útiles a pesos.
        lam = -cfg.demand.estratos[h].betas.b_costo
        excedente[str(h)] = logsum[str(h)] / lam if lam > 0 else 0.0
        excedente_max[str(h)] = util_max[str(h)] / lam if lam > 0 else 0.0
        excedente_total += excedente[str(h)] * n
        excedente_max_total += excedente_max[str(h)] * n

    # El logit describe un agente con término aleatorio Gumbel y `todo_o_nada`
    # uno determinístico: cada supuesto tiene su propio E[max]. Elegir acá —y no
    # en la UI— mantiene la regla del lado de la matemática.
    medida: Literal["logsum", "utilidad_maxima"] = (
        "utilidad_maxima" if cfg.assignment == "todo_o_nada" else "logsum"
    )
    excedente_emparejado = excedente_max_total if medida == "utilidad_maxima" else excedente_total

    return {
        "tiempo_total_min": tiempo_total,
        "viajeros": viajeros,
        "tiempo_medio_min": tiempo_total / viajeros if viajeros > 0 else 0.0,
        "costo_generalizado_percibido_clp": cg_percibido,
        "costo_generalizado_social_clp": cg_social,
        "vot_por_estrato_clp_hora": {str(h): vot[h] for h in estratos},
        "logsum_por_estrato": logsum,
        "excedente_por_estrato_clp": excedente,
        "util_maxima_por_estrato": util_max,
        "excedente_max_por_estrato_clp": excedente_max,
        "viajeros_por_estrato": {str(h): ls_n[h] for h in estratos},
        "excedente_total_clp": excedente_total,
        "excedente_max_total_clp": excedente_max_total,
        "medida_bienestar": medida,
        "recaudacion_parking_clp": rec_parking,
        "recaudacion_tarifa_clp": rec_tarifa,
        "tren_km_hora": tren_km,
        "costo_operador_clp": costo_operador,
        "subsidio_metro_clp": costo_operador - rec_tarifa,
        "bienestar_social_clp": excedente_emparejado + rec_parking + rec_tarifa - costo_operador,
    }
