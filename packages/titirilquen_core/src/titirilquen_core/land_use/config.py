"""Esquemas Pydantic para el módulo de uso de suelo."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SolverKind = Literal["logit", "frechet"]
"""
- `logit`: resolver_equilibrio_logit — el método principal (ver Suelo.tex sec. 5.4)
- `frechet`: resolver_equilibrio_frechet — alternativa didáctica; el código
  original la marca "MALA" al enfrentar `λ_h` heterogéneos.
"""


class LandUseStratumConfig(BaseModel):
    """Parámetros de la función de puje (bid function) por estrato."""

    model_config = ConfigDict(extra="forbid")

    y: float = Field(description="Ingreso del estrato (unidades consistentes con p_i)")
    lambda_: float = Field(
        default=1.0, gt=0, alias="lambda",
        description="Utilidad marginal del ingreso (λ_h)",
    )
    alpha: float = Field(default=1.0, description="Peso de costo de transporte (α_h)")
    rho: float = Field(default=1.0, description="Peso de penalización de densidad (ρ_h)")


class LandUseConfig(BaseModel):
    """Configuración del módulo de uso de suelo."""

    model_config = ConfigDict(extra="forbid")

    H_por_estrato: tuple[int, int, int] = Field(
        default=(33300, 33300, 33300),
        description="Número de hogares por estrato (alto, medio, bajo)",
    )
    estratos: tuple[LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig] = Field(
        default=(
            LandUseStratumConfig(y=120.0, alpha=1.3, rho=1.0),
            LandUseStratumConfig(y=50.0, alpha=1.2, rho=1.0),
            LandUseStratumConfig(y=10.0, alpha=1.1, rho=1.0),
        )
    )
    beta: float = Field(default=1.0, gt=0, description="Parámetro de sensibilidad logit")
    solver: SolverKind = "logit"
    tol: float = Field(default=1e-8, gt=0)
    max_iter: int = Field(default=10000, ge=1)

    @field_validator("H_por_estrato")
    @classmethod
    def _check_positive(cls, v: tuple[int, int, int]) -> tuple[int, int, int]:
        if any(h <= 0 for h in v):
            raise ValueError("Todos los estratos deben tener al menos un hogar")
        return v
