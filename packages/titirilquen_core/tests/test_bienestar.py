"""El excedente del consumidor y los agregados de bienestar.

`bienestar.py` mide el excedente con el logsum, que es el `E[max]` del agente
que el logit describe. Acá se verifican PROPIEDADES, no niveles calibrados: los
números de la ciudad real son trabajo de `test_linea_base`.

Hasta nov-2026 había una segunda medida —la utilidad máxima, emparejada con la
carga determinística— y estos tests vigilaban el emparejamiento. Se retiró con
ese método: queda un solo modelo de comportamiento y una sola medida.
"""

from __future__ import annotations

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


def _agregados(sim: SimulationConfig, lu: LandUseConfig):
    sim.max_iter = 8
    sim.tolerance = 0.1
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu, trace):
        pass
    agg = calcular_agregados(sim, trace)
    assert agg is not None, "la corrida no produjo agregados"
    return agg


def test_el_bienestar_social_se_descompone(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """`W = excedente + recaudación − costo del operador`, término a término."""
    agg = _agregados(sim_liviana, lu_chica)
    esperado = (
        agg["excedente_total_clp"]
        + agg["recaudacion_parking_clp"]
        + agg["recaudacion_peaje_clp"]
        + agg["recaudacion_tarifa_clp"]
        + agg["recaudacion_combustible_clp"]
        - agg["costo_operador_clp"]
    )
    assert agg["bienestar_social_clp"] == pytest.approx(esperado, rel=1e-9)


def test_el_peaje_es_transferencia(sim_liviana: SimulationConfig, lu_chica: LandUseConfig) -> None:
    """D7: lo que paga el automovilista en peaje lo recauda la ciudad, así que
    entra al bienestar social como recaudación, igual que el parking."""
    sim_liviana.demand.globales.peaje_km = 100.0
    agg = _agregados(sim_liviana, lu_chica)
    assert agg["recaudacion_peaje_clp"] > 0
    esperado = (
        agg["excedente_total_clp"]
        + agg["recaudacion_parking_clp"]
        + agg["recaudacion_peaje_clp"]
        + agg["recaudacion_tarifa_clp"]
        + agg["recaudacion_combustible_clp"]
        - agg["costo_operador_clp"]
    )
    assert agg["bienestar_social_clp"] == pytest.approx(esperado, rel=1e-9)


def test_el_factor_dia_punta_mueve_el_subsidio_y_no_el_bienestar(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """D12: el bienestar es de la hora punta; el factor día/punta sólo lleva el
    costo a base diaria para la pregunta de autofinanciamiento."""
    a = _agregados(sim_liviana.model_copy(deep=True), lu_chica)
    sim3 = sim_liviana.model_copy(deep=True)
    sim3.supply.train.factor_dia_punta = 3.0
    b = _agregados(sim3, lu_chica)
    assert b["bienestar_social_clp"] == pytest.approx(a["bienestar_social_clp"], rel=1e-9)
    assert b["costo_operador_clp"] == pytest.approx(a["costo_operador_clp"], rel=1e-9)
    f = sim_liviana.supply.train.factor_dia_punta
    assert b["subsidio_metro_clp"] - a["subsidio_metro_clp"] == pytest.approx(
        (3.0 - f) * a["costo_operador_clp"], rel=1e-9
    )


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

    agg = _agregados(sim_liviana, lu_chica)
    for h in ESTRATOS:
        b_t = abs(sim_liviana.demand.estratos[int(h)].betas.b_tiempo_viaje)
        lam_social = b_t * 60 / VOT_SOCIAL_CLP_HORA
        esperado = agg["logsum_por_estrato"][h] / lam_social
        assert agg["excedente_social_por_estrato_clp"][h] == pytest.approx(esperado, rel=1e-9)


def test_el_social_y_el_conductual_no_coinciden(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Guard: si dieran lo mismo la tercera columna seria decorativa, y el
    hallazgo sobre el signo de Downs-Thomson no tendria sentido."""
    agg = _agregados(sim_liviana, lu_chica)
    assert agg["excedente_social_total_clp"] != pytest.approx(agg["excedente_total_clp"], rel=1e-6)


# ---------------------------------------------------------------------------
# El reparto modal
# ---------------------------------------------------------------------------


def test_los_viajes_por_modo_suman_los_viajeros(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """`Σ_m viajes_por_modo[m] = viajeros`, exactamente.

    Es la propiedad que hace comparable el reparto con el resto de la tabla: si
    el share se calculara sobre otro denominador —el conteo de agentes del
    snapshot, que incluye teletrabajo— los porcentajes no cuadrarían con el
    tiempo medio ni con el costo generalizado, que se promedian sobre ESTOS
    viajeros.
    """
    agg = _agregados(sim_liviana, lu_chica)
    assert set(agg["viajes_por_modo"]) == set(MODOS)
    assert sum(agg["viajes_por_modo"].values()) == pytest.approx(agg["viajeros"], rel=1e-12)


def test_el_reparto_por_estrato_agrega_al_de_ciudad(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """`Σ_h viajes_por_modo_estrato[h][m] = viajes_por_modo[m]`, modo a modo.

    Es la propiedad que hace que las dos tablas de la pantalla —el reparto de
    ciudad completa y el desagregado por estrato— sean el MISMO reparto visto a
    dos niveles, y no dos cálculos que hay que creer que coinciden.
    """
    agg = _agregados(sim_liviana, lu_chica)
    for m in MODOS:
        suma = sum(agg["viajes_por_modo_estrato"][h][m] for h in ESTRATOS)
        assert suma == pytest.approx(agg["viajes_por_modo"][m], rel=1e-12), f"modo {m}"


def test_los_tiempos_medios_reconstruyen_el_total(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """`Σ_m viajes_m · t̄_m = Σ_h viajeros_h · t̄_h = tiempo_total`: los tiempos
    medios por modo y por estrato ponderan con la misma demanda esperada que el
    total, no con un sorteo de agentes (auditoría C, ítem 9)."""
    agg = _agregados(sim_liviana, lu_chica)
    por_modo = sum(agg["viajes_por_modo"][m] * agg["tiempo_medio_por_modo_min"][m] for m in MODOS)
    por_estrato = sum(
        sum(agg["viajes_por_modo_estrato"][h].values()) * agg["tiempo_medio_por_estrato_min"][h]
        for h in ESTRATOS
    )
    assert por_modo == pytest.approx(agg["tiempo_total_min"], rel=1e-12)
    assert por_estrato == pytest.approx(agg["tiempo_total_min"], rel=1e-12)


def test_el_reparto_modal_reacciona_a_la_politica(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Guard: encarecer el metro tiene que mover gente fuera del metro.

    Sin esto, un reparto que quedara pegado en cero o en una constante pasaría
    todos los tests de arriba —suma y claves— sin medir nada.
    """
    base = _agregados(sim_liviana, lu_chica)
    sim_liviana.demand.globales.costo_tarifa_metro *= 6
    caro = _agregados(sim_liviana, lu_chica)
    assert caro["viajes_por_modo"]["Metro"] < base["viajes_por_modo"]["Metro"]


def test_los_varados_se_cuentan_y_no_entran_al_agregado(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """D14: con sólo el auto habilitado, quien no tiene auto queda varado.

    El conteo tiene que ser exactamente esos agentes, en los tres métodos, y
    ninguno de ellos puede aparecer en `viajeros`. Con todos los modos la base
    no deja a nadie varado: el campo no es un ruido que siempre vale algo.
    """
    assert _agregados(sim_liviana, lu_chica)["varados"] == 0
    sim_liviana.modos_habilitados = ("Auto",)
    sim_liviana.max_iter = 8
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim_liviana, lu_chica, trace):
        pass
    agg = calcular_agregados(sim_liviana, trace)
    assert agg is not None
    sin_auto = sum(1 for a in trace.agentes if not a.teletrabaja and not a.tiene_auto)
    con_auto = sum(1 for a in trace.agentes if not a.teletrabaja and a.tiene_auto)
    assert sin_auto > 0
    assert agg["varados"] == sin_auto
    assert agg["viajeros"] == pytest.approx(con_auto, rel=1e-9)


# ---------------------------------------------------------------------------
# D-36 / D-37: costo del operador y costo generalizado
# ---------------------------------------------------------------------------


def test_un_metro_sin_emisiones_sigue_costando_operarlo(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """D-36: los tren-km salen del servicio (f_op · línea · 2), no de las
    emisiones. Con factor de emisión 0 el costo del operador no puede caer."""
    con = _agregados(sim_liviana.model_copy(deep=True), lu_chica)
    sim0 = sim_liviana.model_copy(deep=True)
    sim0.demand.globales.factor_emision_metro_tren_km = 0.0
    sin = _agregados(sim0, lu_chica)
    assert sin["tren_km_hora"] > 0
    assert sin["tren_km_hora"] == pytest.approx(con["tren_km_hora"], rel=1e-9)
    assert sin["costo_operador_clp"] == pytest.approx(con["costo_operador_clp"], rel=1e-9)


def test_los_minutos_ponderados_pesan_espera_y_acceso() -> None:
    """D-37: el costo generalizado no es «minutos × VoT» plano."""
    from titirilquen_core.bienestar import minutos_ponderados
    from titirilquen_core.demand.utility import TiemposObservados

    t = TiemposObservados(
        auto_total=12.0,
        bici_total=20.0,
        bici_libre=20.0,
        tren_acceso=6.0,
        tren_espera=4.0,
        tren_viaje=15.0,
    )
    assert minutos_ponderados("Auto", t, 30.0, w_espera=2, w_acceso=2, w_caminata=1.7) == 12.0
    assert minutos_ponderados("Bici", t, 30.0, w_espera=2, w_acceso=2, w_caminata=1.7) == 20.0
    assert (
        minutos_ponderados("Metro", t, 30.0, w_espera=2, w_acceso=2, w_caminata=1.7) == 15 + 8 + 12
    )
    assert minutos_ponderados("Caminata", t, 30.0, w_espera=2, w_acceso=2, w_caminata=1.7) == 51.0
    # con ponderadores 1 vuelve a los minutos físicos
    assert minutos_ponderados("Metro", t, 30.0, w_espera=1, w_acceso=1, w_caminata=1) == 25.0


def test_el_costo_social_supera_al_de_minutos_planos(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """D-37: con espera y acceso ponderados ×2 (SNI), el costo social agregado
    es mayor que valorar todos los minutos igual — salvo que nadie use metro."""
    from titirilquen_core.constantes import VOT_SOCIAL_CLP_HORA

    agg = _agregados(sim_liviana.model_copy(deep=True), lu_chica)
    if agg["viajes_por_modo"]["Metro"] > 0:
        # cota inferior: minutos planos × VoT social (sin dinero) < social reportado
        plano = agg["tiempo_total_min"] / 60 * VOT_SOCIAL_CLP_HORA
        assert agg["costo_generalizado_social_clp"] > plano


def test_el_costo_de_recursos_se_descompone(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """El total es exactamente la suma de sus cinco partes.

    La descomposición es lo que la interfaz muestra en el «saber más»: si el
    total dejara de ser la suma de sus partes, la explicación mentiría.
    """
    agg = _agregados(sim_liviana, lu_chica)
    esperado = (
        agg["recursos_tiempo_clp"]
        + agg["recursos_combustible_clp"]
        + agg["recursos_otros_operacion_clp"]
        + agg["costo_operador_clp"]
        + agg["costo_co2_clp"]
    )
    assert agg["costo_recursos_clp"] == pytest.approx(esperado, rel=1e-12)
    for parte in ("recursos_tiempo_clp", "recursos_combustible_clp", "costo_co2_clp"):
        assert agg[parte] > 0


def test_el_combustible_va_a_precio_social_y_no_al_que_paga_el_conductor(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Duplicar el precio de mercado cambia la elección de modo, pero el
    costo de recursos por auto-km no puede duplicarse: los mismos litros se
    valoran a 760 $/l, que no mira lo que paga el usuario."""
    caro = sim_liviana.model_copy(deep=True)
    caro.demand.globales.precio_combustible_clp_l *= 2
    sin = _agregados(sim_liviana, lu_chica)
    con = _agregados(caro, lu_chica)
    por_km_sin = sin["recursos_combustible_clp"] / sin["auto_km_hora"]
    por_km_con = con["recursos_combustible_clp"] / con["auto_km_hora"]
    assert por_km_con == pytest.approx(por_km_sin, rel=0.15)
    # entre el mínimo (62,4 ml/km) y el máximo (205,6 ml/km) de la tabla
    assert 0.0624 * 760 <= por_km_sin <= 0.2056 * 760


def test_los_precios_sociales_se_leen_de_la_configuracion(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Son configuración porque cambian cada año: duplicar el precio del
    carbono duplica su costo, y NO mueve el equilibrio (la partición modal),
    porque ningún precio social entra a la elección de modo."""
    otro = sim_liviana.model_copy(deep=True)
    otro.precios_sociales.carbono_clp_t *= 2
    otro.precios_sociales.vst_viaje_clp_h *= 2
    base = _agregados(sim_liviana, lu_chica)
    con = _agregados(otro, lu_chica)
    assert con["viajes_por_modo"] == base["viajes_por_modo"]
    assert con["costo_co2_clp"] == pytest.approx(2 * base["costo_co2_clp"])
    assert con["recursos_tiempo_clp"] == pytest.approx(2 * base["recursos_tiempo_clp"])
    assert con["recursos_combustible_clp"] == pytest.approx(base["recursos_combustible_clp"])


def test_el_impuesto_a_la_bencina_es_transferencia(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """El consumo es uno solo: de los mismos litros salen lo pagado (precio
    de mercado), el recurso (precio social) y el impuesto (la diferencia), así
    que la cuenta cierra exacta. Y el impuesto resulta de los dos precios: si
    el de mercado iguala al social, no hay impuesto."""
    agg = _agregados(sim_liviana, lu_chica)
    g = sim_liviana.demand.globales
    ps = sim_liviana.precios_sociales
    litros = agg["litros_combustible_hora"]
    assert litros > 0
    assert agg["pago_combustible_clp"] == pytest.approx(litros * g.precio_combustible_clp_l)
    assert agg["recursos_combustible_clp"] == pytest.approx(litros * ps.combustible_auto_clp_l)
    assert agg["recaudacion_combustible_clp"] == pytest.approx(
        agg["pago_combustible_clp"] - agg["recursos_combustible_clp"]
    )

    sin = sim_liviana.model_copy(deep=True)
    sin.demand.globales.precio_combustible_clp_l = ps.combustible_auto_clp_l
    assert _agregados(sin, lu_chica)["recaudacion_combustible_clp"] == pytest.approx(0)


def test_la_congestion_encarece_la_bencina_del_viaje() -> None:
    """El mismo viaje, más lento, quema más: a 15 km/h de media un auto gasta
    más litros que a 30. Es lo que el costo fijo por km no podía decir."""
    from titirilquen_core.config import GlobalConfig
    from titirilquen_core.demand.utility import costo_monetario_auto, litros_viaje_auto

    g = GlobalConfig()
    fluido = litros_viaje_auto(5.0, 10.0, g)  # 30 km/h
    lento = litros_viaje_auto(5.0, 20.0, g)  # 15 km/h
    assert fluido == pytest.approx(5.0 * 81.3 / 1000)
    assert lento > fluido
    assert costo_monetario_auto(5.0, 20.0, g) > costo_monetario_auto(5.0, 10.0, g)


def test_los_otros_costos_y_el_co2_entran_al_costo_de_recursos(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    agg = _agregados(sim_liviana, lu_chica)
    assert agg["costo_co2_clp"] > 0
    assert agg["recursos_otros_operacion_clp"] == pytest.approx(
        agg["auto_km_hora"] * 41.40, rel=1e-3
    )


def test_el_peaje_no_entra_al_costo_de_recursos(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """La diferencia de fondo entre los dos enfoques.

    El peaje es una transferencia: sale de un bolsillo y entra a otro sin
    consumir nada. Tiene que mover el costo generalizado —que es lo que el
    usuario percibe— y NO el costo de recursos, salvo por lo que cambie el
    comportamiento. Para aislarlo se compara contra una corrida con el mismo
    reparto modal: con el peaje puesto sobre la MISMA asignación, el costo de
    recursos sólo puede moverse por tiempo y bencina.
    """
    sin = _agregados(sim_liviana, lu_chica)
    sim_liviana.demand.globales.peaje_km = 100.0
    con = _agregados(sim_liviana, lu_chica)

    assert con["recaudacion_peaje_clp"] > 0
    # el percibido lleva el peaje dentro; el de recursos no tiene dónde ponerlo
    assert con["costo_generalizado_percibido_clp"] > sin["costo_generalizado_percibido_clp"]
    recaudado = con["recaudacion_peaje_clp"]
    movido = abs(con["costo_recursos_clp"] - sin["costo_recursos_clp"])
    assert movido < recaudado, (
        "el costo de recursos no puede moverse tanto como lo recaudado: "
        "eso significaría que la transferencia se está contando como recurso"
    )


def test_el_tiempo_de_recursos_va_al_vot_de_norma(
    sim_liviana: SimulationConfig, lu_chica: LandUseConfig
) -> None:
    """Al VST, no al VoT conductual: en recursos un minuto vale lo mismo para
    todos. Se verifica subiendo el VoT conductual de un estrato —que no debe
    mover el tiempo de recursos— y comprobando que sí mueve el percibido."""
    sin = _agregados(sim_liviana, lu_chica)
    sim_liviana.demand.estratos[1].betas.b_costo *= 0.5  # duplica el VoT del estrato alto
    con = _agregados(sim_liviana, lu_chica)

    assert con["vot_por_estrato_clp_hora"]["1"] > sin["vot_por_estrato_clp_hora"]["1"]
    assert con["costo_generalizado_percibido_clp"] != pytest.approx(
        sin["costo_generalizado_percibido_clp"], rel=1e-6
    )
    # El reparto modal cambia (el β entra a la utilidad), así que el tiempo de
    # recursos se mueve algo; lo que NO puede pasar es que siga al VoT.
    assert con["recursos_tiempo_clp"] == pytest.approx(sin["recursos_tiempo_clp"], rel=0.05)
