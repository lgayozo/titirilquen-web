"""El valor del tiempo es UNO SOLO: transporte y uso de suelo no pueden discrepar.

El mismo hogar aparece en dos módulos y en los dos cambia tiempo por dinero:

- **Transporte** — el logit modal pondera `b_tiempo_viaje` y `b_costo`, y su
  cociente es el valor del tiempo conductual (`bienestar.vot_clp_hora`).
- **Uso de suelo** — la puja es `U = λ_h(y − p) − α_h·T − ρ_h·dens`, así que la
  TMS entre tiempo y dinero es `α_h/λ_h`, también un valor del tiempo.

Nada obligaba a que coincidieran, y hasta el 2026-09-02 no coincidían: con los
`λ` uniformes que imponía la forma cerrada (D-08), el uso de suelo implicaba un
VOT de 6,5 / 6,0 / 5,5 —razón alto/bajo 1,18— mientras transporte usaba
6.200 / 3.100 / 1.600 $/h —razón 3,875. El mismo hogar valoraba su tiempo casi
igual entre estratos al pujar por suelo y 3,9 veces distinto al elegir modo.

Desde D-34 (sep-2026) la conciliación es literal, no sólo en razones: la
accesibilidad que entra a la puja es el logsum mensual de transporte, `α = 1`
lo lee tal cual y `λ_h = |b_costo_h|` lo pasa a pesos. Estos tests son un test
de CONSISTENCIA ENTRE MÓDULOS: no verifican una cuenta interna del uso de
suelo, sino que dos calibraciones que viven en archivos distintos sigan
contando la misma historia. Si alguien mueve los betas de la demanda, acá salta
el desfase — que es lo único que impide que los `λ` del schema vuelvan a ser
números mágicos.
"""

from __future__ import annotations

import numpy as np

from titirilquen_core.bienestar import vot_clp_hora
from titirilquen_core.config import DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import DEFAULT_STRATA

#: El estrato `h` del uso de suelo (0=alto, 1=medio, 2=bajo) es el `h+1` de
#: transporte (`StratumId` 1=alto, 2=medio, 3=bajo).
ESTRATOS_TRANSPORTE = (1, 2, 3)


def _b_costo() -> np.ndarray:
    return np.array([abs(DEFAULT_STRATA[h]["betas"]["b_costo"]) for h in ESTRATOS_TRANSPORTE])


def _vot_transporte() -> np.ndarray:
    """VOT conductual por estrato ($/hora), del módulo de transporte."""
    cfg = SimulationConfig(demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}))
    return np.array([vot_clp_hora(cfg, h) for h in ESTRATOS_TRANSPORTE])


def _vot_suelo() -> np.ndarray:
    """VOT implícito por estrato (`α/λ`, en utiles de transporte ÷ utiles/$),
    del uso de suelo. Con α = 1 y λ = |b_costo| sale en $ por utile de
    transporte, que ×b_tiempo·60 es exactamente el VOT en $/h."""
    return np.array([e.alpha / e.lambda_ for e in LandUseConfig().estratos])


def test_lambda_es_literalmente_el_b_costo_de_transporte() -> None:
    """`λ_h = |b_costo_h|`, sin normalizar: un hogar, una función de utilidad.

    Desde D-34 el nivel de λ ya no es libre: lo fija transporte, porque la
    accesibilidad entra en utiles de transporte y λ es lo que la pasa a pesos.
    """
    lambdas = np.array([e.lambda_ for e in LandUseConfig().estratos])
    np.testing.assert_allclose(
        lambdas,
        _b_costo(),
        rtol=1e-9,
        err_msg=(
            "los lambda del schema dejaron de ser el |b_costo| de presets.DEFAULT_STRATA. "
            "Si recalibraste transporte, copiá los nuevos b_costo acá (D-34)."
        ),
    )


def test_alpha_es_uno_y_comun() -> None:
    """`α = 1` en los tres: la puja lee el logsum mensual tal cual.

    Es el ancla del original (`actualizar(T, alpha=[1,1,1])` sobre el logsum).
    Cualquier otro valor es un multiplicador sin fuente; si se quiere más o
    menos nitidez, la perilla es `beta`, no `alpha`.
    """
    alphas = [e.alpha for e in LandUseConfig().estratos]
    assert alphas == [1.0, 1.0, 1.0], f"alpha = {alphas}"


def test_el_vot_es_el_mismo_en_los_dos_modulos() -> None:
    """`α_h/λ_h · b_tiempo_viaje · 60` reproduce el VOT de transporte en $/h,
    en NIVEL y no sólo en razones."""
    bt = np.array([abs(DEFAULT_STRATA[h]["betas"]["b_tiempo_viaje"]) for h in ESTRATOS_TRANSPORTE])
    vot_desde_suelo = _vot_suelo() * bt * 60.0
    np.testing.assert_allclose(
        vot_desde_suelo,
        _vot_transporte(),
        rtol=1e-6,
        err_msg=(
            "el valor del tiempo dejó de ser el mismo en los dos módulos.\n"
            f"  transporte: {_vot_transporte().round(1)} $/h\n"
            f"  suelo (α/λ·b_t·60): {vot_desde_suelo.round(1)} $/h"
        ),
    )


def test_la_utilidad_marginal_del_ingreso_decrece_con_el_ingreso() -> None:
    """`λ_alto < λ_medio < λ_bajo`: un peso vale más para quien tiene menos.

    Fija el SIGNO, que es lo que da la dirección del gradiente de Alonso: con
    `λ` menor, el estrato alto convierte la misma accesibilidad en más pesos
    y puja más fuerte por las parcelas centrales.
    """
    estratos = LandUseConfig().estratos
    lambdas = [e.lambda_ for e in estratos]
    ingresos = [e.y for e in estratos]

    assert ingresos[0] > ingresos[1] > ingresos[2], "los estratos no están ordenados por ingreso"
    assert lambdas[0] < lambdas[1] < lambdas[2], (
        f"λ = {lambdas} no decrece con el ingreso {ingresos}: la utilidad marginal "
        "del ingreso tiene que ser MENOR para el estrato más rico."
    )


def test_el_default_usa_la_subasta_heteroscedastica() -> None:
    """Guard: con `λ` heterogéneos el despacho ya no puede ir a la forma cerrada.

    Si alguien devuelve los `λ` a uniformes, el modelo vuelve a ser el que D-08
    declaraba mal especificado. Esto lo detecta.
    """
    lambdas = {e.lambda_ for e in LandUseConfig().estratos}
    assert len(lambdas) > 1, (
        "los `lambda` por defecto volvieron a ser uniformes: el módulo despacha a "
        "la forma cerrada y `lambda` deja de estar identificado (D-08)."
    )


def test_una_escala_comun_de_lambda_no_mueve_la_asignacion() -> None:
    """D-41: escalar los tres λ por k reescala el determinístico `f/λ`, el ruido
    `1/(βλ)` y `ρ/λ` a la vez: la composición Q no cambia, sólo la unidad de las
    rentas. Por eso la UI no ofrece ese control."""
    from titirilquen_core.land_use import LandUseCity
    from titirilquen_core.land_use.accesibilidad import T_flujo_libre
    from titirilquen_core.land_use.config import LandUseStratumConfig

    L, CBD, dx = 101, 50, 20 / 101
    dem = DemandConfig.model_validate({"estratos": DEFAULT_STRATA})
    T = T_flujo_libre(dem, L, CBD, dx, supply=SupplyConfig())
    base = LandUseConfig(H_por_estrato=(720, 1800, 1080), max_iter=5000)
    escalada = base.model_copy(
        update={
            "estratos": tuple(
                LandUseStratumConfig(y=e.y, alpha=e.alpha, rho=e.rho, **{"lambda": e.lambda_ * 10})
                for e in base.estratos
            )
        }
    )
    Q0 = LandUseCity.build(L=L, CBD=CBD, cfg=base, ancho_celda_km=dx, T=T).result.Q
    Q1 = LandUseCity.build(L=L, CBD=CBD, cfg=escalada, ancho_celda_km=dx, T=T).result.Q
    assert np.max(np.abs(Q0 - Q1)) < 1e-8
