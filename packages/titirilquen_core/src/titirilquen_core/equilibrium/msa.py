"""Método de Promedios Sucesivos (MSA) para el equilibrio oferta-demanda.

Portado y extendido desde `titirilquen-repo/app.py:470-524`. Cambios:

- Criterio de convergencia real: residuo `‖T_n − T_{n−1}‖_∞ < tol`. Si
  `tol=0` (default), se respeta `max_iter` como antes (ver D-10).
- Retorna `ConvergenceTrace` con snapshot por iteración para visualización
  en vivo (antes este dato se perdía tras el loop).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, SimulationConfig, StratumId
from titirilquen_core.demand.choice import probabilidades_logit, probabilidades_wardrop
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.emissions import calcular_emisiones
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.supply import generar_oferta
from titirilquen_core.population import (
    Agente,
    generar_poblacion,
    generar_poblacion_desde_land_use_det,
)
from titirilquen_core.supply.bike import demora_bici_tramo
from titirilquen_core.supply.car import demora_auto_tramo
from titirilquen_core.supply.train import oferta_tren

ModalSplit = dict[str, float]


@dataclass
class IterationSnapshot:
    """Estado de la red al final de una iteración del MSA."""

    iter: int
    f_msa: float
    modal_split: ModalSplit
    demanda_auto: NDArray[np.float64]
    demanda_metro: NDArray[np.float64]
    demanda_bici: NDArray[np.float64]
    demanda_caminata: NDArray[np.float64]
    t_auto: NDArray[np.float64]
    t_bici: NDArray[np.float64]
    t_tren_acceso: NDArray[np.float64]
    t_tren_espera: NDArray[np.float64]
    t_tren_viaje: NDArray[np.float64]
    frecuencia_metro: float
    #: Frecuencia sin recortar (`carga/K`). Comparada con `frecuencia_metro`
    #: revela si `frec_min`/`frec_max` estan mordiendo — ver AT-08/AT-09.
    frecuencia_teorica_metro: float
    residuo: float


@dataclass
class ConvergenceTrace:
    """Resultado completo del loop MSA."""

    iteraciones: list[IterationSnapshot] = field(default_factory=list)
    converged: bool = False
    capacidad_auto: float = 0.0
    v_libre_auto: float = 0.0
    alpha_auto_bpr: float = 0.0
    beta_auto_bpr: float = 0.0
    carga_metro: NDArray[np.float64] | None = None
    estaciones_km: NDArray[np.float64] | None = None
    agentes: list[Agente] = field(default_factory=list)
    emisiones_total_kg: float = 0.0
    emisiones_auto_kg: float = 0.0
    emisiones_metro_kg: float = 0.0
    emisiones_perfil_kg: NDArray[np.float64] | None = None
    # Flujo ACUMULADO por corredor hacia el CBD del estado final (cumsum de la
    # demanda originada, por dirección) — veh/h y bici/h por celda. Es el numerador
    # correcto del v/c: la demanda originada por celda NO lo es (subestima ~60×).
    flujos_auto_veh_h: NDArray[np.float64] | None = None
    flujos_bici_veh_h: NDArray[np.float64] | None = None
    # Demanda ESPERADA por (estrato, modo, celda) del estado final — forma
    # [3, len(_MODOS), n_celdas], estratos 0..2 = 1..3, modos en orden _MODOS.
    # Es la demanda por celda (misma que las Fig. 2/3/4) desagregada por estrato,
    # para el reparto modal espacial por estrato.
    demanda_estrato: NDArray[np.float64] | None = None


def _tiempos_de_snapshot(snap: IterationSnapshot, n_celdas: int) -> list[TiemposObservados]:
    return [
        TiemposObservados(
            auto_total=float(snap.t_auto[i]),
            bici_total=float(snap.t_bici[i]),
            tren_acceso=float(snap.t_tren_acceso[i]),
            tren_espera=float(snap.t_tren_espera[i]),
            tren_viaje=float(snap.t_tren_viaje[i]),
        )
        for i in range(n_celdas)
    ]


_MODOS: tuple[str, ...] = ("Auto", "Metro", "Bici", "Caminata")


@dataclass
class _GrupoDemanda:
    """Agentes no‑teletrabajadores que comparten (estrato, celda, tiene_auto) y
    por lo tanto tienen idéntica utilidad/probabilidades. Agrupar permite calcular
    la elección **una vez por grupo** en lugar de una vez por agente: el costo del
    loop pasa de O(agentes) a O(grupos ≈ 6·n_celdas), independiente de la densidad
    (ver nota de rendimiento abajo)."""

    estrato: StratumId
    celda: int
    tiene_auto: bool
    agentes: list[Agente]


def _agrupar_agentes(agentes: list[Agente]) -> tuple[list[_GrupoDemanda], int]:
    """Agrupa los agentes elegibles por (estrato, celda, tiene_auto) y fija el
    modo de los teletrabajadores. Se hace una sola vez por corrida. Devuelve
    (grupos, n_teletrabaja)."""
    grupos: dict[tuple[StratumId, int, bool], _GrupoDemanda] = {}
    n_tele = 0
    for a in agentes:
        if a.teletrabaja:
            a.modo_elegido = "Teletrabajo"
            a.utilidad_elegida = 0.0
            n_tele += 1
            continue
        key = (a.estrato, a.celda_origen, a.tiene_auto)
        g = grupos.get(key)
        if g is None:
            g = _GrupoDemanda(a.estrato, a.celda_origen, a.tiene_auto, [])
            grupos[key] = g
        g.agentes.append(a)
    return list(grupos.values()), n_tele


def _probs_grupo(
    g: _GrupoDemanda,
    ciudad: CiudadLineal,
    demand: DemandConfig,
    tiempos_por_celda: list[TiemposObservados] | None,
    modos_habilitados: tuple[str, ...] | None,
    wardrop: bool = False,
):
    tiempos = tiempos_por_celda[g.celda] if tiempos_por_celda is not None else None
    utils = calcular_utilidades(
        estrato=g.estrato,
        celda_origen=g.celda,
        tiene_auto=g.tiene_auto,
        ciudad=ciudad,
        config=demand,
        tiempos_observados=tiempos,
        modos_habilitados=modos_habilitados,
    )
    reparto = probabilidades_wardrop if wardrop else probabilidades_logit
    return utils, reparto(utils)


def _correr_iteracion(
    grupos: list[_GrupoDemanda],
    n_tele: int,
    ciudad: CiudadLineal,
    demand: DemandConfig,
    tiempos_por_celda: list[TiemposObservados] | None,
    rng: np.random.Generator,
    expected: bool = False,
    modos_habilitados: tuple[str, ...] | None = None,
    wardrop: bool = False,
) -> tuple[
    ModalSplit,
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
    NDArray[np.float64],
]:
    """Asigna demanda agregando por grupo (no por agente). Si `expected=False`
    (Monte Carlo) sortea el conteo por modo de cada grupo con una multinomial;
    si `expected=True` usa los **flujos esperados** = nₐ·prob (asignación
    fraccional, determinista). No escribe registros por agente: eso se hace una
    sola vez al final con `_asignar_modos_agentes`."""
    conteo: ModalSplit = {
        "Auto": 0.0,
        "Metro": 0.0,
        "Bici": 0.0,
        "Caminata": 0.0,
        "Teletrabajo": float(n_tele),
    }
    dem_auto = np.zeros(ciudad.n_celdas)
    dem_metro = np.zeros(ciudad.n_celdas)
    dem_bici = np.zeros(ciudad.n_celdas)
    dem_caminata = np.zeros(ciudad.n_celdas)
    dem = {"Auto": dem_auto, "Metro": dem_metro, "Bici": dem_bici, "Caminata": dem_caminata}

    for g in grupos:
        _, probs = _probs_grupo(g, ciudad, demand, tiempos_por_celda, modos_habilitados, wardrop)
        n = len(g.agentes)
        i = g.celda
        if expected:
            for m in _MODOS:
                pr = probs.get(m, 0.0)
                if pr:
                    conteo[m] += n * pr
                    dem[m][i] += n * pr
        else:
            pvec = np.array([probs.get(m, 0.0) for m in _MODOS])
            total = float(pvec.sum())
            if total <= 0.0:
                continue  # todos los modos infeasibles → agentes varados (sin viaje)
            pvec = pvec / total
            # Robustez fp: multinomial exige sum(pvals) ≤ 1; el último absorbe el resto.
            pvec[-1] = max(0.0, 1.0 - float(pvec[:-1].sum()))
            counts = rng.multinomial(n, pvec)
            for k, m in enumerate(_MODOS):
                ck = int(counts[k])
                if ck:
                    conteo[m] += ck
                    dem[m][i] += ck

    return conteo, dem_auto, dem_metro, dem_bici, dem_caminata


def _asignar_modos_agentes(
    grupos: list[_GrupoDemanda],
    ciudad: CiudadLineal,
    demand: DemandConfig,
    tiempos_por_celda: list[TiemposObservados] | None,
    rng: np.random.Generator,
    modos_habilitados: tuple[str, ...] | None = None,
    wardrop: bool = False,
) -> None:
    """Asigna `modo_elegido`/`utilidad_elegida` a cada agente **una sola vez**, a
    partir del estado final, muestreando de las probabilidades del grupo
    (vectorizado: `rng.choice(size=nₐ)`). Los registros por agente alimentan las
    figuras agente‑nivel; el muestreo (no argmax) preserva modos minoritarios
    como la bici.

    Con `wardrop=True` el reparto del grupo ya es degenerado —toda la masa en el
    mejor modo—, así que muestrear de él devuelve ese modo para todos los
    agentes del grupo. Es lo correcto: bajo equilibrio determinístico no hay
    heterogeneidad de gustos que separe a dos agentes idénticos."""
    for g in grupos:
        utils, probs = _probs_grupo(
            g, ciudad, demand, tiempos_por_celda, modos_habilitados, wardrop
        )
        n = len(g.agentes)
        pvec = np.array([probs.get(m, 0.0) for m in _MODOS])
        total = float(pvec.sum())
        if total <= 0.0:
            for a in g.agentes:
                a.modo_elegido = None  # agente varado
                a.utilidad_elegida = 0.0
            continue
        pvec = pvec / total
        idx = rng.choice(len(_MODOS), size=n, p=pvec)
        for a, k in zip(g.agentes, idx, strict=True):
            modo = _MODOS[int(k)]
            a.modo_elegido = modo
            a.utilidad_elegida = utils[modo].valor


def iter_msa(
    sim: SimulationConfig, trace: ConvergenceTrace | None = None
) -> Iterator[IterationSnapshot]:
    """Generador que emite una IterationSnapshot por iteración (streaming).

    Si se pasa `trace`, **popula el ConvergenceTrace completo en el mismo
    recorrido**: snapshots, registros por agente (estado final), capacidades y
    emisiones. Así el resultado completo se obtiene en **una sola corrida** (antes
    el worker corría la simulación dos veces). `run_msa` no es más que consumir
    este generador con un `trace`.
    """
    rng = np.random.default_rng(sim.seed)
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)

    agentes = generar_poblacion(
        ciudad=ciudad,
        densidad_hab_km=sim.city.densidad_hab_km,
        share_estratos=sim.city.share_estratos,
        demand_config=sim.demand,
        teletrabajo_factor=sim.city.teletrabajo_factor,
        rng=rng,
    )
    yield from _iter_loop(sim, ciudad, agentes, rng, trace)


def iter_msa_desde_suelo(
    sim: SimulationConfig,
    land_use_config: LandUseConfig,
    trace: ConvergenceTrace | None = None,
    localizacion: Literal["equilibrio", "original"] = "equilibrio",
    promediar_flujos: bool = False,
) -> Iterator[IterationSnapshot]:
    """Igual que :func:`iter_msa` pero la población se deriva del **uso de suelo**
    (opción A del feed suelo→transporte): los `S_i` hogares que la ciudad ofrece
    en cada celda se reparten entre estratos según una matriz `Q`
    (`N[h,i] = mayor_residuo(S_i·Q[h,i])`, con `Σ_h = S_i` exacto), en vez de la
    densidad plana `densidad_hab_km` y el `share_estratos` global. La envolvente
    de población es la oferta `S` (misma que las figuras y que el loop acoplado);
    conserva los hogares por estrato (`Σ_i N[h,i] = H_h`).

    El parámetro `localizacion` decide de dónde sale `Q` — es decir, **dónde vive
    cada estrato**:

    - ``"equilibrio"`` (default): se resuelve el equilibrio de pujas de suelo y se
      usa su `Q`. Usa la T por defecto (flujo libre a la velocidad de referencia),
      igual que la pestaña *Uso de Suelo*, así que el `Q` coincide con el que se
      visualiza ahí para la misma config.
    - ``"original"``: el equilibrio de pujas **no se ha aplicado**, así que la
      localización es la ORIGINAL — mezcla uniforme `π_h = H_h/ΣH` en todas las
      celdas (`Q[h,i] = π_h`). No se resuelve el suelo. La envolvente `S` es la
      misma; sólo cambia la composición por estrato de cada celda.

    El loop iterativo completo (feedback suelo↔transporte) sigue viviendo en el
    módulo acoplado."""
    rng = np.random.default_rng(sim.seed)
    L = sim.city.n_celdas
    CBD = L // 2
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)
    # Envolvente de oferta S(i): la misma en ambos modos (dónde hay vivienda).
    N_total = int(sum(land_use_config.H_por_estrato))
    S = generar_oferta(
        forma=land_use_config.forma,
        I=L,
        N=N_total,
        CBD=CBD,
        sigma_frac=land_use_config.oferta_sigma_frac,
        forma_param=land_use_config.forma_param,
    )
    if localizacion == "original":
        # Localización original: mezcla uniforme π_h en cada celda (sin resolver).
        H = np.asarray(land_use_config.H_por_estrato, dtype=float)
        total = float(H.sum())
        pi = H / total if total > 0 else np.full(len(H), 1.0 / max(len(H), 1))
        Q = np.tile(pi.reshape(-1, 1), (1, L))
    else:
        # Localización de equilibrio de pujas: se resuelve con esta misma oferta S.
        city = LandUseCity.build(
            L=L,
            CBD=CBD,
            cfg=land_use_config,
            rng=rng,
            ancho_celda_km=ciudad.ancho_celda_km,
            S=S,
        )
        assert city.result is not None
        Q = city.result.Q
    agentes = generar_poblacion_desde_land_use_det(
        Q=Q,
        S=S,
        cbd_index=CBD,
        demand_config=sim.demand,
        teletrabajo_factor=sim.city.teletrabajo_factor,
    )
    yield from _iter_loop(sim, ciudad, agentes, rng, trace, promediar_flujos)


def _iter_loop(
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    agentes: list[Agente],
    rng: np.random.Generator,
    trace: ConvergenceTrace | None = None,
    promediar_flujos: bool = False,
) -> Iterator[IterationSnapshot]:
    """Loop MSA sobre una **población ya construida** (compartido por `iter_msa`
    y el loop acoplado). Si se pasa `trace`, lo popula por completo.

    `promediar_flujos` cambia CUÁL variable promedia el MSA, y existe solo para
    medir: el default (`False`) es el comportamiento histórico y ninguna ruta de
    producción lo activa. No es un campo del schema a propósito — moverlo ahí
    obligaría a tocar los espejos TS, el golden y los escenarios guardados.

      * `False` — promedia los TIEMPOS: `t <- f·c(x(t)) + (1−f)·t`, y los flujos
        se recalculan frescos cada iteración desde los tiempos promediados.
      * `True` — promedia los FLUJOS y recalcula los tiempos desde el flujo
        promediado: `x <- f·x* + (1−f)·x`, `t = c(x)`. Es el algoritmo estándar
        (Boyles, Lownes & Unnikrishnan, "Transportation Network Analysis", §6.2
        p. 159), y el único para el que vale el argumento de convergencia: con
        `x*` todo-o-nada, `x*−x` es dirección de descenso de la función de
        Beckmann (p. 160), y eso se apoya en promediar la variable primal.

    El paso `f = 1/(it+1)` es el mismo en ambos, e incluye la inicialización
    `x <- x*` de la iteración 0 (con `it=0`, `f=1`).
    """
    grupos, n_tele = _agrupar_agentes(agentes)
    if trace is not None:
        trace.agentes = agentes

    d_ac: tuple[NDArray[np.float64], ...] | None = None
    tiempos_actuales: list[TiemposObservados] | None = None
    t_auto_ac = np.zeros(ciudad.n_celdas)
    t_bici_ac = np.zeros(ciudad.n_celdas)
    t_tren_acc_ac = np.zeros(ciudad.n_celdas)
    t_tren_esp_ac = np.zeros(ciudad.n_celdas)
    t_tren_v_ac = np.zeros(ciudad.n_celdas)
    estables = 0  # iteraciones consecutivas bajo tolerancia
    last_state: dict | None = None

    for it in range(sim.max_iter):
        conteo, d_auto, d_metro, d_bici, d_caminata = _correr_iteracion(
            grupos,
            n_tele,
            ciudad,
            sim.demand,
            tiempos_actuales,
            rng,
            # 'wardrop' carga de forma fraccional igual que 'expected': su
            # reparto ya es degenerado (todo al mejor modo), asi que sortearlo
            # solo agregaria ruido sin cambiar el valor esperado.
            sim.assignment in ("expected", "wardrop"),
            sim.modos_habilitados,
            sim.assignment == "wardrop",
        )

        if promediar_flujos:
            # `d_*` recién salido de `_correr_iteracion` es el target x*: la
            # asignación a los tiempos actuales. Se promedia ACÁ, antes de las
            # funciones de oferta, para que los tiempos salgan del flujo
            # promediado y no al revés.
            f_x = 1.0 / (it + 1)
            nuevos = (d_auto, d_metro, d_bici, d_caminata)
            d_ac = (
                nuevos
                if d_ac is None
                else tuple(f_x * n + (1 - f_x) * a for n, a in zip(nuevos, d_ac, strict=True))
            )
            d_auto, d_metro, d_bici, d_caminata = d_ac

        car_p = sim.supply.car
        bike_p = sim.supply.bike
        train_p = sim.supply.train

        car_result = demora_auto_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            demanda=d_auto,
            v_max_kmh=car_p.v_max_kmh,
            ancho_pista_m=car_p.ancho_pista_m,
            largo_vehiculo_m=car_p.largo_vehiculo_m,
            gap_m=car_p.gap_m,
            L_ciudad_km=ciudad.largo_total_km,
            num_pistas=car_p.num_pistas,
            alpha_bpr=car_p.alpha_bpr,
            beta_bpr=car_p.beta_bpr,
            capacidad_pista=car_p.capacidad_pista,
        )
        bike_result = demora_bici_tramo(
            ubicacion_centro_km=ciudad.cbd_km,
            capacidad=bike_p.capacidad_pista,
            demanda=d_bici,
            v_media=bike_p.v_media_kmh,
            L_ciudad_km=ciudad.largo_total_km,
            alpha=bike_p.alpha_bpr,
            beta=bike_p.beta_bpr,
            pendiente_porcentaje=sim.city.pendiente_porcentaje,
            v_caminata=sim.demand.globales.v_caminata,
        )
        train_result = oferta_tren(
            demanda=d_metro,
            L_ciudad_km=ciudad.largo_total_km,
            x_centro_km=ciudad.cbd_km,
            v_tren_kmh=train_p.v_tren_kmh,
            capacidad_tren=train_p.capacidad_tren,
            num_estaciones=train_p.num_estaciones,
            v_caminata_kmh=train_p.v_caminata_kmh,
            tasa_carga=train_p.tasa_carga,
            tiempo_detencion_min=train_p.tiempo_detencion_min,
            frec_min=train_p.frec_min,
            frec_max=train_p.frec_max,
            anden_alpha=train_p.anden_alpha,
            anden_beta=train_p.anden_beta,
        )

        if tiempos_actuales is None:
            t_auto_ac = car_result.t_usuarios_min.copy()
            t_bici_ac = bike_result.t_usuarios_min.copy()
            t_tren_acc_ac = train_result.t_acceso_min.copy()
            t_tren_esp_ac = train_result.t_espera_min.copy()
            t_tren_v_ac = train_result.t_viaje_min.copy()
            residuo = float("inf")
        else:
            # Con `promediar_flujos` el suavizado ya ocurrió sobre `d_*`, así que
            # los tiempos se toman tal como salen de la oferta (f = 1). Promediar
            # las dos variables amortiguaría dos veces y frenaría la convergencia
            # sin cambiar el punto fijo. El residuo se sigue midiendo igual.
            f = 1.0 if promediar_flujos else 1.0 / (it + 1)
            old_auto = t_auto_ac.copy()
            old_bici = t_bici_ac.copy()
            old_metro = t_tren_acc_ac + t_tren_esp_ac + t_tren_v_ac
            t_auto_ac = f * car_result.t_usuarios_min + (1 - f) * t_auto_ac
            t_bici_ac = f * bike_result.t_usuarios_min + (1 - f) * t_bici_ac
            t_tren_acc_ac = f * train_result.t_acceso_min + (1 - f) * t_tren_acc_ac
            t_tren_esp_ac = f * train_result.t_espera_min + (1 - f) * t_tren_esp_ac
            t_tren_v_ac = f * train_result.t_viaje_min + (1 - f) * t_tren_v_ac
            new_metro = t_tren_acc_ac + t_tren_esp_ac + t_tren_v_ac
            # Residual de TODA la red (no sólo auto): máximo cambio de tiempo en
            # cualquier modo y celda entre iteraciones MSA.
            residuo = float(
                max(
                    np.max(np.abs(t_auto_ac - old_auto)),
                    np.max(np.abs(t_bici_ac - old_bici)),
                    np.max(np.abs(new_metro - old_metro)),
                )
            )

        tiempos_actuales = [
            TiemposObservados(
                auto_total=float(t_auto_ac[i]),
                bici_total=float(t_bici_ac[i]),
                tren_acceso=float(t_tren_acc_ac[i]),
                tren_espera=float(t_tren_esp_ac[i]),
                tren_viaje=float(t_tren_v_ac[i]),
            )
            for i in range(ciudad.n_celdas)
        ]

        snap = IterationSnapshot(
            iter=it,
            f_msa=1.0 / (it + 1),
            modal_split=conteo,
            demanda_auto=d_auto,
            demanda_metro=d_metro,
            demanda_bici=d_bici,
            demanda_caminata=d_caminata,
            t_auto=t_auto_ac.copy(),
            t_bici=t_bici_ac.copy(),
            t_tren_acceso=t_tren_acc_ac.copy(),
            t_tren_espera=t_tren_esp_ac.copy(),
            t_tren_viaje=t_tren_v_ac.copy(),
            frecuencia_metro=train_result.frecuencia_operativa,
            frecuencia_teorica_metro=train_result.frecuencia_teorica,
            residuo=residuo,
        )
        if trace is not None:
            trace.iteraciones.append(snap)
            last_state = {
                "capacidad": car_result.capacidad_direccion,
                "v_libre": car_result.v_libre_kmh,
                "alpha": car_result.alpha_bpr,
                "beta": car_result.beta_bpr,
                "carga_metro": train_result.carga_por_tramo,
                "estaciones": train_result.estaciones_km,
                "frecuencia": train_result.frecuencia_operativa,
                "flujos_auto": car_result.flujos_veh_por_hora,
                "flujos_bici": bike_result.flujos_bici_por_hora,
            }
        yield snap

        # Criterio de convergencia: residual < tolerancia en 2 iteraciones
        # consecutivas (robusto al ruido estocástico del residual). Fallback a
        # max_iter. Con tolerance=0 nunca corta (sólo número de iteraciones).
        if sim.tolerance > 0 and residuo < sim.tolerance:
            estables += 1
            if estables >= 2:
                if trace is not None:
                    trace.converged = True
                break
        else:
            estables = 0

    if trace is not None:
        _finalizar_trace(trace, sim, ciudad, grupos, tiempos_actuales, rng, last_state)


def run_msa(sim: SimulationConfig) -> ConvergenceTrace:
    """Ejecuta el loop MSA completo hasta convergencia o `max_iter`.

    Es simplemente consumir `iter_msa` con un `trace`: un único recorrido que
    produce el resultado completo (snapshots + agentes + capacidades + emisiones).
    """
    trace = ConvergenceTrace()
    for _ in iter_msa(sim, trace=trace):
        pass
    return trace


def run_msa_con_poblacion(
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    agentes: list[Agente],
    rng: np.random.Generator,
) -> ConvergenceTrace:
    """Corre el MSA sobre una población dada (la usa el loop acoplado, que
    construye los agentes desde el uso de suelo). Devuelve el trace completo."""
    trace = ConvergenceTrace()
    for _ in _iter_loop(sim, ciudad, agentes, rng, trace):
        pass
    return trace


def _demanda_esperada_por_estrato(
    grupos: list[_GrupoDemanda],
    ciudad: CiudadLineal,
    demand: DemandConfig,
    tiempos_por_celda: list[TiemposObservados] | None,
    modos_habilitados: tuple[str, ...] | None,
    wardrop: bool = False,
) -> NDArray[np.float64]:
    """Demanda esperada (nₐ·prob) por estrato·modo·celda del estado dado —
    forma [estrato 0..2, modo (orden _MODOS), celda]. Es la Fig. 9 desagregada
    por estrato: al usar el flujo esperado (no el modo sorteado por agente) sale
    continua bajo cualquier asignación. Teletrabajo va aparte (no viaja)."""
    arr = np.zeros((3, len(_MODOS), ciudad.n_celdas))
    for g in grupos:
        _, probs = _probs_grupo(g, ciudad, demand, tiempos_por_celda, modos_habilitados, wardrop)
        e = int(g.estrato) - 1
        if not 0 <= e < 3:
            continue
        n = len(g.agentes)
        for k, m in enumerate(_MODOS):
            arr[e, k, g.celda] += n * probs.get(m, 0.0)
    return arr


def _finalizar_trace(
    trace: ConvergenceTrace,
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    grupos: list[_GrupoDemanda],
    tiempos_actuales: list[TiemposObservados] | None,
    rng: np.random.Generator,
    last_state: dict | None,
) -> None:
    """Completa el `trace` tras el loop: registros por agente (una sola pasada),
    capacidades del estado final y emisiones de CO₂."""
    # Registros por agente a partir del estado convergido, para figuras agente‑nivel.
    _asignar_modos_agentes(
        grupos,
        ciudad,
        sim.demand,
        tiempos_actuales,
        rng,
        sim.modos_habilitados,
        sim.assignment == "wardrop",
    )
    # Demanda esperada por estrato·modo·celda (reparto modal espacial por estrato).
    trace.demanda_estrato = _demanda_esperada_por_estrato(
        grupos,
        ciudad,
        sim.demand,
        tiempos_actuales,
        sim.modos_habilitados,
        sim.assignment == "wardrop",
    )
    if last_state is None:
        return

    trace.capacidad_auto = last_state["capacidad"]
    trace.v_libre_auto = last_state["v_libre"]
    trace.alpha_auto_bpr = last_state["alpha"]
    trace.beta_auto_bpr = last_state["beta"]
    trace.carga_metro = last_state["carga_metro"]
    trace.estaciones_km = last_state["estaciones"]
    trace.flujos_auto_veh_h = last_state["flujos_auto"]
    trace.flujos_bici_veh_h = last_state["flujos_bici"]

    # Emisiones de CO₂ a partir del estado físico final (flujos + BPR → v_local;
    # metro por tren-km con la frecuencia del equilibrio — ver D-29).
    if last_state["estaciones"] is not None:
        em = calcular_emisiones(
            flujos_auto=last_state["flujos_auto"],
            frecuencia_metro=last_state["frecuencia"],
            estaciones_km=last_state["estaciones"],
            capacidad_auto=last_state["capacidad"],
            alpha_bpr=last_state["alpha"],
            beta_bpr=last_state["beta"],
            v_libre_kmh=last_state["v_libre"],
            largo_ciudad_km=ciudad.largo_total_km,
            n_celdas=ciudad.n_celdas,
            factor_emision_metro_tren_km=sim.demand.globales.factor_emision_metro_tren_km,
            factor_flota_auto=sim.demand.globales.factor_flota_auto,
        )
        trace.emisiones_total_kg = em.total_kg_hora
        trace.emisiones_auto_kg = em.auto_kg_hora
        trace.emisiones_metro_kg = em.metro_kg_hora
        trace.emisiones_perfil_kg = em.perfil_espacial_kg
