"""La regla de los presets, como invariante ejecutable.

Los presets declaran valores ABSOLUTOS, no diferencias contra el default. La
consecuencia es contraintuitiva y ya causó cuatro incidentes documentados: si
una política **omite** un parámetro, aplicarla no lo restaura al default —
hereda lo que haya en el escenario vigente.

Ejemplo del último: `factor_flota` estaba declarado sólo en «Base» y en
«Vehículos híbridos» (0,7). Aplicar «Pro-Auto» después de «Vehículos híbridos»
dejaba la flota en 0,7, así que el escenario "pro-auto" salía con menos
emisiones que el base sin que nada lo dijera.

El comentario en `presets.py` advertía de esto desde hacía meses. Un comentario
no puede fallar; este test sí.
"""

from __future__ import annotations

import pytest

from titirilquen_core.presets import CITY_PRESETS, DEFAULT_STRATA, POLICY_PRESETS

#: «Personalizado» es el dict vacío A PROPÓSITO: significa "no toques nada, deja
#: lo que el usuario tenga". Es la única excepción legítima a la regla.
VACIOS_A_PROPOSITO = {"Personalizado"}


def _universo(presets: dict[str, dict]) -> set[str]:
    """Todos los parámetros que alguna variante toca."""
    return {clave for valores in presets.values() for clave in valores}


@pytest.mark.parametrize("nombre", [n for n in POLICY_PRESETS if n not in VACIOS_A_PROPOSITO])
def test_cada_politica_declara_todos_los_parametros(nombre: str) -> None:
    universo = _universo(POLICY_PRESETS)
    faltan = sorted(universo - set(POLICY_PRESETS[nombre]))
    assert not faltan, (
        f"La política «{nombre}» no declara {faltan}.\n"
        "Los presets son ABSOLUTOS: al aplicarla, esos parámetros conservarían "
        "el valor del escenario anterior en vez de volver al default, y el "
        "escenario resultante dependería de en qué orden se apretaron los "
        "botones. Declaralos con su valor por defecto."
    )


def test_la_politica_base_es_el_escenario_de_referencia() -> None:
    """«Base» tiene que ser reproducible: aplicarla desde cualquier escenario
    debe dejar siempre la misma ciudad. Por eso declara TODO."""
    assert set(POLICY_PRESETS["Base"]) == _universo(POLICY_PRESETS)


@pytest.mark.parametrize("nombre", [n for n in CITY_PRESETS if n not in VACIOS_A_PROPOSITO])
def test_cada_ciudad_declara_su_geometria(nombre: str) -> None:
    """Las formas urbanas siempre fijan largo, densidad y dispersión.

    `poblacion` es la excepción deliberada: sólo la declaran «Base» y
    «Metrópolis». Las otras dos comparan FORMA a la población que el usuario
    tenga, que es justamente el punto de la iso-población.
    """
    faltan = {"largo_ciudad", "densidad", "sigma"} - set(CITY_PRESETS[nombre])
    assert not faltan, f"«{nombre}» no declara {sorted(faltan)}"


def test_los_tres_estratos_estan_calibrados() -> None:
    """`DEFAULT_STRATA` es la calibración vigente y la fuente del contrato TS."""
    assert set(DEFAULT_STRATA) == {1, 2, 3}
    for estrato, cfg in DEFAULT_STRATA.items():
        assert "betas" in cfg, f"estrato {estrato} sin betas"
        assert cfg["betas"]["b_tiempo_viaje"] < 0, "el tiempo tiene que penalizar"
        assert cfg["betas"]["b_costo"] < 0, "el dinero tiene que penalizar"


def test_el_valor_del_tiempo_ordena_los_estratos() -> None:
    """VoT = b_tiempo_viaje · 60 / b_costo. Debe decrecer del estrato alto al
    bajo: si se invierte, la calibración está rota y el reparto modal sale al
    revés sin que ningún test de forma lo note."""
    vot = {
        e: cfg["betas"]["b_tiempo_viaje"] * 60 / cfg["betas"]["b_costo"]
        for e, cfg in DEFAULT_STRATA.items()
    }
    assert vot[1] > vot[2] > vot[3], f"valor del tiempo no ordenado: {vot}"
