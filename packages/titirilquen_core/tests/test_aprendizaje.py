"""El módulo de aprendizaje: las dos ecuaciones del IBL y el motor de una persona.

Se testea lo que tiene respuesta cerrada —los pesos, W_k, Δ*, la invariancia de
escala— y se coteja la fórmula de P_post contra la simulación.
"""

from __future__ import annotations

import numpy as np
import pytest

from titirilquen_core.aprendizaje import (
    REPLICAS_MUESTRA,
    CasoBinario,
    ConfigPersona,
    cuota_por_persona,
    delta_critico,
    ejecutar_desde_equilibrio,
    ejecutar_persona,
    logistica,
    p_post_analitica,
    peso_shocks,
    pesos_ibl,
    phi,
    preparar_caso,
    simular,
    tiempo_percibido,
    ventanas,
)


@pytest.fixture(scope="module")
def ciudad_base():
    """La corrida por defecto de la app, igual que en test_linea_base."""
    from titirilquen_core.config import CityConfig, DemandConfig, SimulationConfig, SupplyConfig
    from titirilquen_core.land_use.config import LandUseConfig
    from titirilquen_core.presets import DEFAULT_STRATA

    sim = SimulationConfig(
        city=CityConfig(n_celdas=201, largo_ciudad_km=20),
        supply=SupplyConfig(),
        demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}),
        max_iter=150,
        tolerance=0.02,
        seed=42,
    )
    lu = LandUseConfig(
        H_por_estrato=(7200, 18000, 10800),
        forma="normal",
        oferta_sigma_frac=0.5,
        max_iter=2000,
    )
    return sim, lu


@pytest.fixture
def caso() -> CasoBinario:
    """Un caso sintético, para no depender del equilibrio de ninguna ciudad.

    ΔV = 0,5 útiles y |β| = 0,05 /min ⇒ A = 10 min y P* = Λ(0,5) = 0,6225.
    """
    return CasoBinario(
        tau=np.array([20.0, 30.0]),
        v_ref=np.array([-1.0, -1.5]),
        beta=-0.05,
    )


# --- Las dos ecuaciones del IBL -------------------------------------------------


def test_pesos_suman_uno_por_persona_y_modo():
    a = np.ones((3, 5, 2), dtype=bool)
    w = pesos_ibl(a, t=5, d=0.7)
    assert np.allclose(w.sum(axis=1), 1.0)


def test_sin_decaimiento_los_pesos_son_uniformes():
    a = np.ones((1, 4, 2), dtype=bool)
    w = pesos_ibl(a, t=4, d=0.0)
    assert np.allclose(w, 0.25)


def test_el_decaimiento_favorece_lo_reciente():
    a = np.ones((1, 4, 1), dtype=bool)
    w = pesos_ibl(a, t=4, d=2.0)[0, :, 0]
    assert np.all(np.diff(w) > 0), "el día más reciente va último y debe pesar más"
    # Antiguedades 4,3,2,1 elevadas a −2, normalizadas.
    esperado = np.array([4.0, 3.0, 2.0, 1.0]) ** -2
    assert np.allclose(w, esperado / esperado.sum())


def test_los_dias_no_elegidos_no_entran():
    a = np.array([[[True], [False], [True]]])
    x = np.array([[[10.0], [999.0], [20.0]]])
    b = tiempo_percibido(x, a, t=3, d=0.0)
    assert b[0, 0] == pytest.approx(15.0), "el 999 del día no elegido no debe contar"


def test_sin_experiencias_el_peso_es_cero():
    a = np.zeros((1, 3, 1), dtype=bool)
    assert np.all(pesos_ibl(a, t=3, d=0.5) == 0.0)


def test_en_t_cero_no_hay_pasado():
    with pytest.raises(ValueError):
        pesos_ibl(np.ones((1, 1, 1), dtype=bool), t=0, d=0.0)


# --- Las fórmulas cerradas ------------------------------------------------------


@pytest.mark.parametrize("k", [1, 2, 3, 5, 10])
def test_peso_de_los_shocks_sin_decaimiento(k: int):
    """Con d = 0 el peso es k/(k+1): k experiencias contra un prior."""
    assert peso_shocks(k, 0.0) == pytest.approx(k / (k + 1))


def test_el_peso_crece_con_la_recencia():
    assert peso_shocks(3, 1.28) > peso_shocks(3, 0.5) > peso_shocks(3, 0.0)


def test_el_shock_critico_deja_la_decision_en_la_moneda(caso: CasoBinario):
    """Δ* está definido justo para que P_post valga ½."""
    for k in (1, 3, 10):
        for d in (0.0, 0.5, 1.28):
            dc = delta_critico(caso, k, d)
            assert p_post_analitica(caso, k, d, dc) == pytest.approx(0.5)


def test_mas_experiencias_malas_bajan_el_umbral(caso: CasoBinario):
    umbrales = [delta_critico(caso, k, 0.5) for k in (1, 2, 3, 5, 10)]
    assert all(np.diff(umbrales) < 0)
    assert umbrales[0] > caso.ventaja_min, "con una sola experiencia hace falta más que A"


def test_la_ventaja_en_minutos(caso: CasoBinario):
    assert caso.ventaja_min == pytest.approx(10.0)
    assert caso.p_verdadera == pytest.approx(float(logistica(0.5)))
    assert caso.mejor == 0


# --- La escala ------------------------------------------------------------------


def test_reescalar_la_utilidad_no_mueve_la_ventaja_ni_el_umbral(caso: CasoBinario):
    """Multiplicar v_ref y β por k es equivalente a μ = k.

    A y Δ* quedan idénticos; lo que cambia es cuán abrupta es la respuesta.
    """
    k = 5.982
    escalado = CasoBinario(tau=caso.tau, v_ref=caso.v_ref * k, beta=caso.beta * k)
    assert escalado.ventaja_min == pytest.approx(caso.ventaja_min)
    for n in (1, 3, 10):
        assert delta_critico(escalado, n, 0.5) == pytest.approx(delta_critico(caso, n, 0.5))
    # P* sí cambia: el logit se afila.
    assert escalado.p_verdadera > caso.p_verdadera


def test_reescalar_afila_la_respuesta_al_shock(caso: CasoBinario):
    """P_post pasa de Λ(z) a Λ(k·z): el cruce por ½ no se mueve."""
    k = 4.0
    escalado = CasoBinario(tau=caso.tau, v_ref=caso.v_ref * k, beta=caso.beta * k)
    d, n = 0.5, 3
    z = caso.dv - abs(caso.beta) * peso_shocks(n, d) * 25.0
    assert p_post_analitica(escalado, n, d, 25.0) == pytest.approx(float(logistica(k * z)))


# --- La simulación --------------------------------------------------------------


def test_sin_ruido_ni_shock_la_eleccion_se_queda_en_la_verdadera(caso: CasoBinario):
    """Sin nada que aprender, la creencia nunca se mueve del prior."""
    r = simular(caso, d=0.5, replicas=50, dias=30)
    assert np.allclose(r.p, caso.p_verdadera)
    assert phi(caso, r.p, (1, 30)) == pytest.approx(1.0)


def test_la_formula_del_shock_predice_la_simulacion(caso: CasoBinario):
    """P_post analítica contra la simulada, donde hay muestra suficiente."""
    d = 0.5
    for k in (1, 3):
        for delta in (5.0, 15.0):
            r = simular(caso, d=d, k=k, delta=delta, replicas=4000, dias=60)
            assert r.llegan_a_k > 0.5
            sim = float(np.nanmean(r.p_post))
            assert sim == pytest.approx(p_post_analitica(caso, k, d, delta), abs=0.01)


def test_un_shock_grande_trunca_la_exposicion(caso: CasoBinario):
    """Con shocks grandes la persona abandona antes de recibirlos todos."""
    suave = simular(caso, d=0.5, k=10, delta=5.0, replicas=300, dias=120)
    brutal = simular(caso, d=0.5, k=10, delta=200.0, replicas=300, dias=120)
    assert brutal.llegan_a_k < suave.llegan_a_k


def test_el_ruido_dana_segun_en_que_modo_este(caso: CasoBinario):
    """La asimetría del hot stove: el signo depende de DÓNDE está el ruido.

    Ojo con la intuición de que más varianza siempre acerca la elección a la
    moneda. Eso vale para la creencia, pero el efecto neto no tiene signo
    propio: el aprendizaje hace abandonar lo que sea variable. Si lo variable
    es el modo bueno, Φ cae; si es el malo, Φ sube por encima de 1.
    """
    comun = {"d": 0.5, "replicas": 400, "dias": 120}
    ventana = (61, 120)
    en_el_mejor = simular(caso, sigma=(60.0, 0.0), **comun)
    en_el_peor = simular(caso, sigma=(0.0, 60.0), **comun)
    assert phi(caso, en_el_mejor.p, ventana) < 1.0
    assert phi(caso, en_el_peor.p, ventana) > 1.0
    assert phi(caso, en_el_mejor.p, ventana) < phi(caso, en_el_peor.p, ventana)


def test_la_corrida_es_reproducible(caso: CasoBinario):
    a = simular(caso, d=0.5, sigma=(20.0, 20.0), replicas=30, dias=20, semilla=7)
    b = simular(caso, d=0.5, sigma=(20.0, 20.0), replicas=30, dias=20, semilla=7)
    assert np.array_equal(a.p, b.p)


# --- Validación -----------------------------------------------------------------


def test_beta_positivo_no_pasa():
    with pytest.raises(ValueError, match="beta"):
        CasoBinario(tau=np.array([1.0, 2.0]), v_ref=np.array([0.0, 0.0]), beta=0.05)


def test_formas_equivocadas_no_pasan():
    with pytest.raises(ValueError, match="forma"):
        CasoBinario(tau=np.array([1.0]), v_ref=np.array([0.0, 0.0]), beta=-0.05)


def test_la_ventana_tiene_que_caber(caso: CasoBinario):
    r = simular(caso, d=0.5, replicas=5, dias=10)
    with pytest.raises(ValueError, match="ventana"):
        cuota_por_persona(r.p, (5, 99))


# --- La puerta desde la interfaz ------------------------------------------------


def test_las_ventanas_reproducen_las_publicadas():
    """Con 250 días tienen que dar exactamente las de los informes."""
    assert ventanas(250) == {"corto": (1, 10), "medio": (11, 50), "largo": (51, 250)}


def test_las_ventanas_se_adaptan_a_un_horizonte_corto():
    """Con el horizonte recortado de la app siguen siendo tres, sin solaparse."""
    for dias in (10, 25, 50, 100):
        v = ventanas(dias)
        assert v["corto"][0] == 1
        assert v["largo"][1] == dias
        assert v["corto"][1] + 1 == v["medio"][0]
        assert v["medio"][1] + 1 == v["largo"][0]
        assert all(a <= b for a, b in v.values())


def test_la_condicion_de_ruido_decide_donde_cae():
    assert ConfigPersona(condicion="ambos", sigma_min=30.0).sigmas() == (30.0, 30.0)
    assert ConfigPersona(condicion="solo_mejor", sigma_min=30.0).sigmas() == (30.0, 0.0)
    assert ConfigPersona(condicion="solo_peor", sigma_min=30.0).sigmas() == (0.0, 30.0)
    assert ConfigPersona().sigmas() == (0.0, 0.0)


def test_el_tratamiento_de_shock_va_completo_o_no_va():
    with pytest.raises(ValueError, match="k_shocks"):
        ConfigPersona(k_shocks=3)
    with pytest.raises(ValueError, match="k_shocks"):
        ConfigPersona(delta_min=20.0)


def test_ejecutar_sin_tratamiento_da_phi_uno(ciudad_base):
    """De punta a punta: sin nada que aprender, Φ = 1 en las tres ventanas."""
    sim, lu = ciudad_base
    r = ejecutar_desde_equilibrio(
        sim, lu, ConfigPersona(estrato=2, celda=135, d=1.28, dias=40, replicas=50)
    )
    assert r["caso"]["mejor"] == "Auto"
    # 33,37 hasta nov-2026; se movió con el consumo único de bencina (el auto
    # paga los litros que quema, no un costo fijo por km) a 34,69, y con los
    # VoT en razón 4 : 2 : 1 a 34,81.
    assert r["caso"]["ventaja_min"] == pytest.approx(34.81, abs=0.05)
    for v in r["ventanas"].values():
        assert v["phi"] == pytest.approx(1.0)


def test_ejecutar_reporta_el_umbral_del_shock(ciudad_base):
    """Con tratamiento aparece el bloque analítico, y cuadra con la simulación."""
    sim, lu = ciudad_base
    cfg = ConfigPersona(
        estrato=2, celda=135, d=1.28, k_shocks=3, delta_min=60.0, dias=40, replicas=600
    )
    r = ejecutar_desde_equilibrio(sim, lu, cfg)
    s = r["shock"]
    assert s["w_k"] == pytest.approx(peso_shocks(3, 1.28))
    assert s["delta_critico_min"] == pytest.approx(r["caso"]["ventaja_min"] / s["w_k"])
    assert s["llegan_a_k"] > 0.5
    assert s["p_post_simulada"] == pytest.approx(s["p_post_analitica"], abs=0.03)


def test_una_celda_fuera_de_la_ciudad_no_pasa(ciudad_base):
    sim, lu = ciudad_base
    with pytest.raises(ValueError, match="celda"):
        ejecutar_desde_equilibrio(sim, lu, ConfigPersona(celda=9999))


def test_preparar_el_caso_una_vez_y_correr_muchos(ciudad_base):
    """El caso se prepara una vez; los experimentos corren sobre él.

    Es la razón de partir la API: en Pyodide el equilibrio cuesta un minuto y
    la simulación un par de segundos.
    """
    sim, lu = ciudad_base
    caso = preparar_caso(sim, lu, estrato=2, celda=135)
    assert caso["mejor"] == "Auto"
    assert caso["margen_phi"] == pytest.approx(caso["p_verdadera"] - 0.5)

    sin = ejecutar_persona(caso, ConfigPersona(estrato=2, celda=135, dias=30, replicas=40))
    con = ejecutar_persona(
        caso,
        ConfigPersona(
            estrato=2,
            celda=135,
            dias=30,
            replicas=40,
            condicion="solo_mejor",
            sigma_min=80.0,
        ),
    )
    assert sin["caso"] == con["caso"], "el mismo caso, sin recalcular el equilibrio"
    assert sin["ventanas"]["largo"]["phi"] == pytest.approx(1.0)
    assert con["ventanas"]["largo"]["phi"] < sin["ventanas"]["largo"]["phi"]


def test_el_margen_de_phi_avisa_cuando_la_ventaja_es_chica(ciudad_base):
    """Una celda casi indiferente deja el denominador de Φ pegado a cero."""
    sim, lu = ciudad_base
    cerca = preparar_caso(sim, lu, estrato=2, celda=135)
    assert abs(cerca["margen_phi"]) > 0.2, "C2 tiene ventaja de sobra"


def test_el_caso_con_tiempos_dados_no_resuelve_la_ciudad(ciudad_base):
    """Reusar los tiempos del equilibrio da el MISMO caso, sin correr el MSA.

    Es lo que hace usable la página: el MSA cuesta más de un minuto en Pyodide
    y el experimento, dos décimas.
    """
    import time

    from titirilquen_core.equilibrium.msa import run_msa

    sim, lu = ciudad_base
    s = run_msa(sim, lu, localizacion="equilibrio").iteraciones[-1]
    celda = 135
    tiempos = {
        "auto_total": float(s.t_auto[celda]),
        "bici_total": float(s.t_bici[celda]),
        "bici_libre": float(s.t_bici_libre[celda]),
        "tren_acceso": float(s.t_tren_acceso[celda]),
        "tren_espera": float(s.t_tren_espera[celda]),
        "tren_viaje": float(s.t_tren_viaje[celda]),
    }
    t0 = time.perf_counter()
    rapido = preparar_caso(sim, lu, estrato=2, celda=celda, tiempos=tiempos)
    con_tiempos = time.perf_counter() - t0

    t0 = time.perf_counter()
    lento = preparar_caso(sim, lu, estrato=2, celda=celda)
    con_msa = time.perf_counter() - t0

    assert rapido == lento, "el atajo tiene que dar exactamente el mismo caso"
    assert con_tiempos < con_msa / 5, f"{con_tiempos:.3f} s contra {con_msa:.3f} s"


def _dict_de(caso: CasoBinario) -> dict:
    """El `CasoDict` que espera `ejecutar_persona`, desde el caso sintético."""
    return {
        "estrato": 2,
        "celda": 100,
        "modos": ["A", "B"],
        "mejor": "A" if caso.mejor == 0 else "B",
        "tau": caso.tau.tolist(),
        "v_ref": caso.v_ref.tolist(),
        "beta": caso.beta,
        "dv": caso.dv,
        "ventaja_min": caso.ventaja_min,
        "p_verdadera": caso.p_verdadera,
        "margen_phi": caso.p_verdadera - 0.5,
    }


def test_p_replicas_son_las_trayectorias_individuales(caso: CasoBinario) -> None:
    """El promedio es suave; cada réplica es una escalera. Ambos van al contrato.

    Es el contraste pedagógico de la figura: si `p_replicas` trajera otra cosa
    —o quedara recortada al número equivocado de días— el gráfico de «una
    réplica» mentiría justo donde queremos ser precisos.
    """
    cfg = ConfigPersona(dias=30, replicas=50, semilla=7, d=0.0, k_shocks=1, delta_min=60.0)
    res = ejecutar_persona(_dict_de(caso), cfg)

    assert len(res["p_replicas"]) == REPLICAS_MUESTRA
    assert all(len(fila) == cfg.dias for fila in res["p_replicas"])

    r = simular(
        caso,
        d=cfg.d,
        k=cfg.k_shocks,
        delta=cfg.delta_min,
        replicas=cfg.replicas,
        dias=cfg.dias,
        semilla=cfg.semilla,
    )
    assert res["p_replicas"][0] == pytest.approx(r.p[0], abs=1e-5)
    assert res["s_por_dia"] == pytest.approx(r.p.mean(axis=0), abs=1e-5)


def test_p_replicas_no_excede_las_replicas_corridas(caso: CasoBinario) -> None:
    """Con menos réplicas que la muestra, se mandan todas y no se inventa ninguna."""
    cfg = ConfigPersona(dias=20, replicas=5, semilla=7)
    res = ejecutar_persona(_dict_de(caso), cfg)
    assert len(res["p_replicas"]) == 5


def test_una_replica_es_escalonada_y_el_promedio_no(caso: CasoBinario) -> None:
    """Con un solo shock, el día 2 sólo hay dos poblaciones: golpeadas y no.

    Es la prueba de que el suavizado del promedio viene de la agregación y no
    del modelo: el shock cae el día en que la persona ELIGE el modo mejor, que
    no es el mismo día en todas. Si esto empezara a dar muchos valores
    distintos, el tratamiento ya no estaría entrando de forma discreta.
    """
    r = simular(caso, d=0.0, k=1, delta=60.0, replicas=400, dias=30, semilla=7)
    assert len(np.unique(r.p[:, 1].round(6))) == 2
    assert len(np.unique(r.p[:, 29].round(6))) > 5
