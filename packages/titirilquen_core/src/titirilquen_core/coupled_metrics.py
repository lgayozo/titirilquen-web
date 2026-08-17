"""Métricas del equilibrio de "Ciudad en equilibrio" (loop suelo ↔ transporte).

Calcula, a partir del `CoupledResult` final, un set de indicadores **por estrato**
(los "diferentes usuarios") y **del sistema** (el equilibrio agregado). Toda la
matemática vive aquí (política del repo); el frontend solo renderiza la tabla.

Reglas de procedencia de los datos (importante para interpretar):

- **Métricas de localización** (dónde vive cada estrato) salen del equilibrio de
  uso de suelo: `N_hi = S_i · Q[h,i]` (hogares esperados de `h` en la parcela
  `i`), suave y determinista.
- **Métricas de transporte** (tiempo, modo, costo, bienestar) salen de la
  **microdata** de agentes de la última corrida MSA, leyendo el tiempo del modo
  efectivamente elegido en el snapshot final.

Caveats de unidades (ver discusión en DISCREPANCIES.md / OVERLEAF_CHANGES.md):

- El **excedente del consumidor** (`delta_excedente_clp`) usa el `E[max]` del
  agente convertido a $ con la utilidad marginal del dinero **propia de cada
  estrato** (`-b_costo_h`). Cuál `E[max]` depende del método de asignación y lo
  decide `bienestar.medida_emparejada`: el logsum bajo los métodos logit, la
  utilidad máxima bajo `todo_o_nada`, donde no hay término aleatorio que
  promediar. El campo `sistema.medida_bienestar` dice cuál se usó. Es comparable
  como *escala monetaria* (eficiencia / disposición a pagar), **no** como
  bienestar interpersonal: cada $1 vale distinto para un rico que para un pobre,
  y `b_costo` varía ~7.5 veces entre estratos. Para la lectura distributiva usar
  `carga_costo_ingreso` y el tiempo.
- Se reporta como **Δ contra la red vacía** (misma infraestructura con demanda
  cero: BPR(0) en auto/bici, tren a frecuencia mínima, mismas estaciones), no
  como nivel: el logsum incluye las ASC, así que el nivel absoluto tiene un
  cero arbitrario y no significa nada — solo las diferencias son
  interpretables. El signo es informativo: Δ < 0 ⇒ domina la congestión
  (demoras, espera, modos que dejan de ser factibles); Δ > 0 ⇒ domina el
  **efecto Mohring** (más demanda ⇒ más frecuencia de metro ⇒ menos espera que
  con la red vacía).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.bienestar import (
    MedidaBienestar,
    medida_emparejada,
    medidas_de_utilidad,
)
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.constantes import CATEGORIAS_MODALES, CategoriaModal
from titirilquen_core.demand.utility import TiemposObservados
from titirilquen_core.equilibrium.msa import ConvergenceTrace, IterationSnapshot
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.land_use.equilibrium import LandUseResult
from titirilquen_core.supply.oferta import resolver_red_vacia

if TYPE_CHECKING:
    from titirilquen_core.config import StratumId

VIAJES_MES = 44
"""Viajes de conmutación por mes (2 por día laboral × 22 días) para convertir
el costo por viaje a carga mensual costo/ingreso (D-27)."""

_MODOS_VIAJE: tuple[str, ...] = ("Auto", "Metro", "Bici", "Caminata")
# Categorías reportadas en el reparto modal (suman 1 sobre todos los agentes).
_CATEGORIAS_MODALES: tuple[str, ...] = CATEGORIAS_MODALES


@dataclass(frozen=True)
class StratumMetrics:
    """Indicadores de un estrato (un "tipo de usuario") en el equilibrio final."""

    estrato: int
    """1 = alto, 2 = medio, 3 = bajo."""

    n_hogares: float
    """Hogares del estrato (Σ_i S_i·Q[h,i] ≈ H_h)."""

    dist_media_cbd_km: float
    """Distancia media de residencia al CBD, ponderada por hogares (km)."""

    tiempo_medio_min: float
    """Tiempo de viaje medio de los agentes que viajan (min)."""

    reparto_modal: dict[CategoriaModal, float]
    """Share por categoría (Auto/Metro/Bici/Caminata/Teletrabajo/Varado); suma 1."""

    costo_medio_clp: float
    """Costo monetario medio del viaje, sobre los que viajan ($)."""

    delta_excedente_clp: float
    """Δ excedente del consumidor vs la **red vacía** ((logsum − logsum_0) /
    −b_costo), en $. Δ<0 ⇒ costo neto de la congestión; Δ>0 ⇒ domina el efecto
    Mohring (frecuencia endógena). Eficiencia/DAP, NO bienestar interpersonal —
    ver módulo docstring."""

    carga_costo_ingreso: float
    """Carga **mensual**: (costo medio por viaje · 44 viajes/mes) / ingreso
    mensual del estrato ($/mes). Fracción interpretable (~0.02–0.30) — antes
    mezclaba costo por viaje en $ con un ingreso adimensional (D-27)."""


@dataclass(frozen=True)
class SystemMetrics:
    """Indicadores del equilibrio agregado (todo el sistema)."""

    convergio_exterior: bool
    """¿El loop suelo↔transporte alcanzó `outer_tol`?"""

    iteraciones_exteriores: int
    residual_final_min: float | None
    """Residuo ||ΔT||_∞ de la última iteración (min); None si no medible."""

    convergio_msa: bool
    """¿Convergió el MSA interior de la última corrida de transporte?"""

    tiempo_total_pax_min: float
    """Σ sobre agentes del tiempo de viaje (pax·min)."""

    tiempo_medio_min: float
    """Tiempo de viaje medio del sistema (min)."""

    reparto_modal: dict[CategoriaModal, float]
    """Reparto modal global (mismas categorías que por estrato; suma 1)."""

    frecuencia_metro: float
    """Frecuencia operativa del metro en el equilibrio (trenes/h)."""

    emisiones_total_kg: float
    emisiones_auto_kg: float
    emisiones_metro_kg: float

    segregacion_theil: float
    """Índice H de Theil sobre Q ∈ [0,1]. 0 = integrada, 1 = segregación total."""

    delta_bienestar_total_clp: float
    """Σ_h n_hogares_h · ΔCS_h ($). Efecto agregado de bienestar de la demanda
    sobre la red (congestión vs Mohring), respecto a la red vacía."""

    medida_bienestar: MedidaBienestar
    """Con qué medida se calculó el ΔCS: `logsum` bajo los métodos logit,
    `utilidad_maxima` bajo `todo_o_nada`. La decide el núcleo
    (`bienestar.medida_emparejada`), igual que en el Sandbox, para que las dos
    páginas no contesten distinto la misma pregunta."""

    ratio_tiempo_bajo_alto: float | None
    """Tiempo medio bajo / alto. >1 ⇒ los pobres viajan más (regresivo)."""

    ratio_carga_bajo_alto: float | None
    """Carga (costo/ingreso) bajo / alto. >1 ⇒ el transporte pesa más al pobre."""


@dataclass(frozen=True)
class EquilibriumMetrics:
    """Reporte completo del equilibrio de Ciudad en equilibrio."""

    por_estrato: list[StratumMetrics]
    sistema: SystemMetrics


#: El mismo reporte ya convertido a dicts por `asdict`. Es un alias y no un
#: `TypedDict` a propósito: repetir los 20 campos acá sería reintroducir en
#: Python el espejo que se acaba de cerrar en TypeScript. El contrato TS se
#: genera desde las dataclasses de arriba, que son la única declaración.
EquilibriumMetricsJSON = dict[str, Any]


def equilibrium_metrics_to_dict(m: EquilibriumMetrics) -> EquilibriumMetricsJSON:
    """Serializa a un dict JSON-nativo (todos los campos son float/int/bool/str/dict).

    Es `asdict` sin más: la forma JSON **es** la de la dataclass. Por eso
    `tools/genera_contrato.py` emite las interfaces TypeScript desde estas
    dataclasses y no desde una copia — no hay dónde divergir.
    """
    return cast("EquilibriumMetricsJSON", asdict(m))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tiempos_observados(snap: IterationSnapshot, i: int) -> TiemposObservados:
    """Reconstruye los tiempos observados de la celda `i` desde el snapshot final."""
    return TiemposObservados(
        auto_total=float(snap.t_auto[i]),
        bici_total=float(snap.t_bici[i]),
        tren_acceso=float(snap.t_tren_acceso[i]),
        tren_espera=float(snap.t_tren_espera[i]),
        tren_viaje=float(snap.t_tren_viaje[i]),
    )


def _tiempo_modo(
    snap: IterationSnapshot, modo: str, i: int, dist_km: float, v_caminata: float
) -> float:
    """Tiempo (min) del `modo` en la celda `i`, según el snapshot final."""
    if modo == "Auto":
        return float(snap.t_auto[i])
    if modo == "Metro":
        return float(snap.t_tren_acceso[i] + snap.t_tren_espera[i] + snap.t_tren_viaje[i])
    if modo == "Bici":
        return float(snap.t_bici[i])
    return dist_km / v_caminata * 60.0  # Caminata


def _costo_modo(modo: str, dist_km: float, gl) -> float:
    """Costo monetario ($) del `modo` para un viaje de `dist_km`."""
    if modo == "Auto":
        return dist_km * gl.costo_combustible_km + gl.costo_parking
    if modo == "Metro":
        return float(gl.costo_tarifa_metro)
    return 0.0  # Bici / Caminata


def _tiempos_red_vacia(sim: SimulationConfig, ciudad: CiudadLineal) -> list[TiemposObservados]:
    """Tiempos por celda con la **red vacía** (demanda cero): BPR(0) en auto y
    bici, tren a frecuencia mínima con las mismas estaciones. Es el baseline del
    ΔCS — la misma infraestructura sin nadie usándola."""
    oferta = resolver_red_vacia(sim, ciudad)
    car0, bike0, train0 = oferta.auto, oferta.bici, oferta.tren
    return [
        TiemposObservados(
            auto_total=float(car0.t_usuarios_min[i]),
            bici_total=float(bike0.t_usuarios_min[i]),
            tren_acceso=float(train0.t_acceso_min[i]),
            tren_espera=float(train0.t_espera_min[i]),
            tren_viaje=float(train0.t_viaje_min[i]),
        )
        for i in range(ciudad.n_celdas)
    ]


def _utilidad_esperada(
    tiempos: TiemposObservados,
    *,
    estrato: int,
    celda: int,
    tiene_auto: bool,
    ciudad: CiudadLineal,
    sim: SimulationConfig,
    medida: MedidaBienestar,
) -> float:
    """`E[max]` del agente en útiles, en la medida que pida `medida`.

    Delega en `bienestar.medidas_de_utilidad`, que es la única implementación de
    las dos fórmulas en el núcleo. Antes este módulo tenía su propia copia del
    logsum —con un filtro de factibilidad levemente distinto— y no aplicaba el
    emparejamiento con el método de asignación, así que bajo `todo_o_nada` esta
    página y el Sandbox medían el bienestar con reglas diferentes.
    """
    par = medidas_de_utilidad(
        estrato,  # type: ignore[arg-type]
        celda,
        tiene_auto,
        ciudad,
        sim,
        tiempos,
    )
    if par is None:
        return float("nan")
    logsum, maximo = par
    return maximo if medida == "utilidad_maxima" else logsum


def _theil(Q: np.ndarray) -> float:
    """Índice H de Theil sobre Q (estratos x parcelas). 0 = integrada, 1 = segregada."""
    total_h = Q.sum(axis=1)
    total_i = Q.sum(axis=0)
    N = float(Q.sum())
    if N <= 0:
        return 0.0

    def entropy(p: np.ndarray) -> float:
        p = p[p > 0]
        return float(-(p * np.log(p)).sum())

    E = entropy(total_h / N)
    if E == 0:
        return 0.0
    weighted = 0.0
    for i in range(Q.shape[1]):
        Ni = total_i[i]
        if Ni <= 0:
            continue
        weighted += (Ni / N) * entropy(Q[:, i] / Ni)
    return 1.0 - weighted / E


# ---------------------------------------------------------------------------
# Cálculo principal
# ---------------------------------------------------------------------------


def compute_equilibrium_metrics(
    *,
    land_use: LandUseResult,
    trace: ConvergenceTrace,
    S: NDArray[np.float64] | NDArray[np.int_],
    sim: SimulationConfig,
    land_use_config: LandUseConfig,
    T_residual: float | None = None,
    converged: bool = False,
    iterations_count: int = 1,
) -> EquilibriumMetrics:
    """Calcula el reporte de métricas de un equilibrio (una OuterIteration).

    Recibe las piezas de la iteración (suelo, transporte y agentes mutuamente
    consistentes) y la oferta `S` (constante en el loop). Diseñada para llamarse
    por iteración exterior desde `coupled.py` y adjuntar el resultado a la
    `OuterIteration` — así viaja por el streaming sin recomputar.
    """
    lu = land_use
    snap = trace.iteraciones[-1]
    agentes = trace.agentes

    n_strata = lu.Q.shape[0]
    L = sim.city.n_celdas
    cbd = L // 2
    dx_km = sim.city.largo_ciudad_km / L
    ciudad = CiudadLineal(n_celdas=L, largo_total_km=sim.city.largo_ciudad_km)
    gl = sim.demand.globales

    S = np.asarray(S, dtype=float)
    Q = np.asarray(lu.Q, dtype=float)
    N = Q * S[None, :]  # N[h,i] = hogares esperados de h en parcela i
    dist = np.abs(np.arange(L) - cbd).astype(float) * dx_km

    ingresos = [float(s.y) for s in land_use_config.estratos]
    b_costo = [
        float(sim.demand.estratos[cast("StratumId", h + 1)].betas.b_costo) for h in range(n_strata)
    ]

    # --- Acumuladores de transporte por estrato (sobre agentes que viajan) ---
    t_sum = np.zeros(n_strata)
    c_sum = np.zeros(n_strata)
    cs_sum = np.zeros(n_strata)
    viajan = np.zeros(n_strata, dtype=int)
    modal = np.zeros((n_strata, len(_CATEGORIAS_MODALES)), dtype=float)
    total_ag = np.zeros(n_strata, dtype=int)
    cat_idx = {c: k for k, c in enumerate(_CATEGORIAS_MODALES)}

    # La medida del excedente la manda el método de asignación, igual que en el
    # Sandbox: sin dispersión de gustos el E[max] del agente es el máximo, no el
    # logsum. Se aplica a los DOS términos del Δ —red real y red vacía— porque
    # restar medidas distintas no daría un delta de nada.
    medida = medida_emparejada(sim.assignment)

    # E[max] depende solo de (estrato, celda, tiene_auto): memoizar.
    # `cache_ff` es el baseline de red vacía del ΔCS (no depende del snapshot).
    cache_ls: dict[tuple[int, int, bool], float] = {}
    cache_ff: dict[tuple[int, int, bool], float] = {}
    tiempos_obs = [_tiempos_observados(snap, i) for i in range(L)]
    tiempos_ff = _tiempos_red_vacia(sim, ciudad)

    for a in agentes:
        h = a.estrato - 1
        total_ag[h] += 1
        if a.teletrabaja:
            modal[h, cat_idx["Teletrabajo"]] += 1
            continue
        if a.modo_elegido is None:
            modal[h, cat_idx["Varado"]] += 1
            continue
        i = a.celda_origen
        d = dist[i]
        modal[h, cat_idx[a.modo_elegido]] += 1
        t_sum[h] += _tiempo_modo(snap, a.modo_elegido, i, d, gl.v_caminata)
        c_sum[h] += _costo_modo(a.modo_elegido, d, gl)
        key = (a.estrato, i, a.tiene_auto)
        ls = cache_ls.get(key)
        if ls is None:
            ls = _utilidad_esperada(
                tiempos_obs[i],
                estrato=a.estrato,
                celda=i,
                tiene_auto=a.tiene_auto,
                ciudad=ciudad,
                sim=sim,
                medida=medida,
            )
            cache_ls[key] = ls
        ls_ff = cache_ff.get(key)
        if ls_ff is None:
            ls_ff = _utilidad_esperada(
                tiempos_ff[i],
                estrato=a.estrato,
                celda=i,
                tiene_auto=a.tiene_auto,
                ciudad=ciudad,
                sim=sim,
                medida=medida,
            )
            cache_ff[key] = ls_ff
        # ΔCS vs red vacía: el nivel tiene cero arbitrario (ASC); solo la
        # diferencia es interpretable (congestión vs efecto Mohring).
        if not np.isnan(ls) and not np.isnan(ls_ff):
            cs_sum[h] += (ls - ls_ff) / (-b_costo[h])
        viajan[h] += 1

    # --- Construir métricas por estrato ---
    por_estrato: list[StratumMetrics] = []
    for h in range(n_strata):
        n_h = float(N[h].sum())
        d_media = float((N[h] * dist).sum() / n_h) if n_h > 0 else 0.0
        nv = int(viajan[h])
        t_medio = float(t_sum[h] / nv) if nv > 0 else 0.0
        c_medio = float(c_sum[h] / nv) if nv > 0 else 0.0
        cs_medio = float(cs_sum[h] / nv) if nv > 0 else 0.0
        tot = int(total_ag[h])
        reparto = {c: (float(modal[h, k] / tot) if tot > 0 else 0.0) for c, k in cat_idx.items()}
        # Carga mensual: costo por viaje × viajes/mes sobre ingreso mensual (D-27).
        carga = (c_medio * VIAJES_MES) / ingresos[h] if ingresos[h] > 0 else 0.0
        por_estrato.append(
            StratumMetrics(
                estrato=h + 1,
                n_hogares=n_h,
                dist_media_cbd_km=d_media,
                tiempo_medio_min=t_medio,
                reparto_modal=reparto,
                costo_medio_clp=c_medio,
                delta_excedente_clp=cs_medio,
                carga_costo_ingreso=carga,
            )
        )

    # --- Métricas del sistema ---
    modal_global_counts = modal.sum(axis=0)
    tot_global = int(total_ag.sum())
    reparto_global = {
        c: (float(modal_global_counts[k] / tot_global) if tot_global > 0 else 0.0)
        for c, k in cat_idx.items()
    }
    t_total = float(t_sum.sum())
    n_viajan_total = int(viajan.sum())
    t_medio_sis = t_total / n_viajan_total if n_viajan_total > 0 else 0.0

    bienestar_total = float(
        sum(por_estrato[h].delta_excedente_clp * por_estrato[h].n_hogares for h in range(n_strata))
    )

    t_alto = por_estrato[0].tiempo_medio_min
    t_bajo = por_estrato[-1].tiempo_medio_min
    ratio_t = (t_bajo / t_alto) if t_alto > 0 else None
    carga_alto = por_estrato[0].carga_costo_ingreso
    carga_bajo = por_estrato[-1].carga_costo_ingreso
    ratio_carga = (carga_bajo / carga_alto) if carga_alto > 0 else None

    residual_out = None if T_residual is None or not np.isfinite(T_residual) else float(T_residual)

    sistema = SystemMetrics(
        convergio_exterior=converged,
        iteraciones_exteriores=iterations_count,
        residual_final_min=residual_out,
        convergio_msa=trace.converged,
        tiempo_total_pax_min=t_total,
        tiempo_medio_min=t_medio_sis,
        reparto_modal=reparto_global,
        frecuencia_metro=float(snap.frecuencia_metro),
        emisiones_total_kg=float(trace.emisiones_total_kg),
        emisiones_auto_kg=float(trace.emisiones_auto_kg),
        emisiones_metro_kg=float(trace.emisiones_metro_kg),
        segregacion_theil=_theil(Q),
        delta_bienestar_total_clp=bienestar_total,
        medida_bienestar=medida,
        ratio_tiempo_bajo_alto=ratio_t,
        ratio_carga_bajo_alto=ratio_carga,
    )

    return EquilibriumMetrics(por_estrato=por_estrato, sistema=sistema)
