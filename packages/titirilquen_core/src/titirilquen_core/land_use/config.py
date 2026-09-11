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

    **Unidades (D-26/D-27/D-34)**: `T` es el logsum mensual de transporte
    (utiles de transporte por mes) y la densidad va en hogares/km; `alpha` es
    adimensional (1 = la accesibilidad tal cual), `rho` en utiles-mes por
    (hogar/km) y `lambda` en utiles por peso (= |b_costo| de transporte), con
    lo que el score queda en $/mes. `y` está en $/mes (CLP); no mueve la
    asignación (se absorbe en ū, ver D-08) pero sí la métrica de carga mensual
    costo/ingreso del acoplado."""

    model_config = ConfigDict(extra="forbid")

    y: float = Field(gt=0, description="Ingreso mensual del estrato ($/mes)")
    lambda_: float = Field(
        default=1.0,
        gt=0,
        alias="lambda",
        description="Utilidad marginal del ingreso (λ_h)",
    )
    alpha: float = Field(
        default=1.0,
        description=(
            "Multiplicador de la accesibilidad (logsum mensual de transporte); 1 = tal cual"
        ),
    )
    rho: float = Field(
        default=5.2e-3,
        description="Penalización de densidad (utiles de transporte por mes, por hogar/km)",
    )


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
    # `lambda` HETEROGÉNEA (2026-09-02). Antes los tres valían 1,0, y eso no era
    # una decisión: era la única opción disponible. La forma cerrada de la
    # ec. (4.26) aplica un `beta` escalar sobre las pujas, así que con ella
    # `lambda_h` sólo entra dividiendo el determinístico y es idénticamente
    # re-escalar `(alpha_h, rho_h)` por `1/lambda_h` — D-08. Con HEV el ruido
    # escala por estrato a `1/(beta·lambda_h)`, que la re-escala de preferencias
    # no toca, y `lambda` queda IDENTIFICADO (`test_hev.py`).
    #
    # De dónde salen estos números (D-34, sep-2026). Un hogar tiene UNA función
    # de utilidad: el que puja por suelo es el que elige modo. Así que:
    #
    #   * `T_h(i)` = −VIAJES_MES·logsum_h(i): la utilidad esperada del viaje desde
    #     la parcela, en utiles de transporte, mensualizada (`accesibilidad.py`).
    #   * `alpha = 1`, común: la puja lee esa accesibilidad tal cual. Es el ancla
    #     que traía el original (`actualizar(T, alpha=[1,1,1])` sobre el logsum)
    #     y nunca se ejecutó. Un alpha ≠ 1 es un multiplicador sin fuente.
    #   * `lambda_h = |b_costo_h|` de `presets.DEFAULT_STRATA`, literal, en
    #     utiles de transporte por peso: 0,000320 / 0,000641 / 0,001241. Con eso
    #     el score `y + f/lambda` queda en $/mes, como `p` e `y` (D-27), el VoT
    #     `alpha/lambda` = 6.200 / 3.100 / 1.600 $/h coincide con transporte, y
    #     el ruido de la puja `1/(beta·lambda_h)` = $3.122 / $1.561 / $806 al mes.
    #   * `beta = 1`: el mismo ruido Gumbel que un viaje. Es la ÚNICA perilla
    #     propia del módulo y tiene lectura directa (beta = 0,1 ⇒ elegir casa es
    #     10 veces más ruidoso que elegir modo). Con 1 la ciudad sale nítida
    #     (Theil ≈ 0,75): un mes de viajes es mucho dinero frente al ruido de
    #     un viaje. Bajarlo es decisión pedagógica (AU-10), no calibración.
    #   * `rho`: SIN FUENTE, ni acá ni en el original (donde valía 1 sobre la
    #     capacidad cruda). Se fija para que `rho·dens` recorra el 50 % del rango
    #     de `alpha·T` del estrato medio en la ciudad por defecto (decisión
    #     2026-09-04): 0,5·87,4/8.410 = 5,2e-3 utiles-mes por (hog/km). Medido:
    #     Theil 0,75, gradiente de renta +0,75. La asignación se invierte al
    #     200 % (≈1,0e-2): la UI no debe dejar pasar de ahí.
    #
    # Todo lo anterior está vigilado por `tests/test_vot_consistente.py` y
    # `tests/test_accesibilidad.py`. Historia: hasta sep-2026 alpha era 6,5/6,0/
    # 5,5 (el 1,3/1,2/1,1 del original ×5 por D-26), lambda = 1 por la forma
    # cerrada (D-08) y T minutos a flujo libre.
    estratos: tuple[LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig] = Field(
        default=(
            LandUseStratumConfig(y=3_500_000.0, alpha=1.0, rho=5.2e-3, **{"lambda": 0.000320323}),
            LandUseStratumConfig(y=1_500_000.0, alpha=1.0, rho=5.2e-3, **{"lambda": 0.00064065}),
            LandUseStratumConfig(y=500_000.0, alpha=1.0, rho=5.2e-3, **{"lambda": 0.00124125}),
        ),
        description=(
            "Parámetros de puja de los tres estratos (alto, medio, bajo). Son la "
            "palanca principal del módulo: `alpha` es común y la diferencia de "
            "`lambda` entre estratos fija el valor del tiempo `alpha/lambda` de "
            "cada uno, que es lo que produce el gradiente de Alonso."
        ),
    )

    # `beta` = 0,15 ≈ 1/√44 (decisión 2026-09-04). La escala del ruido Gumbel de la
    # puja es 1/(beta·lambda_h). Con beta = 1 el ruido es el de UN viaje mientras
    # la señal (T) está mensualizada ×44: eso supone que el gusto idiosincrático
    # por una casa es un solo sorteo, y da una ciudad casi determinista (Theil
    # 0,75, señal/ruido ~90:1). Si en cambio el ruido también se acumula viaje a
    # viaje (iid), su escala mensual crece como √44 ≈ 6,6 y la razón señal/ruido
    # honesta es 6,6 veces menor: beta = 1/√44. Es una APROXIMACIÓN DE SEGUNDO
    # MOMENTO, no una derivación: la suma de 44 Gumbel no es Gumbel, y los shocks
    # de vivienda no son 44 shocks de viaje iid (D-41). Ninguna de las dos
    # hipótesis se estima con estos datos; ésta es la que no infla la nitidez. Medido:
    # Theil ≈ 0,16, alto/medio/bajo ≈ 2,1 / 3,1 / 5,5 km, gradiente de renta
    # +0,78, ~30 iteraciones (vs 140 con beta = 1). Es la ÚNICA perilla propia
    # del módulo: alpha y lambda vienen de transporte (D-34).
    @field_validator("H_por_estrato")
    @classmethod
    def _hogares_no_negativos(cls, v: tuple[int, int, int]) -> tuple[int, int, int]:
        # D-43: el schema aceptaba shares negativos, que aguas abajo dan
        # probabilidades inválidas sin ningún error explícito.
        if any(h < 0 for h in v):
            raise ValueError(f"H_por_estrato no admite negativos: {v}")
        if sum(v) <= 0:
            raise ValueError("H_por_estrato: la ciudad necesita al menos un hogar")
        return v

    beta: float = Field(
        default=0.15,
        gt=0,
        description=(
            "Nitidez de la subasta: escala del ruido de la puja = 1/(beta·lambda). "
            "1 = el ruido de un viaje; 0,15 ≈ 1/√44 = ruido acumulado en el mes"
        ),
    )
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
