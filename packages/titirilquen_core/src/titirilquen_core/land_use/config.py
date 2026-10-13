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

    La atractividad es `f_h(i) = −T_h(i) − ρ_h·d_i` (schema v7, oct-2026).

    **Unidades (D-26/D-27/D-34)**: `T` es el logsum mensual de transporte
    (utiles de transporte por mes) y `d_i` la densidad RELATIVA de la parcela
    —su densidad sobre la media de la ciudad, adimensional—, así que `rho` va en
    utiles-mes: lo que el hogar resta a su puja, en accesibilidad mensual, por
    cada «densidad media» que tenga su celda. λ_h, la utilidad marginal del
    ingreso que pasa el score a $/mes, NO es un campo: es |b_costo_h| de la
    demanda (`accesibilidad.lambda_desde_demanda`, schema v6). `y` está en
    $/mes (CLP); no mueve la asignación (se absorbe en ū, ver D-08) pero sí la
    métrica de carga mensual costo/ingreso del acoplado.

    **No hay `alpha` (desde v7, D1 de la auditoría).** El peso de la
    accesibilidad es 1: la puja lee la utilidad de transporte del mismo hogar,
    que ya está en su escala. Un multiplicador por estrato no tenía fuente, y
    uno común era indistinguible de mover μ (sólo μ·α y μ·ρ están
    identificados: escalar pujas y escala del ruido por el mismo k no cambia
    ninguna probabilidad). La sensibilidad relativa a la densidad es ρ."""

    model_config = ConfigDict(extra="forbid")

    y: float = Field(gt=0, description="Ingreso mensual del estrato ($/mes)")
    rho: float = Field(
        default=0.0,
        ge=0,
        description=(
            "Penalización de densidad, en utiles de transporte por mes por unidad de "
            "densidad RELATIVA (densidad de la celda / densidad media de la ciudad). "
            "0 = Alonso puro: sólo manda la accesibilidad. Entra en pesos como rho/lambda_h"
        ),
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
    # contrario de la verdad: `rho` es la palanca del bid-rent (`alpha`, la otra,
    # se retiró en v7).
    # El `description` de acá existe para que el JSDoc generado lo diga.
    #
    # Calibración en unidades físicas (D-26). Ingresos en $/mes (D-27).
    #
    # `rho` = 0 por defecto: el modelo es Alonso puro, la localización la decide
    # sólo la accesibilidad y la segregación sale de que el tiempo vale distinto
    # por estrato. La penalización por densidad no tiene fuente (Martínez deja
    # f_h como función general de atributos) y actúa sobre una densidad exógena
    # (la oferta S), así que no es congestión residencial: es una desamenidad
    # fija de la parcela. Se conserva como dial pedagógico: como entra dividido
    # por lambda_h, un rho común ya hace que el estrato alto pague más pesos por
    # baja densidad; al subirlo, la ciudad se mezcla, el gradiente de renta se
    # aplana y, pasado un umbral, la asignación se invierte (el alto vive más
    # lejos que el bajo), que es el patrón «ricos en la periferia».
    #
    # Desde v7 (D2 de la auditoría) la densidad es RELATIVA a la media de la
    # ciudad. Con la absoluta (hogares/km), el mismo rho pesaba más en una ciudad
    # más poblada: cambiar `H_por_estrato` movía la localización aunque nadie
    # tocara las preferencias. Equivalencia con v6: rho_v7 = rho_v6 × densidad
    # media (hogares/km).
    #
    # `lambda` HETEROGÉNEA (2026-09-02). Antes los tres valían 1,0, y eso no era
    # una decisión: era la única opción disponible. La forma cerrada de la
    # ec. (4.26) aplica un `β` escalar sobre las pujas, así que con ella
    # `lambda_h` sólo entra dividiendo el determinístico y es idénticamente
    # re-escalar la atractividad `f_h` (peso de T y `rho_h`) por `1/lambda_h`
    # — D-08. Con HEV el ruido escala por estrato a `1/β_h = 1/(mu·lambda_h)`,
    # que la re-escala de preferencias no toca, y `lambda` queda IDENTIFICADO
    # (`test_hev.py`).
    #
    # De dónde salen estos números (D-34, sep-2026). Un hogar tiene UNA función
    # de utilidad: el que puja por suelo es el que elige modo. Así que:
    #
    #   * `T_h(i)` = −VIAJES_MES·logsum_h(i): la utilidad esperada del viaje desde
    #     la parcela, en utiles de transporte, mensualizada (`accesibilidad.py`).
    #   * peso 1 sobre T: la puja lee esa accesibilidad tal cual. Es el ancla
    #     que traía el original (`actualizar(T, alpha=[1,1,1])` sobre el logsum)
    #     y nunca se ejecutó. Hasta v6 era el campo `alpha`; se retiró en v7
    #     porque un alpha ≠ 1 es un multiplicador sin fuente.
    #   * `lambda_h = |b_costo_h|`, en utiles de transporte por peso: con los
    #     presets, 0,000314 / 0,000628 / 0,001216 (D5). Con eso el score
    #     `y + f/lambda` queda en $/mes, como `p` e `y` (D-27), el VoT
    #     `b_tiempo_viaje·60/b_costo` = 6.329 / 3.164 / 1.633 $/h coincide con
    #     transporte, y el ruido de la puja `1/(mu·lambda_h)` = $21.139 /
    #     $10.568 / $5.454 al mes (con mu = 1/√44; `1/lambda_h` = $3.187 /
    #     $1.593 / $822). Desde el schema
    #     v6 NO se guarda acá: lo deriva `accesibilidad.lambda_desde_demanda`, y
    #     calibrar `b_costo` mueve λ y T a la vez. Hasta v5 era una copia literal
    #     que nada sincronizaba.
    #   * `mu` = 1/√VIAJES_MES: la constante `constantes.MU_SUELO` desde v7,
    #     con su justificación ahí. Hasta v6 era un campo de esta configuración.
    #   * `rho`: sin fuente; 0 por defecto (ver el comentario del campo).
    #
    # Todo lo anterior está vigilado por `tests/test_vot_consistente.py` y
    # `tests/test_accesibilidad.py`. Historia: hasta sep-2026 alpha era 6,5/6,0/
    # 5,5 (el 1,3/1,2/1,1 del original ×5 por D-26), lambda = 1 por la forma
    # cerrada (D-08) y T minutos a flujo libre.
    estratos: tuple[LandUseStratumConfig, LandUseStratumConfig, LandUseStratumConfig] = Field(
        default=(
            LandUseStratumConfig(y=3_500_000.0, rho=0.0),
            LandUseStratumConfig(y=1_500_000.0, rho=0.0),
            LandUseStratumConfig(y=500_000.0, rho=0.0),
        ),
        description=(
            "Parámetros de puja de los tres estratos (alto, medio, bajo). La "
            "accesibilidad entra con peso 1; la diferencia de λ_h = |b_costo_h| "
            "entre estratos (de la demanda) fija el valor del tiempo `1/λ` de cada "
            "uno, que es lo que produce el gradiente de Alonso."
        ),
    )

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

    # Hasta v6 había aquí un campo `mu`, la precisión del ruido de localizarse.
    # Ahora es `constantes.MU_SUELO` (1/√VIAJES_MES) y no se configura; ver la
    # justificación ahí. Un escenario v6 que lo traiga falla al importar.
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
