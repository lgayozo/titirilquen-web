"""El motor de ciudad: la población entera aprende con la congestión endógena.

Se usa una ciudad chica (51 celdas, 1.400 agentes) para que la suite siga siendo
rápida. Lo que se verifica es el comportamiento del motor, no los números de los
informes: ésos salen de la ciudad de la app y viven en el sandbox.
"""

from __future__ import annotations

import numpy as np
import pytest

from titirilquen_core.aprendizaje.ciudad import (
    BANDAS,
    MODOS_CIUDAD,
    dispersion_entre_iguales,
    preparar_escenario,
    simular_ciudad,
    softmax_filas,
    suerte_del_estreno,
)
from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.presets import DEFAULT_STRATA

#: Ventanas que caben en el horizonte corto de los tests.
VENTANAS = {"corto": (1, 3), "medio": (4, 10), "largo": (11, 25)}
COMUN = {"dias": 25, "ultimos": 8, "ventanas": VENTANAS}


@pytest.fixture(scope="module")
def escenario():
    """Una ciudad chica, resuelta una vez para todo el módulo."""
    sim = SimulationConfig(
        city=CityConfig(n_celdas=51, largo_ciudad_km=20),
        supply=SupplyConfig(),
        demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}),
        max_iter=40,
        tolerance=0.05,
        seed=42,
    )
    lu = LandUseConfig(
        H_por_estrato=(300, 700, 400),
        forma="normal",
        oferta_sigma_frac=0.5,
        max_iter=2000,
    )
    return preparar_escenario(sim, lu, k_modos=2)


# --- El softmax -----------------------------------------------------------------


def test_las_probabilidades_suman_uno():
    V = np.array([[1.0, 0.0, -2.0], [0.5, 0.5, 0.5]])
    assert np.allclose(softmax_filas(V, 1.0).sum(axis=1), 1.0)


def test_la_escala_afila_la_eleccion():
    """Subir la escala concentra la probabilidad en el mejor; bajarla reparte."""
    V = np.array([[1.0, 0.0]])
    assert softmax_filas(V, 5.0)[0, 0] > softmax_filas(V, 1.0)[0, 0]
    assert softmax_filas(V, 0.2)[0, 0] < softmax_filas(V, 1.0)[0, 0]


def test_los_modos_infactibles_quedan_en_cero():
    V = np.array([[1.0, -np.inf, 0.0]])
    p = softmax_filas(V, 1.0)
    assert p[0, 1] == 0.0
    assert p.sum() == pytest.approx(1.0)


# --- El escenario ---------------------------------------------------------------


def test_el_escenario_describe_la_poblacion(escenario):
    assert escenario.N > 0
    assert escenario.K == 2
    assert escenario.V_ref.shape == (escenario.N, len(MODOS_CIUDAD))
    assert escenario.J.max() <= len(MODOS_CIUDAD)
    # Quien elige tiene al menos dos modos factibles, por definición.
    assert np.all(escenario.J[escenario.elige] >= 2)
    assert sum(escenario.split_equilibrio) == pytest.approx(1.0)


def test_la_ventaja_se_mide_sobre_el_segundo(escenario):
    """dv es la distancia al segundo mejor, así que nunca es negativa."""
    assert np.all(escenario.dv[escenario.elige] >= 0)


def test_solo_dos_o_tres_modos_se_aprenden(escenario):
    sim, lu = escenario.sim, None
    with pytest.raises(ValueError, match="k_modos"):
        preparar_escenario(sim, lu, k_modos=4)  # type: ignore[arg-type]


# --- Los controles del motor ----------------------------------------------------


def test_sin_ruido_la_ciudad_reproduce_su_equilibrio(escenario):
    """Con σ = 0 no hay nada que aprender: Φ = 1 y nadie se diferencia.

    Es el control que valida todo lo demás. Si esto no da 1, el prior, la
    utilidad o la carga de la red están mal conectados.
    """
    r = simular_ciudad(escenario, d=0.5, sigma=0.0, **COMUN)
    for w in VENTANAS:
        assert r["phi"]["todos"][w] == pytest.approx(1.0, abs=0.02)
    assert r["dispersion_iguales"] == pytest.approx(1.0, abs=0.15)


def test_sin_ruido_la_suerte_del_estreno_no_existe(escenario):
    """Sin ε no hay primer día bueno ni malo: los dos grupos son el mismo."""
    r = simular_ciudad(escenario, d=0.5, sigma=0.0, **COMUN)
    mala = r["share_fin_mala_suerte_auto"]
    buena = r["share_fin_buena_suerte_auto"]
    assert mala == pytest.approx(buena, abs=1e-9)


def test_el_ruido_diferencia_a_personas_identicas(escenario):
    """Con ruido, gente idéntica por construcción se separa más que la binomial."""
    sin = simular_ciudad(escenario, d=1.28, sigma=0.0, **COMUN)
    con = simular_ciudad(escenario, d=1.28, sigma=80.0, **COMUN)
    assert con["dispersion_iguales"] > sin["dispersion_iguales"]


def test_la_corrida_es_reproducible(escenario):
    a = simular_ciudad(escenario, d=0.5, sigma=40.0, semilla=7, **COMUN)
    b = simular_ciudad(escenario, d=0.5, sigma=40.0, semilla=7, **COMUN)
    assert a["split_ultimos"] == b["split_ultimos"]
    assert a["phi"]["todos"] == b["phi"]["todos"]


def test_el_ruido_en_un_modo_empuja_hacia_el_otro(escenario):
    """La pregunta de E4: el modo con ruido pierde viajes contra el que no.

    No se compara contra el día 0 sino contra el control sin ruido de la misma
    corrida, que es la línea base correcta.
    """
    control = simular_ciudad(escenario, d=1.28, sigma=0.0, **COMUN)
    solo_auto = simular_ciudad(escenario, d=1.28, sigma=80.0, ruido=(True, False), **COMUN)
    i_auto, i_metro = 0, 1
    d_auto = solo_auto["split_ultimos"][i_auto] - control["split_ultimos"][i_auto]
    d_metro = solo_auto["split_ultimos"][i_metro] - control["split_ultimos"][i_metro]
    assert d_auto < 0, "el modo con ruido tiene que perder cuota"
    assert d_metro > 0, "el modo sin ruido tiene que ganarla"


def test_el_ruido_tiene_que_traer_un_valor_por_modo_aprendido(escenario):
    with pytest.raises(ValueError, match="ruido"):
        simular_ciudad(escenario, d=0.5, sigma=10.0, ruido=(True,), **COMUN)


def test_el_horizonte_tiene_que_dar_para_las_ventanas(escenario):
    with pytest.raises(ValueError, match="días"):
        simular_ciudad(escenario, d=0.5, dias=2)
    with pytest.raises(ValueError, match="ultimos"):
        simular_ciudad(escenario, d=0.5, dias=10, ultimos=50)


# --- Los indicadores ------------------------------------------------------------


def test_phi_se_abre_por_banda_y_por_modo_mejor(escenario):
    r = simular_ciudad(escenario, d=0.5, sigma=40.0, **COMUN)
    assert len(r["phi"]["bandas"]) == len(BANDAS)
    assert sum(b["n"] for b in r["phi"]["bandas"]) == int(escenario.elige.sum())
    # Cada grupo trae P* y 1/J crudos: Φ amplifica donde su diferencia es chica.
    for fila in r["phi"]["por_mejor"].values():
        assert 0.0 <= fila["p_estrella"] <= 1.0
        assert 0.0 < fila["uniforme"] <= 1.0


def test_la_cuota_del_mejor_cubre_a_todos_los_que_eligen(escenario):
    r = simular_ciudad(escenario, d=0.5, sigma=40.0, **COMUN)
    cm = r["cuota_mejor"]
    assert cm["n"] == int(escenario.elige.sum())
    assert 0.0 <= cm["todos"] <= 1.0


def test_la_suerte_necesita_muestra(escenario):
    """Con menos de 20 casos no se dice nada: devuelve NaN en vez de inventar."""
    mala, buena = suerte_del_estreno(np.full(5, 1.0), np.full(5, 0.5))
    assert np.isnan(mala) and np.isnan(buena)


def test_la_dispersion_de_una_poblacion_sin_elegir_no_revienta(escenario):
    """Si nadie puede elegir no hay varianza que comparar: NaN, no un error."""
    import copy

    esc = copy.copy(escenario)
    esc.elige = np.zeros(escenario.N, dtype=bool)
    assert np.isnan(dispersion_entre_iguales(esc, np.zeros((escenario.N, 4), dtype=int)))


# --- La puerta desde la interfaz ------------------------------------------------


def test_la_puerta_devuelve_lo_que_la_pagina_muestra(escenario):
    """`ejecutar_ciudad` arma el resultado serializable, sin recalcular la ciudad."""
    from titirilquen_core.aprendizaje import ConfigCiudad, ejecutar_ciudad

    r = ejecutar_ciudad(escenario, ConfigCiudad(dias=25, ultimos=8))
    assert r["n_agentes"] == escenario.N
    assert r["eligen"] == int(escenario.elige.sum())
    assert len(r["split_por_dia"]) == 25
    assert sum(r["split_ultimos"]) == pytest.approx(1.0)
    # Sin ruido: Φ = 1 y la brecha de percepción es cero.
    assert r["phi"]["largo"] == pytest.approx(1.0, abs=0.02)
    assert r["brecha_percepcion_min"] == pytest.approx(0.0, abs=1e-9)


def test_la_tabla_por_modo_mejor_marca_quien_lleva_el_ruido(escenario):
    """La columna que decide el signo en E4: si el ruido cayó en TU modo mejor."""
    from titirilquen_core.aprendizaje import ConfigCiudad, ejecutar_ciudad

    r = ejecutar_ciudad(
        escenario,
        ConfigCiudad(dias=25, ultimos=8, sigma_min=80.0, ruido_auto=True, ruido_metro=False),
    )
    por_modo = {g["modo"]: g for g in r["por_mejor"]}
    assert por_modo["Auto"]["lleva_ruido"] is True
    assert por_modo["Metro"]["lleva_ruido"] is False
    # Quien tiene el ruido encima pierde; quien no, no.
    assert por_modo["Auto"]["phi"]["largo"] < por_modo["Metro"]["phi"]["largo"]


def test_sin_ruido_nadie_lleva_ruido(escenario):
    """Con σ = 0 la marca tiene que ser False aunque los modos estén activados."""
    from titirilquen_core.aprendizaje import ConfigCiudad, ejecutar_ciudad

    r = ejecutar_ciudad(escenario, ConfigCiudad(dias=25, ultimos=8))
    assert not any(g["lleva_ruido"] for g in r["por_mejor"])


def test_la_ventana_final_no_puede_pasar_del_horizonte():
    from titirilquen_core.aprendizaje import ConfigCiudad

    with pytest.raises(ValueError, match="ultimos"):
        ConfigCiudad(dias=10, ultimos=40)
