"""Esquemas Pydantic para el módulo de uso de suelo."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from titirilquen_core.land_use.supply import FormaOferta

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
    forma: FormaOferta = Field(
        default="normal",
        description=(
            "Forma del perfil de oferta de vivienda a lo largo del corredor: "
            "normal · uniforme · exponencial · anular · bimodal."
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
            "exponencial y el ancho del anillo/picos. Default 0.5 = σ ≈ L/4."
        ),
    )
    forma_param: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description=(
            "2º parámetro de la forma, como fracción de la semi-ciudad: radio del "
            "anillo (anular) o separación de los picos (bimodal). Ignorado en "
            "normal/uniforme/exponencial."
        ),
    )

    @field_validator("H_por_estrato")
    @classmethod
    def _check_positive(cls, v: tuple[int, int, int]) -> tuple[int, int, int]:
        if any(h <= 0 for h in v):
            raise ValueError("Todos los estratos deben tener al menos un hogar")
        return v
