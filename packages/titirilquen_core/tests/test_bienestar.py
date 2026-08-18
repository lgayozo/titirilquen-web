"""Las dos medidas de excedente y su emparejamiento con el método.

`bienestar.py` entrega el excedente del consumidor en dos versiones —logsum y
utilidad máxima media— porque responden a dos supuestos distintos sobre el
agente: con término aleatorio Gumbel (logit) y sin él (`todo_o_nada`). Acá se
verifican PROPIEDADES de esa relación, no niveles calibrados: los números de la
ciudad real son trabajo de `test_linea_base`.

Lo que hace falta vigilar es que la regla de emparejamiento viva en el núcleo.
Si `medida_bienestar` dejara de seguir a `assignment`, la UI mostraría un
excedente que no corresponde al modelo que corrió, y nada más lo detectaría: es
un número plausible en una tabla.
"""

from __future__ import annotations

import math

import pytest

from titirilquen_core.bienestar import calcular_agregados
from titirilquen_core.config import SimulationConfig
from titirilquen_core.constantes import MODOS
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.config import LandUseConfig

ESTRATOS = ("1", "2", "3")


@pytest.fixture
def lu_chica() -> LandUseConfig:
    return LandUseConfig(H_por_estrato=(200, 500, 300), forma="normal", max_iter=200)


def _agregados(sim: SimulationConfig, lu: LandUseConfig, metodo: str):
    sim.assignment = metodo
    sim.max_iter = 8
    sim.tolerance = 0.1
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu, trace):
        pass
    agg = calcular_agregados(sim, trace)
    assert agg is not None, "la corrida no produjo agregados"
    return agg


@pytest.mark.parametrize("metodo", ["montecarlo", "expected", "todo_o_nada"])
def test_el_logsum_domina_a_la_utilidad_maxima(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig, metodo: str
) -> None:
    """`ln Σ e^{V_m} >= max_m V_m` — desigualdad log-sum-exp, por estrato.

    Vale para cualquier método porque las dos medidas se calculan siempre; lo
    que cambia con el método es cuál se usa, no cuánto valen.
    """
    agg = _agregados(sim_liviana, lu_chica, metodo)
    for h in ESTRATOS:
        assert agg["logsum_por_estrato"][h] >= agg["util_maxima_por_estrato"][h] - 1e-9, (
            f"estrato {h}: el logsum ({agg['logsum_por_estrato'][h]:.6f}) quedó por debajo "
            f"de la utilidad máxima ({agg['util_maxima_por_estrato'][h]:.6f}), que es "
            f"imposible por log-sum-exp"
        )


def test_la_brecha_no_supera_el_log_del_numero_de_modos(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """La brecha entre ambas medidas está acotada por `ln(nº modos)`.

    Es la otra mitad de log-sum-exp, y acota cuánto puede valer la dispersión de
    gustos: con J alternativas de utilidad idéntica el logsum las supera en
    exactamente `ln J`. Como la media pondera brechas individuales acotadas, la
    media también lo está.
    """
    agg = _agregados(sim_liviana, lu_chica, "expected")
    techo = math.log(len(MODOS))
    for h in ESTRATOS:
        brecha = agg["logsum_por_estrato"][h] - agg["util_maxima_por_estrato"][h]
        assert brecha <= techo + 1e-9, (
            f"estrato {h}: brecha {brecha:.6f} sobre el techo ln({len(MODOS)}) = {techo:.6f}"
        )


@pytest.mark.parametrize(
    ("metodo", "esperada"),
    [
        ("montecarlo", "logsum"),
        ("expected", "logsum"),
        ("todo_o_nada", "utilidad_maxima"),
    ],
)
def test_la_medida_sigue_al_metodo(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig, metodo: str, esperada: str
) -> None:
    """El emparejamiento es la razón de ser de este cambio: bajo `todo_o_nada`
    no hay término aleatorio, así que el `E[max]` del agente es el máximo."""
    agg = _agregados(sim_liviana, lu_chica, metodo)
    assert agg["medida_bienestar"] == esperada


@pytest.mark.parametrize(
    ("metodo", "campo"),
    [
        ("expected", "excedente_total_clp"),
        ("todo_o_nada", "excedente_max_total_clp"),
    ],
)
def test_el_bienestar_social_usa_la_medida_emparejada(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig, metodo: str, campo: str
) -> None:
    """Sumarle recaudación a un excedente de la medida equivocada mezclaría dos
    supuestos de comportamiento en un solo número."""
    agg = _agregados(sim_liviana, lu_chica, metodo)
    esperado = (
        agg[campo]
        + agg["recaudacion_parking_clp"]
        + agg["recaudacion_tarifa_clp"]
        - agg["costo_operador_clp"]
    )
    assert agg["bienestar_social_clp"] == pytest.approx(esperado, rel=1e-9)


def test_las_dos_medidas_no_coinciden(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Guard del propio test: si dieran lo mismo, todo lo de arriba pasaría sin
    ejercer nada y el emparejamiento sería decorativo."""
    agg = _agregados(sim_liviana, lu_chica, "expected")
    assert agg["excedente_total_clp"] != pytest.approx(agg["excedente_max_total_clp"], rel=1e-6)


# ---------------------------------------------------------------------------
# El excedente al VoT social
# ---------------------------------------------------------------------------
#
# Tercera medida, agregada el 2026-08-18. Es la misma utilidad emparejada pero
# valorada con el VoT de norma en vez del conductual de cada estrato. Importa
# porque cambia el SIGNO de los Δ agregados: con λ_h el bienestar de la base sube
# monótonamente al agregar pistas y con λ social cae entre 3 y 4 pistas. Si esta
# medida se rompiera, la app mostraría una columna plausible con la ponderación
# equivocada y nadie lo notaría.


def test_el_excedente_social_usa_el_vot_de_norma(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """`exc_social = E[max] · VoT_social / (|β_t| · 60)`, despejado del VoT.

    Se verifica contra el cálculo directo por estrato y no contra un número
    pineado: así el test sigue valiendo si se recalibra `b_tiempo_viaje`.
    """
    from titirilquen_core.constantes import VOT_SOCIAL_CLP_HORA

    agg = _agregados(sim_liviana, lu_chica, "expected")
    for h in ESTRATOS:
        b_t = abs(sim_liviana.demand.estratos[int(h)].betas.b_tiempo_viaje)
        lam_social = b_t * 60 / VOT_SOCIAL_CLP_HORA
        esperado = agg["logsum_por_estrato"][h] / lam_social
        assert agg["excedente_social_por_estrato_clp"][h] == pytest.approx(esperado, rel=1e-9)


def test_el_excedente_social_sigue_la_medida_emparejada(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Bajo `todo_o_nada` parte de la utilidad máxima, no del logsum: si tomara
    siempre el logsum heredaría el supuesto de comportamiento equivocado justo en
    el método donde la paradoja se observa."""
    from titirilquen_core.constantes import VOT_SOCIAL_CLP_HORA

    agg = _agregados(sim_liviana, lu_chica, "todo_o_nada")
    for h in ESTRATOS:
        b_t = abs(sim_liviana.demand.estratos[int(h)].betas.b_tiempo_viaje)
        lam_social = b_t * 60 / VOT_SOCIAL_CLP_HORA
        desde_max = agg["util_maxima_por_estrato"][h] / lam_social
        assert agg["excedente_social_por_estrato_clp"][h] == pytest.approx(desde_max, rel=1e-9)


def test_el_social_y_el_conductual_no_coinciden(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Guard: si dieran lo mismo la tercera columna seria decorativa, y el
    hallazgo sobre el signo de Downs-Thomson no tendria sentido."""
    agg = _agregados(sim_liviana, lu_chica, "expected")
    assert agg["excedente_social_total_clp"] != pytest.approx(agg["excedente_total_clp"], rel=1e-6)
