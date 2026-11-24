"""Las funciones de consumo del MESPIVU, contra valores de sus propias tablas."""

import pytest

from titirilquen_core.config import PreciosSociales
from titirilquen_core.operacion_vehicular import (
    consumo_combustible_auto_ml_km,
    otros_costos_operacion_auto_clp_km,
)


@pytest.mark.parametrize(
    ("v", "ml_km"),
    [(10, 205.6), (30, 81.3), (50, 63.7), (60, 62.4), (100, 80.1)],
)
def test_el_consumo_reproduce_la_tabla(v: float, ml_km: float) -> None:
    assert consumo_combustible_auto_ml_km(v) == pytest.approx(ml_km)


def test_el_consumo_interpola_entre_filas() -> None:
    # a medio camino entre 20 km/h (110,2) y 30 km/h (81,3)
    assert consumo_combustible_auto_ml_km(25) == pytest.approx((110.2 + 81.3) / 2)


def test_fuera_de_la_tabla_se_queda_en_el_extremo() -> None:
    assert consumo_combustible_auto_ml_km(3) == pytest.approx(205.6)
    assert consumo_combustible_auto_ml_km(130) == pytest.approx(80.1)


def test_la_congestion_sube_el_consumo() -> None:
    """Lo que el costo fijo por km no podía mostrar: a 15 km/h se gasta más
    bencina por kilómetro que a 50."""
    assert consumo_combustible_auto_ml_km(15) > consumo_combustible_auto_ml_km(50)


def test_los_otros_costos_sin_rugosidad() -> None:
    """Con IRI = 0 queda sólo el término α de cada consumo (por 1.000 km):
    1,109 l · 8.740 + 0,052 neum · 87.543 + 0,173 % · 11.360.008 + 1,083 h · 6.931."""
    por_mil_km = 1.109 * 8740 + 0.052 * 87543 + 0.00173 * 11360008 + 1.083 * 6931
    base = otros_costos_operacion_auto_clp_km(PreciosSociales())
    assert base == pytest.approx(por_mil_km / 1000)
    assert base == pytest.approx(41.40, abs=0.01)


def test_la_rugosidad_los_sube() -> None:
    rugoso = otros_costos_operacion_auto_clp_km(PreciosSociales(iri=4.0))
    assert rugoso > otros_costos_operacion_auto_clp_km(PreciosSociales())


def test_los_precios_son_los_de_la_configuracion() -> None:
    """Con todos los precios en cero no queda costo: nada está fijo en el código."""
    gratis = PreciosSociales(
        lubricante_auto_clp_l=0, neumatico_auto_clp=0, vehiculo_auto_clp=0, mantencion_clp_h=0
    )
    assert otros_costos_operacion_auto_clp_km(gratis) == 0
