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

3. **Excedente del consumidor**: el logsum `ln Σ_m e^{V_m}`, dividido por
   λ = −β_costo para quedar en pesos. Es `E[max_m (V_m + ε_m)]` con ε Gumbel
   iid —o sea, el bienestar del agente que el logit describe—, y reemplaza a la
   "utilidad media", que no significa nada: promediar utilidades entre personas
   no es bienestar.

   Hasta nov-2026 había una segunda medida, la utilidad máxima `max_m V_m`,
   emparejada con la carga determinística ('todo_o_nada'). Se retiró junto con
   ese método: con un solo modelo de comportamiento hay una sola medida.

   **El nivel tiene cero arbitrario** (incluye las constantes específicas), así
   que sólo la DIFERENCIA contra otro escenario es interpretable. Este módulo
   entrega el nivel; quién resta contra qué es decisión de cada consumidor —el
   Sandbox contra el escenario que el usuario fija como referencia, la página
   acoplada contra la red vacía (`coupled_metrics._tiempos_red_vacia`). Las dos
   lecturas son válidas y responden preguntas distintas; lo que no puede haber
   es dos implementaciones de la matemática.

   Desde el 2026-08-17 la página acoplada usa la MISMA implementación
   (`logsum_de_utilidad`), así que las dos páginas no pueden contestar distinto
   la misma pregunta.

Dos convenciones que conviene tener escritas
--------------------------------------------

**La constante de Euler se omite.** El `E[max]` exacto del logit es
`ln Σ e^{V_m} + γ`, con γ ≈ 0,5772; acá se calcula sólo el primer término, que es
la convención habitual. No afecta ningún Δ —γ es aditiva y común, y se cancela en
toda diferencia, que es lo único interpretable.

**Los agentes sin ninguna alternativa factible quedan fuera.** Si para un par
(estrato, celda) no hay modo factible ni con auto ni sin él, `logsum_de_utilidad`
devuelve `None` en las dos ramas y ese grupo no entra al promedio NI al
denominador de población. La consecuencia a vigilar: una política que dejara
gente sin alternativas no la contaría como bienestar muy bajo, la haría
desaparecer del cálculo. Medido el 2026-08-17 sobre la corrida por defecto (20 km)
y sobre una ciudad dispersa de 40 km: cero exclusiones en ambas, los 29.002 y
28.996 viajeros entran completos, porque el metro sigue siendo factible en
prácticamente toda la ciudad. Es un caso hoy vacío, no un caso imposible —
deshabilitar modos o estirar mucho las distancias podría activarlo. Por eso
el conteo viaja junto al agregado, en `varados` (D14): quien lee el excedente
ve cuántos quedaron fuera de él.

El desarrollo completo, con la derivación y la correspondencia paso a paso con
este archivo, está en `docs/libro/informe-bienestar.html`.
"""

from __future__ import annotations

from typing import Literal, TypedDict

import numpy as np

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig, StratumId
from titirilquen_core.constantes import MODOS, VIAJES_POR_TOUR
from titirilquen_core.demand.utility import (
    TiemposObservados,
    calcular_utilidades,
    costo_monetario_auto,
    litros_viaje_auto,
)
from titirilquen_core.emissions import tren_km_hora
from titirilquen_core.equilibrium.msa import ConvergenceTrace
from titirilquen_core.operacion_vehicular import otros_costos_operacion_auto_clp_km

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
    #: Agentes sin ningún modo factible (D14). No están en `viajeros` ni en el
    #: excedente: sin una utilidad de reserva no hay con qué valorarlos. Se
    #: cuentan sobre los agentes porque no tienen fila en `demanda_estrato`;
    #: el conteo es exacto, no un sorteo, porque varar es del grupo entero.
    varados: int
    #: Viajes por modo, en los 4 modos FÍSICOS. Σ = `viajeros`, así que el share
    #: es `viajes_por_modo[m] / viajeros`.
    #:
    #: Se calcula acá y no en la UI porque el reparto modal es lo primero que se
    #: compara entre escenarios y tiene que salir de la MISMA fuente y el MISMO
    #: denominador que el resto de la tabla: la demanda esperada por estrato, no
    #: el conteo de agentes del snapshot. Los dos existen, difieren —el conteo
    #: incluye teletrabajo— y tenerlos juntos en una tabla de comparación era
    #: pedir que alguien reste peras con manzanas.
    viajes_por_modo: dict[str, float]
    #: Lo mismo, desagregado: `[estrato][modo]`. Σ_m sobre un estrato da sus
    #: viajes físicos, y Σ_h Σ_m da `viajeros`. La tabla por estrato lo lee de
    #: acá y no de contar `modo_elegido` sobre los agentes: ese conteo se
    #: normaliza sobre TODOS los agentes del estrato —teletrabajo incluido—, así
    #: que los dos repartos de la pantalla tenían denominadores distintos y sólo
    #: coincidían si uno hacía la conversión a mano.
    viajes_por_modo_estrato: dict[EstratoKey, dict[str, float]]
    tiempo_medio_min: float
    #: Tiempo medio (min) por modo físico y por estrato, ponderado por la MISMA
    #: demanda esperada. Antes la UI los promediaba sobre el `modo_elegido`
    #: sorteado de cada agente, que con carga esperada mete ruido de muestreo
    #: en un indicador que no lo tiene (auditoría C, ítem 9). 0 si nadie viaja.
    tiempo_medio_por_modo_min: dict[str, float]
    tiempo_medio_por_estrato_min: dict[EstratoKey, float]
    #: Tiempo valorado al VoT conductual de cada estrato, más dinero.
    costo_generalizado_percibido_clp: float
    #: Ídem con un VoT único (evaluación social).
    costo_generalizado_social_clp: float
    #: **El otro enfoque para medir el beneficio.** El costo generalizado y el
    #: excedente miran el viaje desde el usuario, e incluyen lo que paga aunque
    #: ese pago no consuma nada: el peaje, el parking y la tarifa son
    #: TRANSFERENCIAS, le salen del bolsillo a uno y le entran a otro. El costo
    #: de recursos cuenta sólo lo que la sociedad gasta de verdad —tiempo,
    #: operación de autos y metro, y el daño del CO₂— y por eso su Δ entre
    #: escenarios es el ahorro de recursos. Es el enfoque del MESPIVU (13.1.1):
    #: «ahorro en el consumo total de recursos entre las situaciones base y
    #: con proyecto», con tiempo, combustible y otros costos de operación.
    #:
    #: El tiempo va al VST, no al VoT conductual: en el enfoque de recursos no
    #: tiene sentido que un minuto valga más según quién lo gaste.
    #:
    #: No es intercambiable con el excedente: son dos caminos a la misma
    #: pregunta, y sumarlos cuenta dos veces. Tampoco coinciden número a número
    #: —el excedente valora con λ_h y lleva el término de Gumbel— así que la
    #: equivalencia es conceptual, no una identidad contable.
    recursos_tiempo_clp: float
    #: Pasajero-km de la hora punta, por modo y en total: viajes por la
    #: distancia de su celda al CBD. Es la medida física de cuánto transporte
    #: produce la ciudad —los viajes cuentan igual uno de 500 m que uno de
    #: 10 km—, y el denominador de toda comparación por unidad de servicio.
    pasajero_km_por_modo: dict[str, float]
    pasajero_km: float
    #: Pasajero-km del metro sobre los que ofrece: `tren-km × capacidad`. Los
    #: tren-km cuentan la ida y la vuelta del servicio, así que con todos los
    #: viajes hacia el CBD no puede pasar de la mitad salvo sobrecarga.
    ocupacion_metro: float
    #: Costo de recursos y CO₂ por pasajero-km: comparan escenarios que mueven
    #: distinta cantidad de transporte ($/pax-km y gramos/pax-km).
    costo_recursos_por_pkm_clp: float
    co2_g_por_pkm: float
    #: Auto-km de la hora punta: viajes en auto por su distancia al CBD.
    auto_km_hora: float
    #: Litros de bencina de la hora punta (`utility.litros_viaje_auto`): la
    #: ÚNICA cuantificación del consumo. De ellos salen las tres cifras de
    #: abajo, y por eso cierran: pagado = recurso + impuesto.
    litros_combustible_hora: float
    #: Los litros a PRECIO SOCIAL (sin impuestos): lo que le cuesta a la
    #: sociedad. La congestión gasta más bencina por kilómetro.
    recursos_combustible_clp: float
    #: Los mismos litros al precio de MERCADO: lo que pagan los conductores, y
    #: lo que entra a su costo generalizado y a su elección de modo.
    pago_combustible_clp: float
    #: Lubricantes, neumáticos, repuestos y mantención de los autos (MESPIVU,
    #: ec. 13.1.1-7), sin rugosidad: un piso.
    recursos_otros_operacion_clp: float
    #: Las emisiones al precio social del carbono (71.801 $/t CO₂).
    costo_co2_clp: float
    #: El stock de infraestructura del escenario a sus costos unitarios
    #: (`config.inversion`), sin anualizar: pistas, estaciones, ciclovía y el
    #: sobrecosto de una flota más limpia.
    inversion_capital_clp: float
    #: Ese capital anualizado (tasa social de descuento, vida útil) y llevado a
    #: la hora punta. Cero mientras los costos unitarios estén en cero.
    costo_inversion_clp: float
    #: `recursos_tiempo + recursos_combustible + recursos_otros_operacion +
    #: costo_operador + costo_co2 + costo_inversion`.
    costo_recursos_clp: float
    #: Valor del tiempo conductual por estrato ($/hora) = β_t/β_c · 60.
    vot_por_estrato_clp_hora: dict[EstratoKey, float]
    #: Logsum medio por estrato (útiles) y su equivalente en pesos (÷ λ_h).
    logsum_por_estrato: dict[EstratoKey, float]
    excedente_por_estrato_clp: dict[EstratoKey, float]
    #: El mismo excedente, pero valorado con el VoT social único en vez del
    #: conductual de cada estrato. Es al excedente lo que
    #: `costo_generalizado_social_clp` es al percibido.
    #:
    #: No es cosmético: cambia el SIGNO de los resultados agregados. El VoT
    #: conductual le da al minuto del estrato alto varias veces el valor del
    #: minuto del bajo, así que agregar en esa unidad pondera a favor de quien
    #: más gana. Con VoT único el minuto de todos vale lo mismo, que es el
    #: supuesto de la evaluación social chilena.
    excedente_social_por_estrato_clp: dict[EstratoKey, float]
    excedente_social_total_clp: float
    viajeros_por_estrato: dict[EstratoKey, float]
    #: Σ_h viajeros_h · excedente_h. Cero arbitrario: sólo el Δ es interpretable.
    excedente_total_clp: float
    #: Recaudación de estacionamiento. Es TRANSFERENCIA, no consumo de recursos:
    #: alguien la recibe. La bencina NO entra — ésa sí se consume.
    recaudacion_parking_clp: float
    #: Recaudación del peaje por km (D7). Transferencia, como el parking.
    recaudacion_peaje_clp: float
    recaudacion_tarifa_clp: float
    #: La parte de la bencina que es impuesto: lo pagado menos el recurso, o
    #: sea los litros por (precio de mercado − precio social). No es un
    #: supuesto aparte: resulta de los dos precios. Es transferencia, como el
    #: peaje: el conductor la pierde y el fisco la gana. Negativa si el precio
    #: de mercado queda bajo el social (un subsidio a la bencina).
    #: Sin ella, el bienestar social trataba toda la bencina como recurso
    #: perdido y toda política que saca autos se veía mejor de lo que es.
    recaudacion_combustible_clp: float
    #: Tren-km por hora del servicio (f_op · largo de línea · 2).
    tren_km_hora: float
    #: Costo de operación del metro EN LA HORA PUNTA, la misma base que el
    #: excedente y las recaudaciones (D12). A diferencia de la tarifa, es consumo.
    costo_operador_clp: float
    #: Costo del operador × `factor_dia_punta` − recaudación por tarifa: el costo
    #: por viaje del día completo contra la tarifa. Negativo ⇒ superávit.
    subsidio_metro_clp: float
    #: Excedente + recaudación − costo del operador − costo de inversión.
    #:
    #: Es la función objetivo estándar en evaluación de políticas de precio, y
    #: sin ella el simulador estaba SESGADO contra ellas: subir el
    #: estacionamiento bajaba el excedente sin acreditar que la ciudad recauda,
    #: así que toda tarificación parecía empeorar el bienestar.
    bienestar_social_clp: float


def minutos_ponderados(
    modo: str,
    tiempos: TiemposObservados,
    t_caminata_min: float,
    *,
    w_espera: float,
    w_acceso: float,
    w_caminata: float,
) -> float:
    """Minutos-equivalentes en vehículo de un viaje: cada componente de tiempo
    pesa lo que pesa en la utilidad (o en la norma), no un minuto plano (D-37).

    Auto y bici: su tiempo tal cual. Metro: viaje + w·espera + w·acceso.
    Caminata como modo: w_caminata · tiempo. Las penalizaciones escalonadas de
    bici y caminata quedan fuera: son desutilidad, no tiempo."""
    if modo == "Auto":
        return float(tiempos.auto_total)
    if modo == "Bici":
        return float(tiempos.bici_total)
    if modo == "Metro":
        return float(
            tiempos.tren_viaje + w_espera * tiempos.tren_espera + w_acceso * tiempos.tren_acceso
        )
    return w_caminata * float(t_caminata_min)


def vot_clp_hora(cfg: SimulationConfig, estrato: StratumId) -> float:
    """Valor del tiempo conductual del estrato, en $/hora."""
    b = cfg.demand.estratos[estrato].betas
    return 0.0 if b.b_costo == 0 else (b.b_tiempo_viaje / b.b_costo) * 60


def _dinero_del_modo(modo: str, cfg: SimulationConfig, dist_km: float, t_auto_min: float) -> float:
    g = cfg.demand.globales
    if modo == "Auto":
        return costo_monetario_auto(dist_km, t_auto_min, g)
    if modo == "Metro":
        return g.costo_tarifa_metro
    return 0.0  # bici y caminata no cuestan dinero en el modelo


def logsum_de_utilidad(
    estrato: StratumId,
    celda: int,
    tiene_auto: bool,
    ciudad: CiudadLineal,
    cfg: SimulationConfig,
    tiempos: TiemposObservados,
) -> float | None:
    """`ln Σ_m e^{V_m}` sobre los modos FACTIBLES. `None` si no hay ninguno.

    Es la ÚNICA implementación del logsum en el núcleo: la usan tanto los
    agregados del Sandbox (`calcular_agregados`) como las métricas de la página
    acoplada (`coupled_metrics`). Hasta agosto de 2026 estaba escrito dos veces,
    y las dos copias ya habían empezado a separarse — una filtraba por
    `isfinite` y la otra por `> UTIL_IMPOSIBLE`. Daban lo mismo, que es
    exactamente como empieza un espejo roto.

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
    return mx + float(np.log(sum(np.exp(v - mx) for v in valores)))


def costo_inversion(cfg: SimulationConfig, trace: ConvergenceTrace) -> tuple[float, float]:
    """`(capital, costo por hora punta)` de la infraestructura del escenario.

    El capital es el stock a sus costos unitarios. Se anualiza con el factor de
    recuperación del capital, `r / (1 − (1 + r)^−n)` —con r = 0, `1/n`—, y se
    divide por las horas punta equivalentes del año para quedar en la base de
    los demás agregados."""
    inv = cfg.inversion
    largo = cfg.city.largo_ciudad_km
    estaciones = (
        len(trace.estaciones_km)
        if trace.estaciones_km is not None
        else cfg.supply.train.num_estaciones
    )
    autos = sum(1 for a in trace.agentes if a.tiene_auto)
    capital = (
        cfg.supply.car.num_pistas * largo * inv.costo_pista_km_clp
        + estaciones * inv.costo_estacion_clp
        + cfg.supply.bike.capacidad_pista / 1000 * largo * inv.costo_ciclovia_km_clp
        + autos * (1 - cfg.demand.globales.factor_flota_auto) * inv.sobrecosto_flota_limpia_clp
    )
    r, n = cfg.precios_sociales.tasa_social_descuento, inv.vida_util_anios
    recuperacion = r / (1 - (1 + r) ** -n) if r > 0 else 1 / n
    return capital, capital * recuperacion / inv.horas_punta_anio


def calcular_agregados(
    cfg: SimulationConfig,
    trace: ConvergenceTrace,
) -> AgregadosDict | None:
    """Agregados del estado final de la corrida. `None` si no hay iteraciones.

    Los precios sociales salen de `cfg.precios_sociales`: se actualizan cada
    año y por eso son configuración, no constantes."""
    ps = cfg.precios_sociales
    vot_social_clp_hora = ps.vst_viaje_clp_h
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
    # Enfoque de AHORRO DE RECURSOS: sólo lo que la sociedad consume de
    # verdad. El tiempo al VST (no al VoT conductual, que pondera por
    # ingreso); la operación de los autos va después del loop, por tramo.
    # Peaje, parking y tarifa quedan fuera: son transferencias, cambian de
    # bolsillo sin consumir nada.
    rec_tiempo = 0.0
    viajes_modo = dict.fromkeys(MODOS, 0.0)
    viajes_modo_estrato: dict[str, dict[str, float]] = {
        str(h): dict.fromkeys(MODOS, 0.0) for h in (1, 2, 3)
    }
    tiempo_modo = dict.fromkeys(MODOS, 0.0)
    pkm_modo = dict.fromkeys(MODOS, 0.0)
    tiempo_estrato = dict.fromkeys(estratos, 0.0)
    viajes_estrato = dict.fromkeys(estratos, 0.0)
    rec_parking = rec_peaje = rec_tarifa = 0.0
    auto_km = litros = 0.0
    # Tenencia de auto REALIZADA por (estrato, celda) entre quienes viajan: la
    # población la fija por conteo redondeado, `round(n·prob_auto)` en cada
    # celda, y con ella se calculó la demanda. Ponderar el logsum por la
    # `prob_auto` nominal lo apartaba de esa demanda (y del acoplado, que suma
    # por agente) en 0,3-2,8 % del nivel (auditoría C, ítem 11).
    n_viaja = np.zeros((3, ciudad.n_celdas))
    n_con_auto = np.zeros((3, ciudad.n_celdas))
    for a in trace.agentes:
        if not a.teletrabaja:
            n_viaja[a.estrato - 1, a.celda_origen] += 1
            n_con_auto[a.estrato - 1, a.celda_origen] += a.tiene_auto
    ls_suma = dict.fromkeys(estratos, 0.0)
    ls_n = dict.fromkeys(estratos, 0.0)

    for i in range(ciudad.n_celdas):
        dist_km = abs(ciudad.cbd_index - i) * ciudad.ancho_celda_km
        t_cam = (dist_km / cfg.demand.globales.v_caminata) * 60
        tiempos = TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            bici_libre=float(snap.t_bici_libre[i]),
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
                dinero = _dinero_del_modo(modo, cfg, dist_km, tiempos.auto_total)
                tiempo_total += d * minutos
                viajeros += d
                viajes_modo[modo] += d
                viajes_modo_estrato[str(h)][modo] += d
                tiempo_modo[modo] += d * minutos
                pkm_modo[modo] += d * dist_km
                tiempo_estrato[h] += d * minutos
                viajes_estrato[h] += d
                # Costo generalizado por COMPONENTES (D-37): el percibido pesa
                # espera, acceso y caminata como la utilidad del estrato; el
                # social, como la tabla 2.1 del SNI.
                b = cfg.demand.estratos[h].betas
                bt = abs(b.b_tiempo_viaje) or 1.0
                min_perc = minutos_ponderados(
                    modo,
                    tiempos,
                    t_cam,
                    w_espera=abs(b.b_tiempo_espera) / bt,
                    w_acceso=abs(b.b_tiempo_acceso) / bt,
                    w_caminata=abs(b.b_tiempo_caminata) / bt,
                )
                min_soc = minutos_ponderados(
                    modo,
                    tiempos,
                    t_cam,
                    w_espera=ps.ponderador_espera,
                    w_acceso=ps.ponderador_caminata,
                    w_caminata=1.0,
                )
                cg_percibido += d * ((min_perc / 60) * vot[h] + dinero)
                cg_social += d * ((min_soc / 60) * vot_social_clp_hora + dinero)
                rec_tiempo += d * (min_soc / 60) * vot_social_clp_hora
                # Sólo las TRANSFERENCIAS cuentan como recaudación. De la bencina
                # entra la parte que es impuesto (se separa al final); el resto
                # es consumo real de recursos, no ingreso.
                if modo == "Auto":
                    auto_km += d * dist_km
                    litros += d * litros_viaje_auto(
                        dist_km, tiempos.auto_total, cfg.demand.globales
                    )
                    rec_parking += d * cfg.demand.globales.costo_parking / VIAJES_POR_TOUR
                    rec_peaje += d * dist_km * cfg.demand.globales.peaje_km
                elif modo == "Metro":
                    rec_tarifa += d * cfg.demand.globales.costo_tarifa_metro

            n_estrato = float(trace.demanda_estrato[h - 1, :, i].sum())
            if n_estrato <= 0:
                continue
            # El conjunto de alternativas depende de tener auto, así que el
            # logsum del estrato es la mezcla de ambos casos ponderada por la
            # tenencia de la celda. Usar `True` para todos sobreestimaría el
            # excedente de quienes no tienen auto. Sin agentes (un trace armado
            # a mano) queda la `prob_auto` nominal.
            nv = n_viaja[h - 1, i]
            p_auto = n_con_auto[h - 1, i] / nv if nv > 0 else cfg.demand.estratos[h].prob_auto
            partes = [
                (logsum_de_utilidad(h, i, True, ciudad, cfg, tiempos), p_auto),
                (logsum_de_utilidad(h, i, False, ciudad, cfg, tiempos), 1 - p_auto),
            ]
            vivas = [(v, w) for v, w in partes if v is not None]
            peso = sum(w for _, w in vivas)
            if peso > 0:
                ls = sum(v * w for v, w in vivas) / peso
                ls_suma[h] += ls * n_estrato
                ls_n[h] += n_estrato

    # Tren-km del servicio, de la misma función que usan las emisiones (D-36).
    # Antes se despejaba `kg / factor_emisión`, y con factor 0 el costo del
    # operador desaparecía aunque el servicio siguiera circulando.
    tren_km = tren_km_hora(float(snap.frecuencia_metro), trace.estaciones_km)
    # En la base del resto del bienestar, la hora punta (D12). El factor día/punta
    # entra sólo al subsidio: sin él, el autofinanciamiento se leería sobre la
    # hora más cargada del día y saldría optimista por construcción; dentro del
    # bienestar le cargaría a la punta la operación del valle sin sus beneficios.
    costo_operador = tren_km * cfg.supply.train.costo_operacion_tren_km

    # Operación de los autos. Los LITROS son los mismos con que cada conductor
    # eligió modo (`litros_viaje_auto`): al precio social dan el recurso, al de
    # mercado lo que se pagó, y la diferencia es el impuesto. Cierra por
    # construcción: pagado = recurso + impuesto.
    rec_combustible = litros * ps.combustible_auto_clp_l
    pago_combustible = litros * cfg.demand.globales.precio_combustible_clp_l
    rec_combustible_imp = pago_combustible - rec_combustible
    rec_otros = auto_km * otros_costos_operacion_auto_clp_km(ps)
    costo_co2 = trace.emisiones_total_kg / 1000 * ps.carbono_clp_t
    capital, c_inversion = costo_inversion(cfg, trace)
    costo_recursos = (
        rec_tiempo + rec_combustible + rec_otros + costo_operador + costo_co2 + c_inversion
    )
    pkm = sum(pkm_modo.values())
    oferta_metro = tren_km * cfg.supply.train.capacidad_tren

    logsum: dict[str, float] = {}
    excedente: dict[str, float] = {}
    excedente_social: dict[str, float] = {}
    excedente_total = 0.0
    excedente_social_total = 0.0
    for h in estratos:
        n = ls_n[h]
        logsum[str(h)] = ls_suma[h] / n if n > 0 else 0.0
        # λ_h = −β_costo (utilidad marginal del ingreso): pasa útiles a pesos.
        lam = -cfg.demand.estratos[h].betas.b_costo
        excedente[str(h)] = logsum[str(h)] / lam if lam > 0 else 0.0
        excedente_total += excedente[str(h)] * n

        # λ SOCIAL: la misma utilidad, valorada con el VoT de NORMA en vez del
        # conductual del estrato. Se despeja del propio VoT:
        #
        #     VoT_h = (β_t/β_c)·60   ⇒   λ_social,h = |β_t,h|·60 / VoT_social
        #
        # Sigue dependiendo del estrato porque β_t fija la escala de SU utilidad
        # —sin eso los útiles de estratos distintos no serían sumables—, pero el
        # PRECIO del minuto pasa a ser único.
        lam_social = (
            abs(cfg.demand.estratos[h].betas.b_tiempo_viaje) * 60 / vot_social_clp_hora
            if vot_social_clp_hora > 0
            else 0.0
        )
        excedente_social[str(h)] = logsum[str(h)] / lam_social if lam_social > 0 else 0.0
        excedente_social_total += excedente_social[str(h)] * n

    return {
        "tiempo_total_min": tiempo_total,
        "viajeros": viajeros,
        "varados": sum(1 for a in trace.agentes if a.modo_elegido is None),
        "viajes_por_modo": viajes_modo,
        "viajes_por_modo_estrato": viajes_modo_estrato,
        "tiempo_medio_min": tiempo_total / viajeros if viajeros > 0 else 0.0,
        "tiempo_medio_por_modo_min": {
            m: tiempo_modo[m] / viajes_modo[m] if viajes_modo[m] > 0 else 0.0 for m in MODOS
        },
        "tiempo_medio_por_estrato_min": {
            str(h): tiempo_estrato[h] / viajes_estrato[h] if viajes_estrato[h] > 0 else 0.0
            for h in estratos
        },
        "costo_generalizado_percibido_clp": cg_percibido,
        "costo_generalizado_social_clp": cg_social,
        "recursos_tiempo_clp": rec_tiempo,
        "pasajero_km_por_modo": pkm_modo,
        "pasajero_km": pkm,
        "ocupacion_metro": pkm_modo["Metro"] / oferta_metro if oferta_metro > 0 else 0.0,
        "costo_recursos_por_pkm_clp": costo_recursos / pkm if pkm > 0 else 0.0,
        "co2_g_por_pkm": trace.emisiones_total_kg * 1000 / pkm if pkm > 0 else 0.0,
        "auto_km_hora": auto_km,
        "litros_combustible_hora": litros,
        "recursos_combustible_clp": rec_combustible,
        "pago_combustible_clp": pago_combustible,
        "recursos_otros_operacion_clp": rec_otros,
        "costo_co2_clp": costo_co2,
        "inversion_capital_clp": capital,
        "costo_inversion_clp": c_inversion,
        "costo_recursos_clp": costo_recursos,
        "vot_por_estrato_clp_hora": {str(h): vot[h] for h in estratos},
        "logsum_por_estrato": logsum,
        "excedente_por_estrato_clp": excedente,
        "excedente_social_por_estrato_clp": excedente_social,
        "excedente_social_total_clp": excedente_social_total,
        "viajeros_por_estrato": {str(h): ls_n[h] for h in estratos},
        "excedente_total_clp": excedente_total,
        "recaudacion_parking_clp": rec_parking,
        "recaudacion_peaje_clp": rec_peaje,
        "recaudacion_tarifa_clp": rec_tarifa,
        "recaudacion_combustible_clp": rec_combustible_imp,
        "tren_km_hora": tren_km,
        "costo_operador_clp": costo_operador,
        "subsidio_metro_clp": costo_operador * cfg.supply.train.factor_dia_punta - rec_tarifa,
        "bienestar_social_clp": (
            excedente_total
            + rec_parking
            + rec_peaje
            + rec_tarifa
            + rec_combustible_imp
            - costo_operador
            - c_inversion
        ),
    }
