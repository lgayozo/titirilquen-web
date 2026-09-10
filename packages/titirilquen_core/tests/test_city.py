"""La ciudad lineal, por fin con pruebas propias (cap. 1 del libro).

Hasta sep-2026 el módulo más básico del núcleo no tenía tests: lo que se
verificaba de la ciudad eran sus consecuencias desde otros módulos, y los tres
hallazgos del capítulo 1 (D-45, D-46 y la convergencia de grilla) cayeron justo
en lo que no se probaba. Cada test de acá fija UNA identidad de la geometría o
de la población; los dos últimos corren el MSA y son los únicos que tardan.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from tests._poblacion import suelo_uniforme
from tests.test_linea_base import _config_web, _land_use_web
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
from titirilquen_core.demand.utility import calcular_utilidades
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa_desde_suelo
from titirilquen_core.land_use.supply import generar_oferta
from titirilquen_core.population import generar_poblacion_desde_land_use_det

GRILLAS = ((51, 5.0), (201, 20.0), (1001, 20.0), (11, 1.0))


# ---------------------------------------------------------------------------
# Geometría
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("n", "largo"), GRILLAS)
def test_el_ancho_de_celda_es_el_largo_sobre_n(n: int, largo: float) -> None:
    ciudad = CiudadLineal(n_celdas=n, largo_total_km=largo)
    assert ciudad.ancho_celda_km == pytest.approx(largo / n)
    assert ciudad.ancho_celda_km * n == pytest.approx(largo)


@pytest.mark.parametrize(("n", "largo"), GRILLAS)
def test_el_cbd_es_la_celda_central_y_su_centroide_cae_en_medio_largo(n: int, largo: float) -> None:
    """Con `n` impar la celda `n//2` es la del medio y su centroide es L/2: las
    dos convenciones de distancia —por índice y por posición— coinciden."""
    ciudad = CiudadLineal(n_celdas=n, largo_total_km=largo)
    assert ciudad.cbd_index == n // 2
    assert (ciudad.cbd_index + 0.5) * ciudad.ancho_celda_km == pytest.approx(ciudad.cbd_km)


@pytest.mark.parametrize("n", (200, 50, 12))
def test_una_grilla_par_se_rechaza(n: int) -> None:
    """D-45: con `n` par el centroide de la celda `n//2` cae medio Δx a la
    derecha de L/2. El docstring lo exigía y ningún validador lo leía."""
    with pytest.raises(ValidationError):
        CityConfig(n_celdas=n)
    with pytest.raises(ValueError, match="impar"):
        CiudadLineal(n_celdas=n, largo_total_km=10.0)


def test_la_grilla_no_puede_ser_absurda() -> None:
    with pytest.raises(ValidationError):
        CityConfig(n_celdas=3)


def test_la_distancia_maxima_es_medio_largo_menos_media_celda() -> None:
    ciudad = CiudadLineal(n_celdas=201, largo_total_km=20.0)
    d = np.abs(np.arange(ciudad.n_celdas) - ciudad.cbd_index) * ciudad.ancho_celda_km
    assert d.max() == pytest.approx(ciudad.largo_total_km / 2 - ciudad.ancho_celda_km / 2)
    assert d[ciudad.cbd_index] == 0.0


def test_las_utilidades_son_simetricas_respecto_del_cbd(demanda_sintetica: DemandConfig) -> None:
    """La distancia que usa el núcleo es `|i − cbd|·Δx`: dos celdas espejo tienen
    que producir exactamente las mismas utilidades, modo por modo."""
    ciudad = CiudadLineal(n_celdas=51, largo_total_km=10.0)
    for k in (1, 7, 25):
        izq = calcular_utilidades(
            estrato=2,
            celda_origen=ciudad.cbd_index - k,
            tiene_auto=True,
            ciudad=ciudad,
            config=demanda_sintetica,
            tiempos_observados=None,
        )
        der = calcular_utilidades(
            estrato=2,
            celda_origen=ciudad.cbd_index + k,
            tiene_auto=True,
            ciudad=ciudad,
            config=demanda_sintetica,
            tiempos_observados=None,
        )
        for modo in izq:
            assert izq[modo].valor == pytest.approx(der[modo].valor)
            assert izq[modo].feasible == der[modo].feasible


def test_la_distancia_por_indice_es_la_que_calcula_el_nucleo(
    demanda_sintetica: DemandConfig,
) -> None:
    """Se recupera la distancia desde el término de tiempo de la caminata,
    `β_cam · d/v_cam · 60`, y tiene que ser `|i − cbd|·Δx`."""
    ciudad = CiudadLineal(n_celdas=51, largo_total_km=10.0)
    gl = demanda_sintetica.globales
    b_cam = demanda_sintetica.estratos[2].betas.b_tiempo_caminata
    # Sólo celdas donde la caminata es factible: fuera del corte (2,4 km) el
    # modo no tiene término de tiempo del que recuperar nada.
    for i in (15, 20, 24, 26, 30, 35):
        u = calcular_utilidades(
            estrato=2,
            celda_origen=i,
            tiene_auto=False,
            ciudad=ciudad,
            config=demanda_sintetica,
            tiempos_observados=None,
        )
        assert u["Caminata"].feasible
        d_recuperada = u["Caminata"].v_tiempo / b_cam * gl.v_caminata / 60.0
        assert d_recuperada == pytest.approx(abs(i - ciudad.cbd_index) * ciudad.ancho_celda_km)


# ---------------------------------------------------------------------------
# Población: una sola fuente, y lo que promete
# ---------------------------------------------------------------------------


def _agentes(n: int, largo: float, lu, demanda: DemandConfig):
    ciudad = CiudadLineal(n_celdas=n, largo_total_km=largo)
    S = generar_oferta(
        forma=lu.forma,
        I=n,
        N=int(sum(lu.H_por_estrato)),
        CBD=ciudad.cbd_index,
        sigma_frac=lu.oferta_sigma_frac,
        forma_param=lu.forma_param,
    )
    H = np.asarray(lu.H_por_estrato, dtype=float)
    Q = np.tile((H / H.sum()).reshape(-1, 1), (1, n))
    return (
        ciudad,
        S,
        generar_poblacion_desde_land_use_det(
            Q=Q, S=S, cbd_index=ciudad.cbd_index, demand_config=demanda, teletrabajo_factor=1.0
        ),
    )


def test_el_cbd_no_tiene_hogares(demanda_sintetica: DemandConfig) -> None:
    for forma in ("uniforme", "normal"):
        lu = suelo_uniforme(1000).model_copy(update={"forma": forma})
        ciudad, S, agentes = _agentes(51, 5.0, lu, demanda_sintetica)
        assert S[ciudad.cbd_index] == 0
        assert not any(a.celda_origen == ciudad.cbd_index for a in agentes)


@pytest.mark.parametrize("n", (51, 101, 401))
def test_la_poblacion_es_exactamente_la_del_suelo_en_cualquier_grilla(
    n: int, demanda_sintetica: DemandConfig
) -> None:
    """D-28, ahora sin tolerancia: la población es ΣH, entera, con cualquier `n`.
    Antes (densidad por celda, y luego por km con la celda del CBD excluida)
    refinar la grilla movía el total en unos pocos agentes."""
    lu = suelo_uniforme(1000)
    _, S, agentes = _agentes(n, 5.0, lu, demanda_sintetica)
    assert int(S.sum()) == 1000
    assert len(agentes) == 1000


def test_la_poblacion_es_simetrica(demanda_sintetica: DemandConfig) -> None:
    """La ciudad es simétrica por construcción: si una asimetría entra, que sea
    declarada y no un accidente de la oferta o del reparto."""
    for forma in ("uniforme", "normal"):
        lu = suelo_uniforme(2000).model_copy(update={"forma": forma})
        ciudad, S, agentes = _agentes(101, 10.0, lu, demanda_sintetica)
        n = ciudad.n_celdas
        assert np.array_equal(S, S[::-1])
        conteo = np.bincount([a.celda_origen for a in agentes], minlength=n)
        assert np.array_equal(conteo, conteo[::-1])


# ---------------------------------------------------------------------------
# Consistencia con el resto del núcleo (corren el MSA)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", (51, 101))
def test_todos_los_modulos_ven_el_mismo_cbd(n: int, demanda_sintetica: DemandConfig) -> None:
    """`CiudadLineal`, el acoplado (`L//2`) y las funciones de oferta —donde el
    tiempo de viaje es 0— tienen que coincidir en qué celda es el centro."""
    sim = SimulationConfig(
        city=CityConfig(n_celdas=n, largo_ciudad_km=5.0),
        supply=SupplyConfig(),
        demand=demanda_sintetica,
        max_iter=2,
        seed=1,
        assignment="expected",
    )
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, suelo_uniforme(500), tr, localizacion="original"):
        pass
    snap = tr.iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=n, largo_total_km=5.0)
    assert ciudad.cbd_index == n // 2 == int(np.argmin(snap.t_auto)) == int(np.argmin(snap.t_bici))


def test_la_grilla_converge() -> None:
    """La resolución NO es invariante —los cortes y escalones de la utilidad
    caen en una celda u otra según Δx— pero converge: el error entre 201 y 401
    celdas es menor que 0,15 pp y el siguiente refinamiento lo reduce."""

    def reparto(n: int) -> dict[str, float]:
        sim = _config_web().model_copy(
            update={"city": CityConfig(n_celdas=n, largo_ciudad_km=20.0)}
        )
        tr = ConvergenceTrace()
        for _ in iter_msa_desde_suelo(sim, _land_use_web(), tr, localizacion="original"):
            pass
        s = tr.iteraciones[-1].modal_split
        t = sum(s.values())
        return {m: 100.0 * v / t for m, v in s.items()}

    r = {n: reparto(n) for n in (201, 401, 801)}
    d1 = max(abs(r[201][m] - r[401][m]) for m in r[201])
    d2 = max(abs(r[401][m] - r[801][m]) for m in r[201])
    assert d1 < 0.15, (d1, r)
    assert d2 <= d1, (d1, d2, r)
