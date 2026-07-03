"""Esquemas Pydantic para el módulo de uso de suelo."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from titirilquen_core.land_use.supply import FormaOferta

SolverKind = Literal["heteroscedastic", "logit"]
"""
- `heteroscedastic`: logit heteroscedástico (escala por estrato β_h = β·λ_h) — el
  método **consistente**, que corrige el problema del λ heterogéneo (ver D-08).
  Default. Coincide con `logit` cuando λ_h = 1 ∀h.
- `logit`: β uniforme sobre la puja `y + f/λ` — inconsistente con λ_h heterogéneo
  (Suelo.tex sec. 5.4). Se conserva para comparación didáctica.
"""


class LandUseStratumConfig(BaseModel):
    """Parámetros de la función de puje (bid function) por estrato.

    **Unidades (D-26/D-27)**: `T` entra en minutos y la densidad en hogares/km,
    así que `alpha` está en utiles/min y `rho` en utiles/(hogar/km). `y` está en
    $/mes (CLP); no mueve la asignación (se absorbe en ū, ver D-08 §C8) pero sí
    la métrica de carga mensual costo/ingreso del acoplado."""

    model_config = ConfigDict(extra="forbid")

    y: float = Field(description="Ingreso mensual del estrato ($/mes)")
    lambda_: float = Field(
        default=1.0, gt=0, alias="lambda",
        description="Utilidad marginal del ingreso (λ_h)",
    )
    alpha: float = Field(default=6.0, description="Peso del tiempo de viaje (utiles/min)")
    rho: float = Field(
        default=0.1, description="Penalización de densidad (utiles por hogar/km)"
    )


class LandUseConfig(BaseModel):
    """Configuración del módulo de uso de suelo."""

    model_config = ConfigDict(extra="forbid")

    H_por_estrato: tuple[int, int, int] = Field(
        default=(33300, 33300, 33300),
        description="Número de hogares por estrato (alto, medio, bajo)",
    )
    densidad_max: float = Field(
        default=800.0,
        gt=0,
        description=(
            "Densidad residencial (hab/km) en el CBD. La densidad es un gradiente "
            "de Clark GEOMÉTRICO en la distancia al CBD, independiente del precio y "
            "de ρ: dens(d) = densidad_max·(densidad_min/densidad_max)^(d/d_max)."
        ),
    )
    densidad_min: float = Field(
        default=200.0,
        gt=0,
        description=(
            "Densidad residencial (hab/km) en la periferia (piso del gradiente de "
            "Clark). Interpola geométricamente entre densidad_max en el CBD y "
            "densidad_min en el borde según la distancia. Independiente del estrato."
        ),
    )
    # Calibración en unidades físicas (D-26), equivalente a la antigua
    # (α=1.3/1.2/1.1 por celda, ρ=1 por hogar/celda) en la grilla de referencia
    # del frontend (201 celdas / 20 km): α' ≈ α·(celdas/km)/2 ≈ α·5, ρ' = ρ·Δx ≈ 0.1.
    # Ingresos en $/mes (D-27).
    estratos: tuple[LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig] = Field(
        default=(
            LandUseStratumConfig(y=3_500_000.0, alpha=6.5, rho=0.1),
            LandUseStratumConfig(y=1_500_000.0, alpha=6.0, rho=0.1),
            LandUseStratumConfig(y=500_000.0, alpha=5.5, rho=0.1),
        )
    )
    beta: float = Field(default=1.0, gt=0, description="Parámetro de sensibilidad logit")
    solver: SolverKind = "heteroscedastic"
    tol: float = Field(default=1e-8, gt=0)
    max_iter: int = Field(default=10000, ge=1)
    forma: FormaOferta = Field(
        default="normal",
        description=(
            "Forma del perfil de oferta de vivienda a lo largo del corredor: "
            "normal · uniforme · exponencial · meseta · bimodal · valle."
        ),
    )
    oferta_sigma_frac: float = Field(
        default=0.5,
        gt=0,
        le=1.5,
        description=(
            "Ancho/dispersión de la oferta como fracción de la semi-ciudad: "
            "σ = frac · min(CBD, L-1-CBD). Menor ⇒ ciudad compacta (vivienda junto "
            "al CBD); mayor ⇒ dispersa. También controla la pendiente de la "
            "exponencial y el ancho de los picos (bimodal). Default 0.5 = σ ≈ L/4."
        ),
    )
    forma_param: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description=(
            "2º parámetro de la forma, como fracción de la semi-ciudad: separación "
            "de los picos (bimodal). Ignorado en las demás formas."
        ),
    )

    @field_validator("H_por_estrato")
    @classmethod
    def _check_positive(cls, v: tuple[int, int, int]) -> tuple[int, int, int]:
        if any(h <= 0 for h in v):
            raise ValueError("Todos los estratos deben tener al menos un hogar")
        return v
