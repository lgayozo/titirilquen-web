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

Estos tests fijan la conciliación. Son un test de CONSISTENCIA ENTRE MÓDULOS: no
verifican una cuenta interna del uso de suelo, sino que dos calibraciones que
viven en archivos distintos sigan contando la misma historia. Si alguien mueve
los betas de la demanda o los `alpha` de las pujas, acá salta el desfase — que es
lo único que impide que los `λ` del schema vuelvan a ser números mágicos.
"""

from __future__ import annotations

import numpy as np

from titirilquen_core.bienestar import vot_clp_hora
from titirilquen_core.config import DemandConfig, SimulationConfig
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import DEFAULT_STRATA

#: El estrato `h` del uso de suelo (0=alto, 1=medio, 2=bajo) es el `h+1` de
#: transporte (`StratumId` 1=alto, 2=medio, 3=bajo).
ESTRATOS_TRANSPORTE = (1, 2, 3)

#: Índice del estrato que sirve de numerario. El NIVEL común de `λ` no está
#: identificado —escalarlos todos por k equivale a escalar `beta` por k (AU-13)—
#: así que sólo tienen sentido las RAZONES. Se comparan normalizadas al medio.
NUMERARIO = 1

#: Tolerancia relativa sobre las razones de VOT. Los `λ` del schema están
#: redondeados a 4 decimales, lo que introduce un error de ~6e-5; 1e-3 lo cubre
#: con holgura y sigue detectando cualquier recalibración real.
TOL_REL = 1e-3


def _vot_transporte() -> np.ndarray:
    """VOT conductual por estrato ($/hora), del módulo de transporte."""
    cfg = SimulationConfig(demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}))
    return np.array([vot_clp_hora(cfg, h) for h in ESTRATOS_TRANSPORTE])


def _vot_suelo() -> np.ndarray:
    """VOT implícito por estrato (`α/λ`, en utiles/min ÷ utiles/$), del uso de suelo."""
    return np.array([e.alpha / e.lambda_ for e in LandUseConfig().estratos])


def test_lambda_es_consistente_con_el_vot_de_transporte() -> None:
    """`α_h/λ_h` reproduce el perfil de VOT de la demanda modal.

    Es LA razón de ser de los `λ` heterogéneos del schema: sin esta condición,
    0,5417 y 1,7760 serían tres números elegidos a mano.
    """
    razon_transporte = _vot_transporte() / _vot_transporte()[NUMERARIO]
    razon_suelo = _vot_suelo() / _vot_suelo()[NUMERARIO]

    assert np.allclose(razon_suelo, razon_transporte, rtol=TOL_REL), (
        "el valor del tiempo dejó de ser el mismo en los dos módulos.\n"
        f"  transporte (VOT normalizado al medio): {razon_transporte.round(4)}\n"
        f"  uso de suelo (α/λ  normalizado):       {razon_suelo.round(4)}\n\n"
        "Si moviste los betas de la demanda o los `alpha` de las pujas, recalculá "
        "los `lambda` del schema como λ_h = α_h/VOT_h, normalizados a λ_medio = 1. "
        "Si el desfase es DELIBERADO, decilo en el commit: significa que el mismo "
        "hogar valora su tiempo distinto según el módulo."
    )


def test_la_utilidad_marginal_del_ingreso_decrece_con_el_ingreso() -> None:
    """`λ_alto < λ_medio < λ_bajo`: un peso vale más para quien tiene menos.

    Fija el SIGNO, que es lo que da la dirección del gradiente de Alonso: con
    `λ` menor, el estrato alto tiene `α/λ` mayor —valora más su tiempo— y puja
    más fuerte por las parcelas centrales.
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

    Si alguien devuelve los `λ` a uniformes, los dos tests de arriba podrían
    seguir pasando por casualidad (con `α` recalibrados), pero el modelo volvería
    a ser el que D-08 declaraba mal especificado. Esto lo detecta.
    """
    lambdas = {e.lambda_ for e in LandUseConfig().estratos}
    assert len(lambdas) > 1, (
        "los `lambda` por defecto volvieron a ser uniformes: el módulo despacha a "
        "la forma cerrada y `lambda` deja de estar identificado (D-08)."
    )


def test_alpha_es_comun_como_en_transporte() -> None:
    """Un minuto duele igual a todos: `alpha` no lleva heterogeneidad.

    Es el espejo de `test_los_estratos_comparten_la_escala_del_tiempo` en
    transporte. Con `alpha` común, TODA la heterogeneidad del VOT vive en `λ`,
    y los dos módulos cuentan la misma historia (utilidad marginal del ingreso
    decreciente), no sólo el mismo número.
    """
    alphas = {e.alpha for e in LandUseConfig().estratos}
    assert len(alphas) == 1, f"alpha difiere entre estratos: {sorted(alphas)}"
