"""Esquemas Pydantic para el módulo de uso de suelo."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from titirilquen_core.land_use.supply import FormaOferta

"""El módulo tiene un **único solver**: `solve_logit` (β uniforme sobre la puja
`y + f/λ`). Con λ_h heterogéneo, mover λ re-escala las preferencias y el ruido
de ese estrato a la vez — limitación conocida (D-08), no un efecto de
comportamiento. No hay corrección implementada.

Existió un campo `solver` con un segundo método presentado como la corrección:
no lo era (dejaba λ inerte). Se eliminó junto con el campo. Un escenario
guardado que todavía lo traiga **no se migra**: falla al importar con un error
explícito, decisión tomada al romper la compatibilidad en agosto de 2026."""


class LandUseStratumConfig(BaseModel):
    """Parámetros de la función de puje (bid function) por estrato.

    **Unidades (D-26/D-27)**: `T` entra en minutos y la densidad en hogares/km,
    así que `alpha` está en utiles/min y `rho` en utiles/(hogar/km). `y` está en
    $/mes (CLP); no mueve la asignación (se absorbe en ū, ver D-08) pero sí
    la métrica de carga mensual costo/ingreso del acoplado."""

    model_config = ConfigDict(extra="forbid")

    y: float = Field(description="Ingreso mensual del estrato ($/mes)")
    lambda_: float = Field(
        default=1.0,
        gt=0,
        alias="lambda",
        description="Utilidad marginal del ingreso (λ_h)",
    )
    alpha: float = Field(default=6.0, description="Peso del tiempo de viaje (utiles/min)")
    rho: float = Field(default=0.1, description="Penalización de densidad (utiles por hogar/km)")


class LandUseConfig(BaseModel):
    """Configuración del módulo de uso de suelo."""

    model_config = ConfigDict(extra="forbid")

    H_por_estrato: tuple[int, int, int] = Field(
        default=(33300, 33300, 33300),
        description="Número de hogares por estrato (alto, medio, bajo)",
    )
    # Hubo aquí un par `densidad_max` / `densidad_min` que se conservaba "por
    # compatibilidad de serialización" y que el propio `description` declaraba
    # vestigial: la densidad por celda es una CONSECUENCIA de la oferta
    # (dens = S/Δx, ver `LandUseCity.densidad_por_celda`), no un parámetro. La
    # escala de población la fija `H_por_estrato`. Se retiraron al romper la
    # compatibilidad de escenarios en agosto de 2026.
    #
    # OJO: ese comentario quedó pegado al campo de abajo en el espejo TypeScript
    # y terminó rotulando `estratos` como «VESTIGIAL (no usado)», que es lo
    # contrario de la verdad: `alpha` y `rho` son las dos palancas del bid-rent.
    # El `description` de acá existe para que el JSDoc generado lo diga.
    #
    # Calibración en unidades físicas (D-26), equivalente a la antigua
    # (α=1.3/1.2/1.1 por celda, ρ=1 por hogar/celda) en la grilla de referencia
    # del frontend (201 celdas / 20 km): α' ≈ α·(celdas/km)/2 ≈ α·5, ρ' = ρ·Δx ≈ 0.1.
    # Ingresos en $/mes (D-27).
    estratos: tuple[LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig] = Field(
        default=(
            LandUseStratumConfig(y=3_500_000.0, alpha=6.5, rho=0.1),
            LandUseStratumConfig(y=1_500_000.0, alpha=6.0, rho=0.1),
            LandUseStratumConfig(y=500_000.0, alpha=5.5, rho=0.1),
        ),
        description=(
            "Parámetros de puja de los tres estratos (alto, medio, bajo). Son la "
            "palanca principal del módulo: la diferencia de `alpha` entre estratos "
            "es lo que produce el gradiente de localización de Alonso."
        ),
    )
    beta: float = Field(default=1.0, gt=0, description="Parámetro de sensibilidad logit")
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
