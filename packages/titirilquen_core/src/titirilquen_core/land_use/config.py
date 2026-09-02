"""Esquemas Pydantic para el módulo de uso de suelo."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from titirilquen_core.land_use.supply import FormaOferta

"""El modelo de subasta lo elige `solve_subasta` **según los datos**, no un campo
de configuración: con `λ_h` uniformes usa la forma cerrada de la ec. (4.26) de
Martínez, que ahí es exacta, y con `λ_h` heterogéneos usa HEV (`hev.py`), que es
el modelo correcto cuando la varianza de las pujas difiere entre estratos.

Existió un campo `solver` que ofrecía elegir, y uno de los métodos que ofrecía
decía corregir el artefacto de λ sin hacerlo (dejaba λ inerte). Se eliminó junto
con el campo, y no se repuso al implementar HEV justamente para que no se pueda
elegir el modelo inválido para la configuración dada. Un escenario guardado que
todavía traiga `solver` **no se migra**: falla al importar con un error
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
    rho: float = Field(default=0.0025, description="Penalización de densidad (utiles por hogar/km)")


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
    # Calibración en unidades físicas (D-26). Ingresos en $/mes (D-27).
    #
    # ρ = 0,0025 y no 0,1 (2026-08-24). El valor anterior venía de convertir
    # ρ=1 por hogar/celda sobre la grilla de 201 celdas, y esa conversión era
    # fiel pero partía de un punto ya roto: la ciudad del `Suelo.tex` original
    # tiene 1001 celdas, y el balance entre los dos términos de la amenidad
    #
    #     razón ≈ α·(L/2)²·1,253 / (ρ·N)
    #
    # va con el CUADRADO del número de celdas. Pasar de 1001 a 201 lo dividió
    # por 25 sin que nadie rebalanceara ρ, así que `ρ·dens` terminó dominando a
    # `α·T` en el 80% de la ciudad y el suelo más caro quedó en la PERIFERIA:
    # el modelo de Alonso al revés. Medido: gradiente de renta −0,73 con ρ=0,1
    # y +0,81 con ρ=0,0025, que es el valor que reproduce la razón ≈ 6 del
    # documento original. Ver `test_el_suelo_central_vale_mas_que_el_periferico`.
    #
    # Con los `λ` uniformes —el default— cambiar ρ NO reasigna a nadie: es común
    # a los tres estratos y se absorbe en ū (AU-05), así que las distancias
    # medias por estrato quedan idénticas y sólo cambia el perfil de precios.
    # OJO: eso vale SÓLO con λ uniforme. Lo que entra en la puja es `ρ_h/λ_h`,
    # así que en cuanto los λ difieren una ρ común deja de ser un término común
    # y sí reasigna: con λ = (0,5 · 1 · 2) y ρ = 0,05 la ciudad se invierte
    # entera (alto a 5,67 km, bajo a 2,47). AU-05, corregido el 2026-09-02.
    estratos: tuple[LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig] = Field(
        default=(
            LandUseStratumConfig(y=3_500_000.0, alpha=6.5, rho=0.0025),
            LandUseStratumConfig(y=1_500_000.0, alpha=6.0, rho=0.0025),
            LandUseStratumConfig(y=500_000.0, alpha=5.5, rho=0.0025),
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
