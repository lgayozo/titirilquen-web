"""Esquemas Pydantic — fuente única de configuración para el simulador.

Reemplaza el dict `CONFIG_DEMANDA` duplicado entre `app.py` y `Ciudad2.py` del
repositorio original. Todos los valores por defecto coinciden con los del
código original para preservar compatibilidad.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StratumId = Literal[1, 2, 3]
"""1 = Alto, 2 = Medio, 3 = Bajo."""


class PhysicalPenalties(BaseModel):
    """Penalizaciones aditivas escalonadas (step) para bici y caminata.

    Ver docs/DISCREPANCIES.md (D-02) — estas son constantes aditivas, no
    multiplicativas como sugiere el Overleaf.
    """

    model_config = ConfigDict(extra="forbid")

    bici_10: float
    bici_20: float
    bici_30: float
    walk_5: float
    walk_15: float
    walk_25: float


class StratumBetas(BaseModel):
    """Coeficientes del logit multinomial por estrato."""

    model_config = ConfigDict(extra="forbid")

    asc_auto: float
    asc_metro: float
    asc_bici: float
    asc_caminata: float
    b_tiempo_viaje: float
    b_costo: float
    b_tiempo_espera: float
    b_tiempo_caminata: float
    penalizaciones_fisicas: PhysicalPenalties


class JornadaHoras(BaseModel):
    model_config = ConfigDict(extra="forbid")

    horas_rigido: float = 9.0
    horas_flexible: float = 8.0
    horas_part_time: float = 4.0


class StratumConfig(BaseModel):
    """Configuración por estrato. Inactiva por defecto: jornada/part_time sólo afectan
    metadatos de agentes, no la utilidad (ver D-07)."""

    model_config = ConfigDict(extra="forbid")

    prob_teletrabajo: float = Field(ge=0, le=1)
    prob_auto: float = Field(ge=0, le=1)
    prob_jornada_flexible: float = Field(default=0.3, ge=0, le=1)
    prob_part_time: float = Field(default=0.1, ge=0, le=1)
    jornada: JornadaHoras = Field(default_factory=JornadaHoras)
    betas: StratumBetas


class GlobalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_auto: float = 31
    v_metro: float = 35
    v_bici: float = 14
    v_caminata: float = 4.8
    costo_combustible_km: float = 120
    costo_tarifa_metro: float = 800
    costo_parking: float = 6000
    factor_emision_auto: float = 0.180
    factor_emision_metro: float = 0.040


class DemandConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    globales: GlobalConfig = Field(default_factory=GlobalConfig)
    estratos: dict[StratumId, StratumConfig]

    @field_validator("estratos", mode="before")
    @classmethod
    def _coerce_keys(cls, v: object) -> object:
        """JSON dict keys llegan como str; convertir a int para casar con `StratumId`."""
        if isinstance(v, dict):
            return {int(k) if isinstance(k, str) else k: val for k, val in v.items()}
        return v

    @field_validator("estratos")
    @classmethod
    def _check_strata_complete(cls, v: dict[StratumId, StratumConfig]) -> dict[StratumId, StratumConfig]:
        missing = {1, 2, 3} - set(v.keys())
        if missing:
            raise ValueError(f"Faltan estratos: {sorted(missing)}")
        return v


class CityConfig(BaseModel):
    """Ciudad lineal. `n_celdas` debe ser impar para que el CBD quede centrado."""

    model_config = ConfigDict(extra="forbid")

    n_celdas: int = Field(default=1001, ge=11)
    largo_ciudad_km: float = Field(default=20.0, gt=0)
    densidad_por_celda: int = Field(default=100, ge=1)
    pendiente_porcentaje: float = Field(default=0.0)
    teletrabajo_factor: float = Field(default=1.0, ge=0.0, le=5.0)
    share_estratos: tuple[float, float, float] = Field(default=(0.10, 0.40, 0.50))
    ingresos_estratos: tuple[float, float, float] = Field(default=(120.0, 50.0, 10.0))

    @field_validator("share_estratos")
    @classmethod
    def _shares_sum_to_one(cls, v: tuple[float, float, float]) -> tuple[float, float, float]:
        if abs(sum(v) - 1.0) > 1e-6:
            raise ValueError(f"Los shares de estratos deben sumar 1, obtuve {sum(v)}")
        return v


class BikeSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_media_kmh: float = 14
    capacidad_pista: int = 800
    alpha_bpr: float = 0.5
    beta_bpr: float = 2.0


class CarSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_max_kmh: float = 31
    ancho_pista_m: float = 3.5
    largo_vehiculo_m: float = 5.0
    gap_m: float = 2.0
    num_pistas: int = Field(default=2, ge=1)
    alpha_bpr: float = 0.8
    beta_bpr: float = 2.0


class TrainSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_tren_kmh: float = 35
    capacidad_tren: int = 1200
    num_estaciones: int = Field(default=10, ge=2)
    v_caminata_kmh: float = 4.8
    tasa_carga: float = 6.0
    frec_min: float = 10
    frec_max: float = 20


class SupplyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bike: BikeSupplyParams = Field(default_factory=BikeSupplyParams)
    car: CarSupplyParams = Field(default_factory=CarSupplyParams)
    train: TrainSupplyParams = Field(default_factory=TrainSupplyParams)


class SimulationConfig(BaseModel):
    """Configuración completa de una corrida del simulador — el objeto que se
    serializa al archivo `.ttrq.json`."""

    model_config = ConfigDict(extra="forbid")

    city: CityConfig = Field(default_factory=CityConfig)
    supply: SupplyConfig = Field(default_factory=SupplyConfig)
    demand: DemandConfig
    max_iter: int = Field(default=12, ge=1, le=100)
    tolerance: float = Field(default=0.0, ge=0)
    seed: int | None = None
