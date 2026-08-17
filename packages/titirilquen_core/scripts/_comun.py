"""Piezas compartidas por los scripts de auditoría.

Los once scripts de `scripts/` hacían todos lo mismo para empezar: armar la
configuración que corre la aplicación, drenar el MSA, y resumir el reparto
modal. Ese bloque estaba reescrito ocho veces, con la expresión del v/c
copiada textual en cinco, y cada copia con sus propias claves de salida.

Peor que la repetición: sólo UNO de los cinco dialectos de "modificar un
parámetro" llevaba el guard de validación (`valida`), así que los otros cuatro
seguían expuestos al fallo que ese guard existe para atrapar.

Este módulo es la base. Los scripts que necesiten otra cosa siguen pudiendo
armarla, pero lo común se declara una vez.

Se importan como módulo hermano (`from _comun import ...`) porque `scripts/`
no es un paquete instalable; corren con `uv run python scripts/<x>.py` desde
`packages/titirilquen_core`, y Python pone el directorio del script en el path.
"""

from __future__ import annotations

from typing import Any

from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import DEFAULT_STRATA

#: Población de la ciudad por defecto de la app: 1.800 hab/km × 20 km.
SUMA_H = 36_000

#: Mezcla socioeconómica 20/50/30 (alto/medio/bajo).
#:
#: Antes vivía como `10/40/50` en un script y nadie lo notó: las auditorías
#: midieron esa ciudad durante semanas y reportaron líneas base que no eran las
#: de la aplicación. Es el motivo por el que esto se declara una sola vez.
H_POR_ESTRATO = (int(SUMA_H * 0.20), int(SUMA_H * 0.50), int(SUMA_H * 0.30))

MODOS_CON_TELE = ("Auto", "Metro", "Bici", "Caminata", "Teletrabajo")


def demanda_ui() -> DemandConfig:
    """La calibración vigente — la misma que corre en el navegador."""
    return DemandConfig.model_validate({"estratos": DEFAULT_STRATA})


def base_sim() -> SimulationConfig:
    """La configuración que ve el usuario al abrir el módulo de transporte."""
    return SimulationConfig(
        city=CityConfig(n_celdas=201, largo_ciudad_km=20, densidad_hab_km=1800),
        supply=SupplyConfig(),
        demand=demanda_ui(),
        max_iter=20,
        tolerance=0.1,
        seed=42,
        assignment="expected",
    )


def base_lu() -> LandUseConfig:
    return LandUseConfig(H_por_estrato=H_POR_ESTRATO, forma="normal", oferta_sigma_frac=0.5)


def corre_trace(
    sim: SimulationConfig,
    lu: LandUseConfig | None = None,
    localizacion: str = "equilibrio",
) -> ConvergenceTrace:
    """Drena el MSA y devuelve el trace completo."""
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu or base_lu(), tr, localizacion=localizacion):
        pass
    return tr


def resumen(tr: ConvergenceTrace) -> dict[str, Any]:
    """Reparto modal (%) y diagnóstico del equilibrio."""
    last = tr.iteraciones[-1]
    total = sum(last.modal_split.values()) or 1
    return {
        **{m: 100 * last.modal_split.get(m, 0) / total for m in MODOS_CON_TELE},
        "vc": vc_auto(tr),
        "t_auto": float(last.t_auto.max()),
        "t_bici": float(last.t_bici.max()),
        "f_op": last.frecuencia_metro,
        "co2": tr.emisiones_total_kg,
        "iters": len(tr.iteraciones),
        "conv": tr.converged,
    }


def corre(sim: SimulationConfig, lu: LandUseConfig | None = None) -> dict[str, Any]:
    """Corre y resume en un paso — lo que hace casi todo barrido."""
    return resumen(corre_trace(sim, lu))


def vc_auto(tr: ConvergenceTrace) -> float:
    """Saturación del corredor.

    El numerador es el flujo ACUMULADO hacia el CBD, no la demanda originada
    por celda: ésa lo subestima unas 60 veces y hacía leer un corredor saturado
    como si estuviera al 2 %.
    """
    if tr.flujos_auto_veh_h is None or not tr.capacidad_auto:
        return 0.0
    return float(tr.flujos_auto_veh_h.max()) / tr.capacidad_auto


def valida(modelo: Any, kw: dict) -> dict:
    """Rechaza claves que no existen en el modelo.

    `model_copy(update=...)` de Pydantic **no valida**: una clave inexistente se
    cuela como atributo suelto, el parámetro que se creía estar moviendo no se
    mueve, y el barrido lo reporta como «inerte». Pasó dos veces —el `solver`
    del suelo y `factor_emision_auto` tras renombrarlo a `factor_flota_auto`—,
    en ambos casos con la conclusión equivocada ya escrita en un documento.
    """
    desconocidas = set(kw) - set(type(modelo).model_fields)
    if desconocidas:
        raise ValueError(f"no son campos de {type(modelo).__name__}: {sorted(desconocidas)}")
    return kw


def con_car(sim: SimulationConfig | None = None, **kw: Any) -> SimulationConfig:
    """Copia de la config con parámetros de oferta vial cambiados."""
    s = sim or base_sim()
    s.supply.car = s.supply.car.model_copy(update=valida(s.supply.car, kw))
    return s


def con_bike(sim: SimulationConfig | None = None, **kw: Any) -> SimulationConfig:
    s = sim or base_sim()
    s.supply.bike = s.supply.bike.model_copy(update=valida(s.supply.bike, kw))
    return s


def con_train(sim: SimulationConfig | None = None, **kw: Any) -> SimulationConfig:
    s = sim or base_sim()
    s.supply.train = s.supply.train.model_copy(update=valida(s.supply.train, kw))
    return s


def con_globales(sim: SimulationConfig | None = None, **kw: Any) -> SimulationConfig:
    s = sim or base_sim()
    g = s.demand.globales
    s.demand.globales = g.model_copy(update=valida(g, kw))
    return s


def con_city(sim: SimulationConfig | None = None, **kw: Any) -> SimulationConfig:
    s = sim or base_sim()
    s.city = s.city.model_copy(update=valida(s.city, kw))
    return s


def minutos_equivalentes(utiles: float, b_tiempo_viaje: float) -> float:
    """Útiles → minutos de viaje en vehículo.

    Es la única unidad que permite comparar coeficientes ENTRE estratos: la
    escala de la utilidad se cancela en el cociente. `b_tiempo_viaje` es
    negativo, así que un costo (utilidad negativa) sale positivo.
    """
    return utiles / b_tiempo_viaje if b_tiempo_viaje else float("nan")
