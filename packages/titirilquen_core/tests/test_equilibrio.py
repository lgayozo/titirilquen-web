"""El loop de equilibrio, por dentro.

`test_equilibrium_smoke` verificaba que una corrida de tres iteraciones no
explotara. `test_linea_base` fija los números de la ciudad real. Entre esos dos
quedaban sin cubrir las decisiones que hacen que el MSA sea lo que es: cuál de
los tres métodos de asignación se usa, qué pasa cuando un agente no tiene
ningún modo factible, si el criterio de corte realmente corta, y si la ruta que
usa la aplicación —la que deriva la población del uso de suelo— hace lo que
dice en sus dos modos de localización.

Ninguno de estos tests mide un número de calibración: eso es trabajo de
`test_linea_base`. Acá se verifican PROPIEDADES, que es lo que sobrevive a una
recalibración.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from titirilquen_core.config import (
    CityConfig,
    DemandConfig,
    SimulationConfig,
    SupplyConfig,
)
from titirilquen_core.equilibrium.msa import ConvergenceTrace, iter_msa, iter_msa_desde_suelo
from titirilquen_core.land_use.config import LandUseConfig


def _drena(sim: SimulationConfig, lu: LandUseConfig | None = None, **kw) -> ConvergenceTrace:
    tr = ConvergenceTrace()
    if lu is None:
        for _ in iter_msa(sim, tr):
            pass
    else:
        for _ in iter_msa_desde_suelo(sim, lu, tr, **kw):
            pass
    return tr


@pytest.fixture
def lu_chica() -> LandUseConfig:
    return LandUseConfig(H_por_estrato=(200, 500, 300), forma="normal", max_iter=200)


# ---------------------------------------------------------------------------
# Los tres métodos de asignación, bajo el loop
# ---------------------------------------------------------------------------
#
# `probabilidades_todo_o_nada` tiene sus propios tests unitarios, pero hasta
# ahora nunca se había ejercitado DENTRO del MSA — que es donde la decisión de
# `msa.py` ("todo_o_nada carga fraccionalmente igual que expected") podía estar
# equivocada sin que nada avisara.


@pytest.mark.parametrize("metodo", ["montecarlo", "expected", "todo_o_nada"])
def test_los_tres_metodos_corren_y_conservan_la_poblacion(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig, metodo: str
) -> None:
    sim_liviana.assignment = metodo
    sim_liviana.max_iter = 8
    sim_liviana.tolerance = 0.1
    tr = _drena(sim_liviana, lu_chica)

    assert tr.iteraciones, "el loop no emitió ninguna iteración"
    # Nadie se pierde ni se duplica: el reparto suma la población entera,
    # teletrabajadores incluidos.
    total = sum(tr.iteraciones[-1].modal_split.values())
    assert total == pytest.approx(len(tr.agentes), rel=1e-9)


def test_el_todo_o_nada_concentra_mas_que_el_logit(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """La propiedad que DEFINE al método: sin dispersión de gustos, cada grupo
    va entero a un modo, así que el reparto agregado es más concentrado.

    Se mide con la entropía del reparto modal. Es una propiedad estructural, no
    un número calibrado: sobrevive a que se recalibre el simulador.
    """

    def entropia(sim: SimulationConfig, metodo: str) -> float:
        sim.assignment = metodo
        sim.max_iter = 10
        sim.tolerance = 0.05
        split = _drena(sim, lu_chica).iteraciones[-1].modal_split
        viajes = np.array([v for m, v in split.items() if m != "Teletrabajo"], dtype=float)
        p = viajes[viajes > 0] / viajes.sum()
        return float(-(p * np.log(p)).sum())

    logit = entropia(sim_liviana.model_copy(deep=True), "expected")
    determinista = entropia(sim_liviana.model_copy(deep=True), "todo_o_nada")
    assert determinista < logit, (
        f"el todo-o-nada debería concentrar más el reparto: "
        f"entropía {determinista:.4f} vs logit {logit:.4f}"
    )


def test_promediar_flujos_llega_a_un_punto_fijo_parecido(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """El esquema estándar del MSA promedia FLUJOS; el nuestro promedia TIEMPOS.

    Existe sólo como instrumento de medición (ninguna ruta de producción lo
    activa), y este test fija lo que la auditoría de agosto de 2026 midió: los
    dos esquemas convergen al mismo punto fijo dentro de unos pocos puntos
    porcentuales. Si algún día divergen mucho, la elección de esquema dejó de
    ser inocua y hay que decidirla en serio.
    """
    sim_liviana.assignment = "expected"
    sim_liviana.max_iter = 12
    sim_liviana.tolerance = 0.05

    def reparto(promediar_flujos: bool) -> dict[str, float]:
        tr = _drena(sim_liviana.model_copy(deep=True), lu_chica, promediar_flujos=promediar_flujos)
        último = tr.iteraciones[-1]
        d = {
            "Auto": float(último.demanda_auto.sum()),
            "Metro": float(último.demanda_metro.sum()),
            "Bici": float(último.demanda_bici.sum()),
            "Caminata": float(último.demanda_caminata.sum()),
        }
        total = sum(d.values()) or 1.0
        return {k: 100 * v / total for k, v in d.items()}

    tiempos, flujos = reparto(False), reparto(True)
    peor = max(abs(tiempos[m] - flujos[m]) for m in tiempos)
    assert peor < 8.0, f"los dos esquemas divergen {peor:.1f} pp: {tiempos} vs {flujos}"


# ---------------------------------------------------------------------------
# Bordes del conjunto de elección
# ---------------------------------------------------------------------------


def test_un_modo_deshabilitado_no_recibe_demanda(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    sim_liviana.modos_habilitados = ("Auto", "Caminata")
    sim_liviana.assignment = "expected"
    tr = _drena(sim_liviana, lu_chica)
    último = tr.iteraciones[-1]
    assert último.demanda_metro.sum() == 0.0
    assert último.demanda_bici.sum() == 0.0
    assert último.demanda_auto.sum() > 0.0


def test_sin_modos_factibles_los_agentes_quedan_varados(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Con sólo el auto habilitado, quien no tiene auto no tiene NINGUNA
    alternativa: no viaja y no se le puede asignar un modo.

    Es el caso que produce `modo_elegido = None`, y el que obliga a que el
    reparto modal NO sume la población entera. Si el modelo colapsara ese caso a
    un modo cualquiera, estaría inventando viajes.
    """
    sim_liviana.modos_habilitados = ("Auto",)
    sim_liviana.assignment = "expected"
    tr = _drena(sim_liviana, lu_chica)

    varados = [a for a in tr.agentes if a.modo_elegido is None]
    assert varados, "con sólo auto habilitado debería haber agentes sin alternativa"
    assert all(not a.tiene_auto and not a.teletrabaja for a in varados)

    # Y no se cuelan en el reparto: la suma queda por debajo de la población.
    total = sum(tr.iteraciones[-1].modal_split.values())
    assert total == pytest.approx(len(tr.agentes) - len(varados), rel=1e-9)


# ---------------------------------------------------------------------------
# La ruta que usa la aplicación
# ---------------------------------------------------------------------------


def test_las_dos_localizaciones_dan_ciudades_distintas(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """`"equilibrio"` aplica el bid-rent (cada estrato se ubica donde puja más);
    `"original"` reparte la mezcla uniforme π_h en todas las celdas.

    Deben diferir: si dieran lo mismo, el equilibrio de pujas no estaría
    haciendo nada y el módulo de uso de suelo sería decorativo.
    """
    sim_liviana.assignment = "expected"
    eq = _drena(sim_liviana.model_copy(deep=True), lu_chica, localizacion="equilibrio")
    orig = _drena(sim_liviana.model_copy(deep=True), lu_chica, localizacion="original")

    # Misma población en ambos casos: cambia dónde vive cada estrato, no cuántos.
    assert len(eq.agentes) == len(orig.agentes)
    perfil_eq = eq.iteraciones[-1].demanda_auto
    perfil_orig = orig.iteraciones[-1].demanda_auto
    assert not np.allclose(perfil_eq, perfil_orig), (
        "las dos localizaciones dieron el mismo perfil de demanda"
    )


def test_la_demanda_por_estrato_cuadra_con_el_reparto(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """`demanda_estrato[estrato, modo, celda]` es el cubo del que salen los
    agregados de bienestar y el reparto espacial por estrato.

    Que le faltara al serializador de la API fue el bug de F0: el frontend
    recibía `undefined` y mostraba todos los indicadores en cero, sin error.
    Este test fija que el cubo exista y cuadre con el reparto agregado.
    """
    sim_liviana.assignment = "expected"
    tr = _drena(sim_liviana, lu_chica)
    cubo = tr.demanda_estrato
    assert cubo is not None, "el trace no trae demanda_estrato"
    assert cubo.shape == (3, 4, sim_liviana.city.n_celdas)

    split = tr.iteraciones[-1].modal_split
    viajes_split = sum(v for m, v in split.items() if m != "Teletrabajo")
    assert float(cubo.sum()) == pytest.approx(viajes_split, rel=1e-6)


def test_el_criterio_de_corte_corta_antes_del_tope(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Con una tolerancia realista el loop debe terminar por convergencia, no
    por agotar `max_iter`. Sólo se probaba con `tolerance=1e6`, que corta
    siempre y no verifica nada."""
    sim_liviana.assignment = "expected"
    sim_liviana.max_iter = 40
    sim_liviana.tolerance = 0.1
    tr = _drena(sim_liviana, lu_chica)

    assert tr.converged
    assert len(tr.iteraciones) < 40, "convergió recién en el tope: el criterio no cortó"
    assert tr.iteraciones[-1].residuo <= 0.1


def test_el_residuo_baja(sim_liviana: SimulationConfig, lu_chica: LandUseConfig) -> None:
    """No exige monotonía —el MSA puede rebotar en las primeras vueltas— pero sí
    que el final sea mucho mejor que el primer valor finito."""
    sim_liviana.assignment = "expected"
    sim_liviana.max_iter = 15
    sim_liviana.tolerance = 0.0  # sin corte: se ven todas
    residuos = [
        s.residuo for s in _drena(sim_liviana, lu_chica).iteraciones if np.isfinite(s.residuo)
    ]
    assert len(residuos) >= 3
    assert residuos[-1] < residuos[0] / 5


# ---------------------------------------------------------------------------
# Validadores de la configuración
# ---------------------------------------------------------------------------
#
# `config.py` tiene cuatro validadores y ninguno se ejercitaba. Son la única
# defensa contra una configuración que el frontend arme mal.


def test_faltan_estratos(demanda_calibrada: DemandConfig) -> None:
    incompleta = {1: demanda_calibrada.estratos[1], 2: demanda_calibrada.estratos[2]}
    with pytest.raises(ValidationError, match="Faltan estratos"):
        DemandConfig(estratos=incompleta)


def test_las_claves_de_estrato_llegan_como_texto_desde_json(
    demanda_calibrada: DemandConfig,
) -> None:
    """Un objeto JSON tiene claves string; `StratumId` es un entero. Sin la
    coerción, toda config que venga del navegador sería inválida."""
    crudo = {str(k): v.model_dump() for k, v in demanda_calibrada.estratos.items()}
    assert set(DemandConfig(estratos=crudo).estratos) == {1, 2, 3}


def test_los_shares_deben_sumar_uno(demanda_calibrada: DemandConfig) -> None:
    with pytest.raises(ValidationError):
        CityConfig(share_estratos=(0.5, 0.5, 0.5))


def test_hace_falta_al_menos_un_modo(demanda_calibrada: DemandConfig) -> None:
    with pytest.raises(ValidationError):
        SimulationConfig(
            city=CityConfig(),
            supply=SupplyConfig(),
            demand=demanda_calibrada,
            modos_habilitados=(),
        )


def test_la_grilla_no_puede_ser_absurda() -> None:
    with pytest.raises(ValidationError):
        CityConfig(n_celdas=3)


# ---------------------------------------------------------------------------
# Cortes de factibilidad configurables
# ---------------------------------------------------------------------------
#
# Eran constantes del núcleo hasta ago-2026. Al volverlos campos del schema hay
# dos cosas que vigilar: que el default siga siendo el supuesto histórico —o la
# línea base se movería sin que nadie lo decidiera— y que moverlos haga algo,
# porque un campo que se ignora es peor que no tenerlo.


def test_los_cortes_por_defecto_son_los_del_modelo() -> None:
    """El default sale de `constantes.py`: el número se declara una sola vez."""
    from titirilquen_core.config import GlobalConfig
    from titirilquen_core.constantes import CORTE_BICI_MIN, CORTE_CAMINATA_MIN

    g = GlobalConfig()
    assert g.corte_caminata_min == CORTE_CAMINATA_MIN
    assert g.corte_bici_min == CORTE_BICI_MIN


def test_bajar_el_corte_de_caminata_reduce_la_caminata(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Si el campo se ignorara, este test pasaría inadvertido: el reparto sería
    idéntico y nadie lo notaría hasta que alguien moviera el slider en el aula."""

    def caminata(corte: float) -> float:
        sim = sim_liviana.model_copy(deep=True)
        sim.demand.globales.corte_caminata_min = corte
        sim.max_iter = 6
        sim.tolerance = 0.1
        split = _drena(sim, lu_chica).iteraciones[-1].modal_split
        total = sum(split.values()) or 1
        return 100.0 * split.get("Caminata", 0) / total

    amplio, angosto = caminata(30.0), caminata(8.0)
    assert angosto < amplio, (
        f"bajar el corte de 30 a 8 min no redujo la caminata: {amplio:.2f}% -> {angosto:.2f}%"
    )


def test_el_corte_no_puede_ser_cero_ni_negativo(
    demanda_calibrada: DemandConfig,
) -> None:
    """`gt=0`: un corte de 0 dejaría la caminata infactible en toda la ciudad, que
    no es una configuración sino un error de tipeo."""
    from titirilquen_core.config import GlobalConfig

    for valor in (0, -5):
        with pytest.raises(ValidationError):
            GlobalConfig(corte_caminata_min=valor)
        with pytest.raises(ValidationError):
            GlobalConfig(corte_bici_min=valor)
