"""LA RED DE SEGURIDAD: el reparto modal de la ciudad por defecto, pineado.

Este test existe para una sola cosa: que una cirugía de arquitectura no mueva
los números del simulador sin que nadie se entere. Se corre al cierre de cada
fase de refactor. Si falla, el refactor tocó el modelo — no la forma.

**Los valores de configuración están hardcodeados a propósito.** El test debe
seguir describiendo la corrida de la aplicación aunque los defaults del core
cambien; si tomara los defaults de Pydantic, un cambio de default se
auto-justificaría y el test dejaría de vigilar nada. La contraparte es que
cuando el frontend cambie un default hay que actualizar acá también, y el
comentario de cada valor dice de dónde sale.

Las dos ramas de `localizacion` son escenarios REALES de la app, no variantes
teóricas — `SandboxPage.tsx` elige entre ellas según si el usuario ya corrió el
módulo de Uso de Suelo:

    localizacion: landUseCity.isPost ? "equilibrio" : "original"

Medido el 2026-08-15 y contrastado con dos fuentes independientes: la rama
"equilibrio" reproduce la línea base documentada en `docs/CONTINUAR.md` §2.4, y
la rama "original" reproduce lo que muestra el navegador al simular sin haber
corrido Uso de Suelo.
"""

from __future__ import annotations

import pytest

from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import DEFAULT_STRATA

#: Tolerancia del pineo, en puntos porcentuales. 0,05 pp es más fino que el
#: segundo decimal que reportan los informes, y holgado frente al ruido de
#: coma flotante entre plataformas.
TOL_PP = 0.05

#: Reparto esperado por rama de `localizacion`, en % del total de agentes
#: (teletrabajo incluido en el denominador, como lo muestra la app).
ESPERADO = {
    # Movida dos veces en sep-2026, y las dos veces a propósito:
    #  1. `lambda` del uso de suelo heterogéneo (VOT-consistente con transporte):
    #     movió sólo `equilibrio` (metro +1,36 pp), porque `original` no pasa por
    #     el módulo de suelo.
    #  2. Transporte HOMOSCEDÁSTICO (`presets.py`): el bloque de betas del alto
    #     se reescaló por 0,0331/0,055 y el del bajo por 0,0331/0,015, o sea el
    #     alto elige modo con MÁS ruido que antes y el bajo con MENOS. Mueve las
    #     dos ramas: auto −1,6 pp (el alto baja de 57 % a 48 % de auto), y ese
    #     flujo se reparte entre metro, bici y caminata. Por estrato, sobre
    #     viajeros, rama original: auto 47,7 / 22,6 / 3,7 %.
    #  3. D-34: la accesibilidad de la puja pasa de minutos a flujo libre al
    #     logsum mensual de transporte por estrato, con alpha = 1 y
    #     lambda = |b_costo|. Mueve sólo `equilibrio`, y poco (auto +0,03,
    #     metro −0,13, bici +0,05, caminata +0,08): la ciudad resultante es casi
    #     la misma, ahora con unidades que cierran.
    #  4. beta = 0,15 ≈ 1/√44 (ruido acumulado en el mes, no el de un viaje):
    #     la ciudad de partida pasa de Theil 0,75 a 0,16 —el estrato bajo ya no
    #     queda confinado a la periferia (5,5 km en vez de 6,7)— y sus viajes
    #     más cortos migran del metro a la caminata y la bici: metro −3,0 pp,
    #     caminata +1,65, bici +1,10, auto +0,20. `original` sigue intacta.
    #  5. D-42: la accesibilidad del suelo standalone (y del arranque del
    #     acoplado) pasa del «flujo libre» con 10 min de acceso fijos a la red
    #     VACÍA configurada (estaciones reales, frecuencia mínima). Mueve poco:
    #     metro −0,11, caminata +0,07, bici +0,04, auto −0,03.
    "equilibrio": {
        "Auto": 15.39,
        "Metro": 32.06,
        "Bici": 23.89,
        "Caminata": 9.14,
        "Teletrabajo": 19.53,
    },
    "original": {
        "Auto": 15.81,
        "Metro": 28.32,
        "Bici": 24.96,
        "Caminata": 11.42,
        "Teletrabajo": 19.49,
    },
}

#: Iteraciones hasta converger. Pinearlo detecta cambios en la dinámica del MSA
#: que el reparto final podría no mostrar.
#: `equilibrio` pasó de 7 a 8 con los `lambda` heterogéneos (sep-2026): la ciudad
#: de partida es más segregada y el MSA necesita una pasada más. El reescalado
#: homoscedástico de transporte no cambió el conteo.
ITERACIONES_ESPERADAS = {"equilibrio": 8, "original": 8}


def _config_web() -> SimulationConfig:
    """La `SimulationConfig` con la que arranca la aplicación.

    Valores de `apps/web/src/lib/defaults.ts::defaultSimulationConfig`; los que
    difieren del default de Pydantic están marcados — son las divergencias
    intencionales que el contrato del frontend declara.
    """
    return SimulationConfig(
        city=CityConfig(
            n_celdas=201,  # web: 201 · core: 1001
            largo_ciudad_km=20,
        ),
        supply=SupplyConfig(),
        demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}),
        max_iter=20,
        tolerance=0.1,
        seed=42,  # web fija la semilla; el core la deja libre
        assignment="expected",  # web: expected · core: montecarlo
    )


def _land_use_web() -> LandUseConfig:
    """El `LandUseConfig` con el que arranca la aplicación.

    De `defaults.ts::defaultLandUseConfig`. ΣH = 36.000 = 1.800 hab/km sobre
    20 km, shares 20/50/30. `max_iter` 2.000 es del frontend (el core trae
    10.000); con `tol = 1e-8` ambos convergen al mismo punto, pero se usa el de
    la app porque es la corrida que este test describe.
    """
    return LandUseConfig(
        H_por_estrato=(7200, 18000, 10800),
        forma="normal",
        oferta_sigma_frac=0.5,
        max_iter=2000,
    )


def _corre(localizacion: str) -> tuple[dict[str, float], int, bool]:
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(_config_web(), _land_use_web(), trace, localizacion=localizacion):
        pass
    split = trace.iteraciones[-1].modal_split
    total = sum(split.values())
    pct = {modo: 100.0 * valor / total for modo, valor in split.items()}
    return pct, len(trace.iteraciones), trace.converged


@pytest.mark.parametrize("localizacion", ["equilibrio", "original"])
def test_linea_base_reparto_modal(localizacion: str) -> None:
    """El reparto modal de la ciudad por defecto no se mueve."""
    pct, _, converged = _corre(localizacion)
    assert converged, f"la corrida base de '{localizacion}' dejó de converger"

    esperado = ESPERADO[localizacion]
    desvios = {
        modo: (pct[modo], objetivo)
        for modo, objetivo in esperado.items()
        if abs(pct[modo] - objetivo) > TOL_PP
    }
    assert not desvios, (
        f"el reparto modal de '{localizacion}' se movió más de {TOL_PP} pp.\n"
        + "\n".join(f"  {m}: {obt:.2f}% (esperado {esp:.2f}%)" for m, (obt, esp) in desvios.items())
        + "\n\nSi el cambio es DELIBERADO, actualiza ESPERADO y explica el porqué "
        "en el mensaje del commit. Si no lo es, el refactor tocó el modelo."
    )


@pytest.mark.parametrize("localizacion", ["equilibrio", "original"])
def test_linea_base_iteraciones(localizacion: str) -> None:
    """La dinámica del MSA tampoco: mismo número de iteraciones hasta converger."""
    _, iteraciones, _ = _corre(localizacion)
    assert iteraciones == ITERACIONES_ESPERADAS[localizacion]


def test_las_dos_ramas_de_localizacion_difieren() -> None:
    """Guard del propio test: si las dos ramas coincidieran, una de las dos no
    se estaría ejerciendo y el pineo sería falso.

    Bajo `original` los estratos se mezclan uniformemente en cada celda; bajo
    `equilibrio` el bid-rent los ordena por distancia al CBD, y el estrato alto
    —el que tiene auto— queda más cerca. El metro cae casi 5 pp.
    """
    equilibrio, _, _ = _corre("equilibrio")
    original, _, _ = _corre("original")
    assert abs(equilibrio["Metro"] - original["Metro"]) > 1.0
