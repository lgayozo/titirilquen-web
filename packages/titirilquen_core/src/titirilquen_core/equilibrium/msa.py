"""Método de Promedios Sucesivos (MSA) para el equilibrio oferta-demanda.

Portado y extendido desde `titirilquen-repo/app.py:470-524`. Cambios:

- Criterio de convergencia real: brecha no amortiguada
  `‖c(x(t_{n−1})) − t_{n−1}‖_∞ < tol` (D8). Si `tol=0`, se respeta `max_iter`
  como antes (ver D-10).
- Retorna `ConvergenceTrace` con snapshot por iteración para visualización
  en vivo (antes este dato se perdía tras el loop).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike, NDArray

from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import DemandConfig, SimulationConfig, StratumId
from titirilquen_core.constantes import MODOS
from titirilquen_core.demand.choice import probabilidades_logit, probabilidades_todo_o_nada
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.emissions import calcular_emisiones
from titirilquen_core.land_use.accesibilidad import T_flujo_libre, lambda_desde_demanda
from titirilquen_core.land_use.allocation import asignar_hogares_simple
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.supply import generar_oferta
from titirilquen_core.population import Agente, _mayor_residuo, generar_poblacion_desde_land_use_det
from titirilquen_core.supply.oferta import resolver_oferta, resolver_red_vacia

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
    #: Tiempo de bici con la red vacía; fijo en toda la corrida. Es sobre el que
    #: se evalúan los escalones y el corte de la bici (D9, `TiemposObservados`).
    t_bici_libre: NDArray[np.float64]
    t_tren_acceso: NDArray[np.float64]
    t_tren_espera: NDArray[np.float64]
    t_tren_viaje: NDArray[np.float64]
    frecuencia_metro: float
    #: Frecuencia sin recortar (`carga/K`). Comparada con `frecuencia_metro`
    #: revela si `frec_min`/`frec_max` estan mordiendo — ver AT-08/AT-09.
    frecuencia_teorica_metro: float
    #: Brecha NO amortiguada de la iteración (min): `max |c(x(t)) − t|` sobre
    #: modos y celdas, con `t` los tiempos con que se calculó la demanda y
    #: `c(x(t))` los que devuelve la red cargada con ella. Hasta D8 era el cambio
    #: del iterado amortiguado, `f · (esto)`, y con f = 1/(n+1) la tolerancia se
    #: aflojaba sola en cada iteración (Boyles et al., p. 314).
    residuo: float


@dataclass
class ConvergenceTrace:
    """Resultado completo del loop MSA."""

    iteraciones: list[IterationSnapshot] = field(default_factory=list)
    converged: bool = False
    #: Brecha NO amortiguada del estado final (min): se recalcula la demanda con
    #: los tiempos finales, se resuelve la oferta con ESA demanda y se mide el
    #: máximo cambio de tiempo en cualquier modo y celda (D-39). Es la misma
    #: medida que `residuo` desde D8, pero un paso más allá —sobre los tiempos
    #: que el loop entrega— y siempre con flujos esperados, así que no trae el
    #: ruido de muestreo de 'montecarlo'.
    gap_final_min: float = float("nan")
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
    #: La `Q[h, i]` con que se pobló la ciudad (qué fracción de la celda i es
    #: del estrato h). Es la única fuente para correr otra política con la
    #: misma gente en el mismo lugar (`Q_dada`, D11c).
    localizacion_Q: NDArray[np.float64] | None = None  # noqa: N815 — la Q del libro


#: Alias local del orden canónico (`titirilquen_core.constantes.MODOS`).
_MODOS = MODOS


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
    todo_o_nada: bool = False,
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
    reparto = probabilidades_todo_o_nada if todo_o_nada else probabilidades_logit
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
        _, probs = _probs_grupo(g, ciudad, demand, tiempos_por_celda, modos_habilitados)
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


def _utilidad_y_reparto_ton(
    grupos: list[_GrupoDemanda],
    ciudad: CiudadLineal,
    demand: DemandConfig,
    tiempos_por_celda: list[TiemposObservados] | None,
    modos_habilitados: tuple[str, ...] | None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Utilidad `V[g, m]` (−∞ si el modo es infactible) y carga todo-o-nada
    `y[g, m]` de cada grupo, en el orden de `_MODOS` (D-70)."""
    V = np.full((len(grupos), len(_MODOS)), -np.inf)
    y = np.zeros((len(grupos), len(_MODOS)))
    for k, g in enumerate(grupos):
        utils, probs = _probs_grupo(g, ciudad, demand, tiempos_por_celda, modos_habilitados, True)
        for j, m in enumerate(_MODOS):
            if m in utils and utils[m].feasible:
                V[k, j] = utils[m].valor
            y[k, j] = probs.get(m, 0.0)
    return V, y


def _costo_en_exceso_medio(
    x: NDArray[np.float64],
    V: NDArray[np.float64],
    n: NDArray[np.float64],
    b_t: NDArray[np.float64],
) -> float:
    """Brecha del equilibrio de usuario (D-70): lo que cada viajero paga, en
    promedio, por sobre el mejor modo de su grupo, en minutos de viaje
    equivalentes: `Σ n·x·(V* − V)/|b_t| / Σ n·x`. Vale 0 exactamente en el
    equilibrio: todo modo usado por un grupo es uno de sus mejores modos.

    Es la medida estándar del equilibrio de usuario (*average excess cost*),
    no la brecha en tiempos del logit, porque bajo todo o nada la respuesta a
    los tiempos de un equilibrio no es única —un grupo indiferente puede ir a
    cualquiera de sus mejores modos— y comparar tiempos frescos la haría saltar
    aunque el estado ya sea un equilibrio."""
    masa = n[:, None] * x
    total = float(masa.sum())
    if total <= 0.0:
        return 0.0
    v_max = np.max(V, axis=1, keepdims=True)
    exceso = np.subtract(v_max, V, out=np.zeros_like(V), where=masa > 0) / b_t[:, None]
    return float((masa * exceso).sum() / total)


def _asignar_modos_agentes(
    grupos: list[_GrupoDemanda],
    ciudad: CiudadLineal,
    demand: DemandConfig,
    tiempos_por_celda: list[TiemposObservados] | None,
    rng: np.random.Generator,
    modos_habilitados: tuple[str, ...] | None = None,
) -> None:
    """Asigna `modo_elegido`/`utilidad_elegida` a cada agente **una sola vez**, a
    partir del estado final, muestreando de las probabilidades del grupo
    (vectorizado: `rng.choice(size=nₐ)`). Los registros por agente alimentan las
    figuras agente‑nivel; el muestreo (no argmax) preserva modos minoritarios
    como la bici. Todo o nada asigna sus agentes en `_finalizar_ton` (D-70)."""
    for g in grupos:
        utils, probs = _probs_grupo(g, ciudad, demand, tiempos_por_celda, modos_habilitados)
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


def iter_msa_desde_suelo(
    sim: SimulationConfig,
    land_use_config: LandUseConfig,
    trace: ConvergenceTrace | None = None,
    localizacion: Literal["equilibrio", "original"] = "equilibrio",
    promediar_flujos: bool = False,
    Q_dada: ArrayLike | None = None,
) -> Iterator[IterationSnapshot]:
    """El MSA de transporte con la población derivada del **uso de suelo**: los
    `S_i` hogares que la ciudad ofrece en cada celda se reparten entre estratos
    según una matriz `Q` (`N[h,i] = mayor_residuo(S_i·Q[h,i])`, con `Σ_h = S_i`
    exacto). Es la ÚNICA ruta desde sep-2026; antes existía `iter_msa` con una
    densidad plana que la app no usaba (D-46, C-02). La envolvente
    de población es la oferta `S` (misma que las figuras y que el loop acoplado);
    conserva los hogares por estrato (`Σ_i N[h,i] = H_h`).

    El parámetro `localizacion` decide de dónde sale `Q` — es decir, **dónde vive
    cada estrato**:

    - ``"equilibrio"`` (default): se resuelve el equilibrio de pujas de suelo y se
      usa su `Q`. Usa la accesibilidad a flujo libre (logsum mensual, D-34),
      igual que la pestaña *Uso de Suelo*, así que el `Q` coincide con el que se
      visualiza ahí para la misma config.
    - ``"original"``: el equilibrio de pujas **no se ha aplicado**, así que la
      localización es la ORIGINAL — mezcla uniforme `π_h = H_h/ΣH` en todas las
      celdas (`Q[h,i] = π_h`). No se resuelve el suelo. La envolvente `S` es la
      misma; sólo cambia la composición por estrato de cada celda.

    Con ``Q_dada`` (sólo con ``"equilibrio"``) la localización no se resuelve:
    se usa esa `Q`, típicamente la `localizacion_Q` de la corrida de otra
    tarjeta. Es la estática comparativa de corto plazo de Comparar (D11c): la
    misma gente en el mismo lugar, y sólo cambia el transporte.

    El loop iterativo completo (feedback suelo↔transporte) sigue viviendo en el
    módulo acoplado."""
    if Q_dada is not None and localizacion != "equilibrio":
        raise ValueError(
            "Q_dada reemplaza a la Q de equilibrio; con «original» la Q es la "
            "mezcla uniforme y no se entrega"
        )
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
    elif Q_dada is not None:
        Q = _valida_Q(Q_dada, S, len(land_use_config.H_por_estrato))
        # Mismos números aleatorios que la corrida que produjo esta Q: el
        # equilibrio de suelo reparte las parcelas con el `rng` antes del
        # MSA (`LandUseCity.update`). Sin este sorteo, la tarjeta congelada
        # arrancaría el MSA con otro estado del generador y el Δ contra la
        # base traería ruido de muestreo además de la política.
        asignar_hogares_simple(
            Q=Q, S=S, H=np.asarray(land_use_config.H_por_estrato, dtype=int), rng=rng
        )
    else:
        # Localización de equilibrio de pujas: se resuelve con esta misma oferta S.
        city = LandUseCity.build(
            L=L,
            CBD=CBD,
            cfg=land_use_config,
            rng=rng,
            ancho_celda_km=ciudad.ancho_celda_km,
            S=S,
            T=T_flujo_libre(
                sim.demand,
                L,
                CBD,
                ciudad.ancho_celda_km,
                sim.modos_habilitados,
                supply=sim.supply,
                pendiente_porcentaje=sim.city.pendiente_porcentaje,
            ),
            lambda_h=lambda_desde_demanda(sim.demand),
        )
        assert city.result is not None
        Q = city.result.Q
    agentes = generar_poblacion_desde_land_use_det(
        Q=Q,
        S=S,
        cbd_index=CBD,
        demand_config=sim.demand,
        teletrabajo_factor=sim.demand.globales.teletrabajo_factor,
    )
    if trace is not None:
        trace.localizacion_Q = np.asarray(Q, dtype=float)
    yield from _iter_loop(sim, ciudad, agentes, rng, trace, promediar_flujos)


def _valida_Q(Q: ArrayLike, S: NDArray[np.int_], n_estratos: int) -> NDArray[np.float64]:
    """Una `Q` entregada desde afuera: forma (estratos × celdas), finita, no
    negativa y, en cada celda con vivienda, una columna que suma 1 (reparte la
    celda). Donde `S_i = 0` el equilibrio de suelo deja la columna en cero."""
    Q = np.asarray(Q, dtype=float)
    L = len(S)
    if Q.shape != (n_estratos, L):
        raise ValueError(f"Q_dada tiene forma {Q.shape}; se espera ({n_estratos}, {L})")
    if not np.all(np.isfinite(Q)) or np.any(Q < 0):
        raise ValueError("Q_dada debe ser finita y no negativa")
    if not np.allclose(Q.sum(axis=0)[np.asarray(S) > 0], 1.0, atol=1e-6):
        raise ValueError("cada celda con vivienda debe sumar 1 en Q_dada")
    return Q


def _iter_loop(
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    agentes: list[Agente],
    rng: np.random.Generator,
    trace: ConvergenceTrace | None = None,
    promediar_flujos: bool = False,
) -> Iterator[IterationSnapshot]:
    """Loop MSA sobre una **población ya construida** (compartido por
    `iter_msa_desde_suelo` y el loop acoplado). Si se pasa `trace`, lo popula por completo.

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

    **Todo o nada promedia siempre flujos, y por grupo** (D-70): promediando
    tiempos la respuesta salta entera de modo y el reparto oscila sin converger,
    aunque el equilibrio de usuario existe. Se promedia el reparto de cada grupo
    (no sólo el total por celda) porque lo necesitan la brecha —el costo en
    exceso medio, `_costo_en_exceso_medio`— y el estado final: en el equilibrio
    un grupo indiferente queda repartido entre sus mejores modos.
    """
    grupos, n_tele = _agrupar_agentes(agentes)
    if trace is not None:
        trace.agentes = agentes

    ton = sim.assignment == "todo_o_nada"
    x_ton: NDArray[np.float64] | None = None  # reparto promediado por grupo
    if ton:
        n_g = np.array([len(g.agentes) for g in grupos], dtype=float)
        b_t = np.array([abs(sim.demand.estratos[g.estrato].betas.b_tiempo_viaje) for g in grupos])
        celda_g = np.array([g.celda for g in grupos], dtype=int)
        # La utilidad de la iteración `it` se calcula al final de la `it−1`
        # (sirve para la brecha de ese iterado y para la carga de éste).
        V_ton, y_ton = _utilidad_y_reparto_ton(
            grupos, ciudad, sim.demand, None, sim.modos_habilitados
        )

    d_ac: tuple[NDArray[np.float64], ...] | None = None
    tiempos_actuales: list[TiemposObservados] | None = None
    t_auto_ac = np.zeros(ciudad.n_celdas)
    t_bici_ac = np.zeros(ciudad.n_celdas)
    t_tren_acc_ac = np.zeros(ciudad.n_celdas)
    t_tren_esp_ac = np.zeros(ciudad.n_celdas)
    t_tren_v_ac = np.zeros(ciudad.n_celdas)
    t_bici_libre = resolver_red_vacia(sim, ciudad).bici.t_usuarios_min
    estables = 0  # iteraciones consecutivas bajo tolerancia
    last_state: dict | None = None

    for it in range(sim.max_iter):
        if ton:
            f_x = 1.0 / (it + 1)
            x_ton = y_ton if x_ton is None else f_x * y_ton + (1 - f_x) * x_ton
            masa = n_g[:, None] * x_ton
            dem = [np.zeros(ciudad.n_celdas) for _ in _MODOS]
            for j in range(len(_MODOS)):
                np.add.at(dem[j], celda_g, masa[:, j])
            d_auto, d_metro, d_bici, d_caminata = dem
            conteo: ModalSplit = {
                "Auto": float(masa[:, 0].sum()),
                "Metro": float(masa[:, 1].sum()),
                "Bici": float(masa[:, 2].sum()),
                "Caminata": float(masa[:, 3].sum()),
                "Teletrabajo": float(n_tele),
            }
        else:
            conteo, d_auto, d_metro, d_bici, d_caminata = _correr_iteracion(
                grupos,
                n_tele,
                ciudad,
                sim.demand,
                tiempos_actuales,
                rng,
                sim.assignment == "expected",
                sim.modos_habilitados,
            )

        if promediar_flujos and not ton:
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

        oferta = resolver_oferta(sim, ciudad, d_auto, d_bici, d_metro)
        car_result, bike_result, train_result = oferta.auto, oferta.bici, oferta.tren
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
            # sin cambiar el punto fijo. El residuo se mide con la misma fórmula,
            # pero ya no es la brecha: los dos tiempos que compara salen de
            # flujos que difieren en una fracción f, así que vuelve a ser un
            # cambio amortiguado. Para esta variante la vara es `gap_final_min`.
            f = 1.0 if promediar_flujos or ton else 1.0 / (it + 1)
            old_auto = t_auto_ac.copy()
            old_bici = t_bici_ac.copy()
            old_metro = t_tren_acc_ac + t_tren_esp_ac + t_tren_v_ac
            # Brecha no amortiguada (D8): lo que devuelve la red cargada contra
            # los tiempos con que se calculó la demanda. Es `Δt/f` del promedio
            # de tiempos —`t_nuevo − t = f·(c − t)`—, medido sin dividir.
            residuo = float(
                max(
                    np.max(np.abs(car_result.t_usuarios_min - old_auto)),
                    np.max(np.abs(bike_result.t_usuarios_min - old_bici)),
                    np.max(
                        np.abs(
                            train_result.t_acceso_min
                            + train_result.t_espera_min
                            + train_result.t_viaje_min
                            - old_metro
                        )
                    ),
                )
            )
            t_auto_ac = f * car_result.t_usuarios_min + (1 - f) * t_auto_ac
            t_bici_ac = f * bike_result.t_usuarios_min + (1 - f) * t_bici_ac
            t_tren_acc_ac = f * train_result.t_acceso_min + (1 - f) * t_tren_acc_ac
            t_tren_esp_ac = f * train_result.t_espera_min + (1 - f) * t_tren_esp_ac
            t_tren_v_ac = f * train_result.t_viaje_min + (1 - f) * t_tren_v_ac

        tiempos_actuales = [
            TiemposObservados(
                auto_total=float(t_auto_ac[i]),
                bici_total=float(t_bici_ac[i]),
                bici_libre=float(t_bici_libre[i]),
                tren_acceso=float(t_tren_acc_ac[i]),
                tren_espera=float(t_tren_esp_ac[i]),
                tren_viaje=float(t_tren_v_ac[i]),
            )
            for i in range(ciudad.n_celdas)
        ]
        if ton:
            assert x_ton is not None
            V_ton, y_ton = _utilidad_y_reparto_ton(
                grupos, ciudad, sim.demand, tiempos_actuales, sim.modos_habilitados
            )
            residuo = _costo_en_exceso_medio(x_ton, V_ton, n_g, b_t)

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
            t_bici_libre=t_bici_libre,
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
                "capacidad_practica": car_result.capacidad_practica,
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

        # Criterio de convergencia: brecha no amortiguada < tolerancia en 2
        # iteraciones consecutivas (robusto al ruido estocástico). Fallback a
        # max_iter. Con tolerance=0 nunca corta (sólo número de iteraciones).
        # Con 'montecarlo' el ruido de muestreo deja la brecha en ~0,15–0,75 min
        # y la corrida agota max_iter aunque `gap_final_min`, que carga flujos
        # esperados, quede bajo la tolerancia. Con 'todo_o_nada' el residuo es
        # el costo en exceso medio (D-70), que baja como 1/n: converge, pero
        # con pocas pistas pide más vueltas que el logit.
        if sim.tolerance > 0 and residuo < sim.tolerance:
            estables += 1
            if estables >= 2:
                if trace is not None:
                    trace.converged = True
                break
        else:
            estables = 0

    if trace is not None:
        _finalizar_trace(trace, sim, ciudad, grupos, tiempos_actuales, rng, last_state, x_ton)


def run_msa(
    sim: SimulationConfig,
    land_use_config: LandUseConfig,
    localizacion: Literal["equilibrio", "original"] = "original",
    Q_dada: ArrayLike | None = None,
) -> ConvergenceTrace:
    """Ejecuta el loop MSA completo hasta convergencia o `max_iter`.

    Es simplemente consumir `iter_msa_desde_suelo` con un `trace`: un único
    recorrido que produce el resultado completo (snapshots + agentes +
    capacidades + emisiones).

    Hasta sep-2026 existía una segunda ruta, `iter_msa`, que poblaba la ciudad
    con una densidad plana (`densidad_hab_km` × `share_estratos`) sin pasar por
    el uso de suelo. Era la ruta de `/simulate` y de los tests, y la app nunca
    la usaba: dos fuentes de población para una misma ciudad (D-46, C-02). La
    población viene ahora siempre de `LandUseConfig`; la densidad plana se
    reproduce con `forma="uniforme"` y `localizacion="original"`.
    """
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(
        sim, land_use_config, trace, localizacion=localizacion, Q_dada=Q_dada
    ):
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
) -> NDArray[np.float64]:
    """Demanda esperada (nₐ·prob) por estrato·modo·celda del estado dado —
    forma [estrato 0..2, modo (orden _MODOS), celda]. Es la Fig. 9 desagregada
    por estrato: al usar el flujo esperado (no el modo sorteado por agente) sale
    continua bajo cualquier asignación. Teletrabajo va aparte (no viaja)."""
    arr = np.zeros((3, len(_MODOS), ciudad.n_celdas))
    for g in grupos:
        _, probs = _probs_grupo(g, ciudad, demand, tiempos_por_celda, modos_habilitados)
        e = int(g.estrato) - 1
        if not 0 <= e < 3:
            continue
        n = len(g.agentes)
        for k, m in enumerate(_MODOS):
            arr[e, k, g.celda] += n * probs.get(m, 0.0)
    return arr


def _finalizar_ton(
    trace: ConvergenceTrace,
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    grupos: list[_GrupoDemanda],
    tiempos_actuales: list[TiemposObservados] | None,
    x: NDArray[np.float64],
) -> None:
    """Estado final de todo o nada desde el reparto promediado `x[g, m]` (D-70):
    modos por agente (cuotas de mayor residuo, sin sorteo: no hay gustos que
    separen a dos agentes del mismo grupo), demanda por estrato y la brecha
    final, que es el costo en exceso medio de ese reparto."""
    V, _ = _utilidad_y_reparto_ton(
        grupos, ciudad, sim.demand, tiempos_actuales, sim.modos_habilitados
    )
    arr = np.zeros((3, len(_MODOS), ciudad.n_celdas))
    for k, g in enumerate(grupos):
        n = len(g.agentes)
        if not np.isfinite(V[k]).any():
            for a in g.agentes:
                a.modo_elegido = None  # agente varado
                a.utilidad_elegida = 0.0
            continue
        cuota = n * x[k]
        enteros = _mayor_residuo(cuota, n)
        modos = [j for j in range(len(_MODOS)) for _ in range(int(enteros[j]))]
        for a, j in zip(g.agentes, modos, strict=True):
            a.modo_elegido = _MODOS[j]
            a.utilidad_elegida = float(V[k, j])
        e = int(g.estrato) - 1
        if 0 <= e < 3:
            arr[e, :, g.celda] += cuota
    trace.demanda_estrato = arr
    n_g = np.array([len(g.agentes) for g in grupos], dtype=float)
    b_t = np.array([abs(sim.demand.estratos[g.estrato].betas.b_tiempo_viaje) for g in grupos])
    trace.gap_final_min = _costo_en_exceso_medio(x, V, n_g, b_t)


def _finalizar_trace(
    trace: ConvergenceTrace,
    sim: SimulationConfig,
    ciudad: CiudadLineal,
    grupos: list[_GrupoDemanda],
    tiempos_actuales: list[TiemposObservados] | None,
    rng: np.random.Generator,
    last_state: dict | None,
    reparto_ton: NDArray[np.float64] | None = None,
) -> None:
    """Completa el `trace` tras el loop: registros por agente (una sola pasada),
    capacidades del estado final y emisiones de CO₂.

    Con `reparto_ton` (todo o nada, D-70) el estado final es el reparto
    promediado de cada grupo, no la respuesta todo-o-nada a los tiempos finales:
    en el equilibrio un grupo indiferente queda repartido, y recalcular la
    respuesta lo mandaría entero a uno de sus modos."""
    if reparto_ton is not None:
        _finalizar_ton(trace, sim, ciudad, grupos, tiempos_actuales, reparto_ton)
    else:
        # Registros por agente a partir del estado convergido, para figuras agente‑nivel.
        _asignar_modos_agentes(
            grupos, ciudad, sim.demand, tiempos_actuales, rng, sim.modos_habilitados
        )
        # Demanda esperada por estrato·modo·celda (reparto modal espacial por estrato).
        trace.demanda_estrato = _demanda_esperada_por_estrato(
            grupos, ciudad, sim.demand, tiempos_actuales, sim.modos_habilitados
        )
    if last_state is None:
        return

    # Brecha no amortiguada (D-39): demanda fresca con los tiempos finales →
    # oferta → tiempos; cuánto difieren de los que el loop declaró finales.
    # Con todo o nada la fija `_finalizar_ton` (costo en exceso, D-70).
    snap = trace.iteraciones[-1]
    if reparto_ton is None:
        _, da, dm, db, _ = _correr_iteracion(
            grupos,
            0,
            ciudad,
            sim.demand,
            tiempos_actuales,
            rng,
            expected=True,
            modos_habilitados=sim.modos_habilitados,
        )
        fresca = resolver_oferta(sim, ciudad, da, db, dm)
        metro_final = snap.t_tren_acceso + snap.t_tren_espera + snap.t_tren_viaje
        metro_fresco = fresca.tren.t_acceso_min + fresca.tren.t_espera_min + fresca.tren.t_viaje_min
        trace.gap_final_min = float(
            max(
                np.max(np.abs(fresca.auto.t_usuarios_min - snap.t_auto)),
                np.max(np.abs(fresca.bici.t_usuarios_min - snap.t_bici)),
                np.max(np.abs(metro_fresco - metro_final)),
            )
        )

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
            # La misma capacidad que la BPR de los tiempos (D6): si no, las
            # emisiones verían otra congestión que la del equilibrio.
            capacidad_auto=last_state["capacidad_practica"],
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
