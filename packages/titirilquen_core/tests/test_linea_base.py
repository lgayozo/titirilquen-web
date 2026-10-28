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
    #  4. mu = 1/√VIAJES_MES ≈ 0,151 (ruido acumulado en el mes, no el de un viaje):
    #     la ciudad de partida pasa de Theil 0,75 a 0,16 —el estrato bajo ya no
    #     queda confinado a la periferia (5,5 km en vez de 6,7)— y sus viajes
    #     más cortos migran del metro a la caminata y la bici: metro −3,0 pp,
    #     caminata +1,65, bici +1,10, auto +0,20. `original` sigue intacta.
    #  5. D-42: la accesibilidad del suelo standalone (y del arranque del
    #     acoplado) pasa del «flujo libre» con 10 min de acceso fijos a la red
    #     VACÍA configurada (estaciones reales, frecuencia mínima). Mueve poco:
    #     metro −0,11, caminata +0,07, bici +0,04, auto −0,03.
    #  6. rho = 0 (2026-09-15): la penalización por densidad, sin fuente, deja
    #     de actuar por defecto y el suelo queda en Alonso puro (Theil 0,24 en
    #     vez de 0,17, el alto a 1,9 km en vez de 2,2). Los viajes cortos del
    #     centro migran a metro y auto: metro +0,60, caminata −0,31, bici −0,10,
    #     auto −0,09; una iteración más del MSA. `original` sigue intacta.
    #  7. BPR del auto = FHWA, 0,15 / 4 en vez de 0,8 / 2 heredados (2026-09-15).
    #     Bajo capacidad la curva castiga menos y el auto gana: original auto
    #     +1,08, metro −0,81, bici −0,22, caminata −0,06; equilibrio auto +0,78,
    #     metro −0,52, bici −0,19, caminata −0,07. Mismas iteraciones.
    #  8. Ciclovía de 4.000 bici/h en vez de 2.500 (2026-09-15): la ciclovía deja
    #     de ser la restricción que ataba la base (v/c 1,7 → 1,3, la misma que
    #     la vía) y la bici empata con el metro. Original: bici +4,65, metro
    #     −3,89, auto −0,53, caminata −0,24; equilibrio: bici +4,88, metro −4,27,
    #     auto −0,48, caminata −0,13. El MSA cierra en 7 iteraciones en ambas.
    #  9. Parking por TOUR, no por viaje (2026-10-13, decisión de Leandro):
    #     `costo_parking` = 2.000 por día y a cada viaje de ida le toca la mitad
    #     (`VIAJES_POR_TOUR`). Antes se cobraba entero en los 44 viajes del mes,
    #     dos veces por día. El auto se abarata 1.000 $ por viaje y gana mucho:
    #     original auto +5,52, metro −3,35, bici −1,30, caminata −0,86;
    #     equilibrio auto +5,79, metro −3,68, bici −1,37, caminata −0,78, y una
    #     iteración más del MSA (8).
    # 10. BPR del auto sobre la capacidad PRÁCTICA, 0,8·C (2026-10-13, D6 de la
    #     auditoría, decisión de Leandro): 0,15/4 se estimó con la capacidad de
    #     nivel de servicio C, no con la real de Greenshields (Boyles, p. 102).
    #     El auto se congestiona antes y pierde: original auto −1,17, metro
    #     +0,83, bici +0,25, caminata +0,10, y una iteración más (8);
    #     equilibrio auto −0,94, metro +0,54, bici +0,29, caminata +0,11,
    #     mismas iteraciones.
    # 11. D8 + D9 de la auditoría (2026-10-13, decisiones de Leandro). D9: los
    #     escalones 10/20/30 y el corte de 45 min de la bici se evalúan sobre
    #     el tiempo de red VACÍA, no el congestionado; la congestión ya no
    #     castiga dos veces y la bici gana al metro: original bici +2,12, metro
    #     −2,09; equilibrio bici +2,71, metro −2,75 (medidos con la regla de
    #     parada vieja). D8: la parada mira la brecha no amortiguada < 0,2 min;
    #     itera más y mueve ≤ 0,07 pp. Juntos: original auto −0,10, metro
    #     −1,99, bici +2,07, caminata +0,01; equilibrio auto −0,03, metro
    #     −2,68, bici +2,68, caminata +0,03.
    # 12. D11 de la auditoría (2026-10-13): la accesibilidad del suelo cobra los
    #     viajes ESPERADOS, VIAJES_MES·(1 − p_tele,h), no 44 a todos. El alto
    #     (teletrabaja 40 %) aplana su gradiente más que el medio (20 %) y el
    #     bajo (5 %): distancia media al CBD alto 1,99 → 3,06 km, medio 2,96 →
    #     3,04, bajo 5,85 → 5,00 (alto y medio quedan empatados). Sólo se mueve «equilibrio»:
    #     auto +0,09, metro −1,50, bici +0,22, caminata +1,16; 20 → 17 it.
    # 13. Sin teletrabajo por defecto (2026-10-13, decisión de Leandro) y D5
    #     de la auditoría, juntos porque el ancla depende de los viajeros:
    #     `prob_teletrabajo` 0,40 / 0,20 / 0,05 → 0 en los tres estratos, y los
    #     VoT anclados al VST, ×1,0208 (6.329 / 3.164 / 1.633 $/h). Viajan todos
    #     los hogares (antes ~80,5 %), el corredor se carga más y gana el metro.
    #     Sobre VIAJEROS (lo antiguo dividido por 1 − teletrabajo), original:
    #     auto −0,92, metro +4,78, bici −3,58, caminata −0,26; equilibrio:
    #     auto −0,41, metro +4,37, bici −3,53, caminata −0,39. Teletrabajo
    #     19,5 → 0.
    # 14. μ del suelo como valor de escenario (2026-10-15, decisión de Leandro):
    #     `LandUseConfig.mu` = 0,30 en vez de la constante 1/√44 ≈ 0,151. La
    #     ciudad de partida se segrega (alto a 1,4 km del CBD en media, antes
    #     2,0; bajo a 6,4, antes 5,8) y el bajo, más lejos, camina menos. Sólo se
    #     mueve «equilibrio»: auto +0,07, metro +0,56, bici −0,15, caminata
    #     −0,47; mismas iteraciones.
    # 15. Oferta de la base: 4 pistas y ciclovía de 6.000 bici/h en vez de 2 y
    #     4.000 (2026-10-18, decisión de Leandro). Con 2 pistas el tramo junto
    #     al CBD cargaba v/c 2,01 (auto a ~4,4 km/h) y la ciclovía 1,54; ahora
    #     1,19 y 1,07. Más capacidad induce auto: original auto +4,57, metro
    #     −5,45, bici +1,51, caminata −0,65; equilibrio auto +3,23, metro −4,65,
    #     bici +2,10, caminata −0,68. El MSA cierra mucho antes: 29 → 10 y 12.
    # 16. Parada del equilibrio (2026-10-25, auditoría B, decisión de Leandro):
    #     'expected' promedia FLUJOS con el paso halving de Boyles §8.3.5 y para
    #     con la brecha no amortiguada < 0,02 min, no < 0,2 con paso 1/n. No es
    #     otro modelo sino el mismo equilibrio resuelto más cerca: lo pineado
    #     antes estaba 0,12-0,17 pp lejos del punto fijo (verificado contra
    #     G < 1e-6). Original auto −0,07, metro +0,17, bici −0,07, caminata
    #     −0,02; equilibrio auto −0,07, metro +0,12, bici −0,04, caminata −0,01.
    # 17. Media celda del CBD (2026-10-28, D-71, decisión de Leandro):
    #     auto y bici recorrían (k − ½)·dx, no k·dx como la caminata, el metro y
    #     el costo; les faltaba la media celda del CBD, que ahora cruzan con el
    #     flujo de su lado. La bici se alarga 50 m y deja de derivar con
    #     n_celdas. Original auto −0,02, metro +0,18, bici −0,21, caminata
    #     +0,06; equilibrio auto −0,03, metro +0,20, bici −0,21, caminata +0,04.
    "equilibrio": {
        "Auto": 28.25,
        "Metro": 26.11,
        "Bici": 35.79,
        "Caminata": 9.85,
        "Teletrabajo": 0.0,
    },
    "original": {
        "Auto": 29.16,
        "Metro": 23.42,
        "Bici": 35.42,
        "Caminata": 12.01,
        "Teletrabajo": 0.0,
    },
}

#: Iteraciones hasta converger. Pinearlo detecta cambios en la dinámica del MSA
#: que el reparto final podría no mostrar.
#: `equilibrio` pasó de 7 a 8 con los `lambda` heterogéneos (sep-2026): la ciudad
#: de partida es más segregada y el MSA necesita una pasada más. El reescalado
#: homoscedástico de transporte no cambió el conteo. Volvió a 8 con el parking
#: por tour (oct-2026): con más autos el corredor se carga más y tarda una pasada
#: más en estabilizarse. `original` pasó de 7 a 8 con la BPR sobre capacidad
#: práctica (oct-2026): con la curva más empinada el MSA necesita una pasada más.
#: D8 (oct-2026) cambió QUÉ se mide: la brecha no amortiguada < 0,2 min en vez
#: del cambio amortiguado < 0,1, que se aflojaba solo como 1/n. 8 → 20 y 13.
#: D11 (oct-2026, teletrabajo en la accesibilidad) movió la ciudad de partida
#: de `equilibrio`: 20 → 17. Sin teletrabajo por defecto y D5 (oct-2026): la
#: demanda sube ~24 % y la brecha baja como 1/n desde más arriba: 17 → 29 y
#: 13 → 29, con `max_iter` 40 (150 desde oct-2026: no cambia, porque cortan
#: por brecha). La oferta de 4 pistas y ciclovía 6.000 (oct-2026) descongestiona
#: el corredor y la brecha cae mucho antes: 29 → 12 y 29 → 10. La parada de la
#: auditoría B (oct-2026: flujos con paso halving, brecha < 0,02) llega más
#: cerca en menos pasadas: 12 → 6 y 10 → 6.
ITERACIONES_ESPERADAS = {"equilibrio": 6, "original": 6}

#: La misma corrida con `umbrales="suaves"` (oct-2026): rampas, corte CMNL y
#: dominancia suave del metro en vez de escalones, cortes duros y D-69. Es la
#: especificación alternativa que el usuario elige en la interfaz, y se pinea
#: aparte para que un cambio en ella tampoco pase inadvertido. Frente a la base:
#: el metro pierde 0,4-0,6 pp, que se reparten entre los otros tres modos.
#: Con la parada de la auditoría B (oct-2026) se movió como la base: metro +0,15
#: y +0,19; 12 → 6 y 9 → 6 iteraciones. Con la media celda del CBD (D-71,
#: oct-2026), también como la base: bici −0,25 y −0,26, metro +0,21 y +0,23.
ESPERADO_SUAVES = {
    "equilibrio": {"Auto": 28.53, "Metro": 25.74, "Bici": 35.78, "Caminata": 9.96},
    "original": {"Auto": 29.41, "Metro": 22.90, "Bici": 35.56, "Caminata": 12.12},
}
ITERACIONES_SUAVES = {"equilibrio": 6, "original": 6}


def _config_web(umbrales: str = "escalones") -> SimulationConfig:
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
        # Explícitos y no del default de Pydantic, por la regla de arriba.
        supply=SupplyConfig.model_validate(
            {"car": {"num_pistas": 4}, "bike": {"capacidad_pista": 6000}}
        ),
        demand=DemandConfig.model_validate(
            {"estratos": DEFAULT_STRATA, "globales": {"umbrales": umbrales}}
        ),
        max_iter=150,
        tolerance=0.02,  # = default del core desde la auditoría B (oct-2026)
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


def _corre(localizacion: str, umbrales: str = "escalones") -> tuple[dict[str, float], int, bool]:
    trace = ConvergenceTrace()
    sim = _config_web(umbrales)
    for _ in iter_msa_desde_suelo(sim, _land_use_web(), trace, localizacion=localizacion):
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


@pytest.mark.parametrize("localizacion", ["equilibrio", "original"])
def test_linea_base_umbrales_suaves(localizacion: str) -> None:
    """La especificación alternativa también tiene su base pineada."""
    pct, iteraciones, converged = _corre(localizacion, "suaves")
    assert converged
    assert iteraciones == ITERACIONES_SUAVES[localizacion]
    for modo, objetivo in ESPERADO_SUAVES[localizacion].items():
        assert abs(pct[modo] - objetivo) <= TOL_PP, f"{modo}: {pct[modo]:.2f} vs {objetivo}"


def test_un_ciclo_de_periodo_dos_parte_el_paso() -> None:
    """Con el doble de hogares la iteración directa oscila entre dos estados
    (el auto salta entre ~21 % y ~27 %) y la brecha baja apenas ~0,5 % por
    vuelta. El halving con «no bajó» estricto nunca partía el paso y la corrida
    agotaba el tope con brecha 11,8 min; con disminución suficiente
    (`_RHO_HALVING`) el paso se parte y converge."""
    lu = _land_use_web()
    lu = lu.model_copy(update={"H_por_estrato": tuple(2 * h for h in lu.H_por_estrato)})
    trace = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(_config_web(), lu, trace, localizacion="original"):
        pass
    assert trace.converged
    assert min(s.f_msa for s in trace.iteraciones) < 1.0


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
