"""De una `ConfigPersona` a un resultado serializable — la puerta desde la app.

Arma el caso binario a partir del equilibrio de la ciudad (el día 0 del
experimento: los tiempos que todos conocen al empezar) y corre la simulación.
"""

from __future__ import annotations

from typing import TypedDict

import numpy as np

from titirilquen_core.aprendizaje.ciudad import (
    MODOS_CIUDAD,
    EscenarioCiudad,
    simular_ciudad,
)
from titirilquen_core.aprendizaje.config import (
    MODOS_BINARIOS,
    ConfigCiudad,
    ConfigPersona,
)
from titirilquen_core.aprendizaje.persona import (
    CasoBinario,
    delta_critico,
    p_post_analitica,
    peso_shocks,
    simular,
)
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import run_msa
from titirilquen_core.land_use.config import LandUseConfig

# --- La forma de salida ---------------------------------------------------------
# Declarada como TypedDict porque `tools/genera_contrato.py` emite desde acá la
# interfaz TypeScript: el contrato se genera, no se escribe a mano.


class TiemposCeldaDict(TypedDict):
    """Los tiempos de UNA celda, tal como los trae el snapshot del equilibrio.

    Permite armar el caso sin volver a resolver la ciudad: en el navegador esa
    diferencia es de un minuto a nada.
    """

    auto_total: float
    bici_total: float
    bici_libre: float
    tren_acceso: float
    tren_espera: float
    tren_viaje: float


class EscenarioResumenDict(TypedDict):
    """Lo que la interfaz necesita saber de un escenario ya preparado.

    El escenario en sí son matrices de N × 4 y no viaja: se queda cacheado del
    lado del motor y la interfaz lo referencia por `clave`.
    """

    clave: str
    k_modos: int
    n_agentes: int
    eligen: int
    modos: list[str]
    split_equilibrio: list[float]


class PhiVentanasDict(TypedDict):
    """Φ en los tres horizontes."""

    corto: float
    medio: float
    largo: float


class GrupoDict(TypedDict):
    """Un grupo de la población, separado por cuál es SU modo mejor.

    Es la tabla que importa en E4: `lleva_ruido` dice si la variabilidad cayó
    sobre el modo que a esa persona le convenía, y de eso depende el signo.
    """

    modo: str
    n: int
    lleva_ruido: bool
    p_estrella: float
    uniforme: float
    phi: PhiVentanasDict


class CiudadDict(TypedDict):
    """El resultado de un experimento sobre la ciudad."""

    n_agentes: int
    eligen: int
    modos: list[str]
    dias: int
    escala: float
    split_equilibrio: list[float]
    split_ultimos: list[float]
    split_por_dia: list[list[float]]
    phi: PhiVentanasDict
    por_mejor: list[GrupoDict]
    dispersion_iguales: float
    abandono_auto: float
    abandono_metro: float
    suerte_mala_auto: float
    suerte_buena_auto: float
    brecha_percepcion_min: float


class VentanaDict(TypedDict):
    """Lo que resume una ventana de días."""

    desde: int
    hasta: int
    s: float
    phi: float
    invertidos: float


class VentanasDict(TypedDict):
    """Los tres horizontes de análisis."""

    corto: VentanaDict
    medio: VentanaDict
    largo: VentanaDict


class CasoDict(TypedDict):
    """El caso binario del que salió el experimento.

    `margen_phi` es P* − ½, el denominador de Φ. Donde es chico, Φ amplifica
    cualquier diferencia: con P* = 0,51 un desvío de un punto en la cuota se
    convierte en un Φ de dos dígitos. Quien muestre Φ tiene que mirarlo.
    """

    estrato: int
    celda: int
    modos: list[str]
    mejor: str
    tau: list[float]
    v_ref: list[float]
    beta: float
    dv: float
    ventaja_min: float
    p_verdadera: float
    margen_phi: float


class ShockDict(TypedDict):
    """El umbral analítico y su contraste con la simulación. Sólo con tratamiento."""

    w_k: float
    delta_critico_min: float
    p_post_analitica: float
    p_post_simulada: float | None
    llegan_a_k: float


class AprendizajeDict(TypedDict):
    """El resultado completo de un experimento de una persona."""

    caso: CasoDict
    dias: int
    replicas: int
    ventanas: VentanasDict
    s_por_dia: list[float]
    p_replicas: list[list[float]]
    shock: ShockDict | None


#: Cuantas trayectorias individuales se mandan junto al promedio. `s_por_dia`
#: es la media sobre las replicas, y esa media es suave aunque cada historia
#: sea una escalera: el tratamiento de E1 cae el dia en que la persona ELIGE
#: el modo mejor, que no es el mismo dia en todas. Sin ver una replica sola,
#: la figura sugiere un ajuste gradual que el modelo no tiene.
REPLICAS_MUESTRA = 20


#: Fracciones del horizonte que definen corto, mediano y largo plazo. Con 250
#: días dan exactamente las ventanas de los informes: 1–10, 11–50 y 51–250.
CORTES = (0.04, 0.20, 1.00)


def ventanas(dias: int) -> dict[str, tuple[int, int]]:
    """Las tres ventanas de análisis para un horizonte cualquiera, 1-indexadas."""
    if dias < 3:
        raise ValueError("hacen falta al menos 3 días para tres ventanas")
    fin = [max(i + 1, int(np.ceil(dias * c))) for i, c in enumerate(CORTES)]
    fin[2] = dias
    return {
        "corto": (1, fin[0]),
        "medio": (fin[0] + 1, fin[1]),
        "largo": (fin[1] + 1, fin[2]),
    }


def _caso_binario(caso: CasoDict) -> CasoBinario:
    """Del dict serializable de vuelta al objeto de cálculo."""
    return CasoBinario(
        tau=np.array(caso["tau"]),
        v_ref=np.array(caso["v_ref"]),
        beta=caso["beta"],
    )


def preparar_caso(
    sim: SimulationConfig,
    lu: LandUseConfig,
    *,
    estrato: int,
    celda: int,
    tiempos: TiemposCeldaDict | None = None,
) -> CasoDict:
    """El caso de una celda, serializable, listo para correr experimentos.

    Con `tiempos` usa los que ya se calcularon —los del snapshot del equilibrio
    que la app tiene a mano— y NO resuelve la ciudad. Sin ellos corre el MSA,
    que en Pyodide cuesta más de un minuto.
    """
    if tiempos is not None:
        if not 0 <= celda < sim.city.n_celdas:
            raise ValueError(f"celda {celda} fuera de la ciudad ({sim.city.n_celdas} celdas)")
        caso = _caso_con_tiempos(
            sim,
            estrato=estrato,
            celda=celda,
            t=TiemposObservados(**tiempos),
        )
    else:
        caso = caso_desde_equilibrio(sim, lu, estrato=estrato, celda=celda)
    return {
        "estrato": estrato,
        "celda": celda,
        "modos": list(MODOS_BINARIOS),
        "mejor": MODOS_BINARIOS[caso.mejor],
        "tau": caso.tau.tolist(),
        "v_ref": caso.v_ref.tolist(),
        "beta": caso.beta,
        "dv": caso.dv,
        "ventaja_min": caso.ventaja_min,
        "p_verdadera": caso.p_verdadera,
        "margen_phi": caso.p_verdadera - 0.5,
    }


def caso_desde_equilibrio(
    sim: SimulationConfig, lu: LandUseConfig, *, estrato: int, celda: int
) -> CasoBinario:
    """El caso binario de una persona, con los tiempos del equilibrio MSA.

    Ese equilibrio es el prior del IBL: la información exógena de buena calidad
    con la que la persona arranca el día 1.
    """
    s = run_msa(sim, lu, localizacion="equilibrio").iteraciones[-1]
    if not 0 <= celda < sim.city.n_celdas:
        raise ValueError(f"celda {celda} fuera de la ciudad ({sim.city.n_celdas} celdas)")
    t = TiemposObservados(
        auto_total=float(s.t_auto[celda]),
        bici_total=float(s.t_bici[celda]),
        tren_acceso=float(s.t_tren_acceso[celda]),
        tren_espera=float(s.t_tren_espera[celda]),
        tren_viaje=float(s.t_tren_viaje[celda]),
        bici_libre=float(s.t_bici_libre[celda]),
    )
    return _caso_con_tiempos(sim, estrato=estrato, celda=celda, t=t)


def _caso_con_tiempos(
    sim: SimulationConfig, *, estrato: int, celda: int, t: TiemposObservados
) -> CasoBinario:
    """El caso de una celda, con los tiempos ya resueltos."""
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    u = calcular_utilidades(
        estrato=estrato,  # type: ignore[arg-type]
        celda_origen=celda,
        tiene_auto=True,
        ciudad=ciudad,
        config=sim.demand,
        tiempos_observados=t,
        modos_habilitados=MODOS_BINARIOS,
    )
    for m in MODOS_BINARIOS:
        if not u[m].feasible:
            raise ValueError(f"el modo {m} no es factible en la celda {celda}")
    return CasoBinario(
        # τ es el tiempo que pondera β: del metro, sólo el que va en vehículo.
        # El acceso y la espera ya están dentro de v_ref y no se aprenden.
        tau=np.array([t.auto_total, t.tren_viaje]),
        v_ref=np.array([u[m].valor for m in MODOS_BINARIOS]),
        beta=float(sim.demand.estratos[estrato].betas.b_tiempo_viaje),  # type: ignore[index]
    )


def ejecutar_persona(caso_dict: CasoDict, cfg: ConfigPersona) -> AprendizajeDict:
    """El paso barato: corre el experimento sobre un caso ya preparado.

    `caso_dict` sale de `preparar_caso`. No se vuelve a resolver el equilibrio.
    """
    caso = _caso_binario(caso_dict)
    r = simular(
        caso,
        d=cfg.d,
        sigma=cfg.sigmas(),
        k=cfg.k_shocks,
        delta=cfg.delta_min,
        replicas=cfg.replicas,
        dias=cfg.dias,
        semilla=cfg.semilla,
    )
    vs = ventanas(cfg.dias)
    p_estrella = caso.p_verdadera
    por_ventana: dict[str, VentanaDict] = {}
    for nombre, (a, b) in vs.items():
        pn = r.p[:, a - 1 : b].mean(axis=1)
        s = float(pn.mean())
        por_ventana[nombre] = {
            "desde": a,
            "hasta": b,
            "s": s,
            "phi": (s - 0.5) / (p_estrella - 0.5),
            "invertidos": float(np.mean(pn < 0.5)),
        }

    salida: AprendizajeDict = {
        "caso": caso_dict,
        "dias": cfg.dias,
        "replicas": cfg.replicas,
        "ventanas": por_ventana,  # type: ignore[typeddict-item]
        "s_por_dia": r.p.mean(axis=0).round(5).tolist(),
        "p_replicas": r.p[:REPLICAS_MUESTRA].round(5).tolist(),
        "shock": None,
    }
    if cfg.k_shocks > 0:
        salida["shock"] = {
            "w_k": peso_shocks(cfg.k_shocks, cfg.d),
            "delta_critico_min": delta_critico(caso, cfg.k_shocks, cfg.d),
            "p_post_analitica": p_post_analitica(caso, cfg.k_shocks, cfg.d, cfg.delta_min),
            "p_post_simulada": (float(np.nanmean(r.p_post)) if r.llegan_a_k > 0 else None),
            "llegan_a_k": r.llegan_a_k,
        }
    return salida


def ejecutar_desde_equilibrio(
    sim: SimulationConfig, lu: LandUseConfig, cfg: ConfigPersona
) -> AprendizajeDict:
    """Los dos pasos juntos. Para tests y scripts, no para la interfaz.

    En el navegador conviene llamar `preparar_caso` una vez y después
    `ejecutar_persona` por cada experimento: el equilibrio es el caro.
    """
    caso = preparar_caso(sim, lu, estrato=cfg.estrato, celda=cfg.celda)
    return ejecutar_persona(caso, cfg)


def ejecutar_ciudad(esc: EscenarioCiudad, cfg: ConfigCiudad) -> CiudadDict:
    """Corre un experimento sobre un escenario ya preparado.

    `esc` sale de `preparar_escenario`, que es el paso caro —resuelve el
    equilibrio— y se reusa entre experimentos.
    """
    r = simular_ciudad(
        esc,
        d=cfg.d,
        sigma=cfg.sigma_min,
        ruido=cfg.ruido(),
        escala=cfg.escala,
        dias=cfg.dias,
        ultimos=cfg.ultimos,
        semilla=cfg.semilla,
    )
    ventanas_phi: PhiVentanasDict = {
        "corto": r["phi"]["todos"]["corto"],
        "medio": r["phi"]["todos"]["medio"],
        "largo": r["phi"]["todos"]["largo"],
    }
    lleva = dict(zip(MODOS_CIUDAD, cfg.ruido(), strict=False))
    grupos: list[GrupoDict] = [
        {
            "modo": m,
            "n": v["n"],
            "lleva_ruido": bool(lleva.get(m, False)) and cfg.sigma_min > 0,
            "p_estrella": v["p_estrella"],
            "uniforme": v["uniforme"],
            "phi": {w: v[w] for w in ("corto", "medio", "largo")},  # type: ignore[typeddict-item]
        }
        for m, v in r["phi"]["por_mejor"].items()
    ]

    # La brecha entre la utilidad con la que se decide y la que se vive, en
    # minutos. b_tiempo_viaje es el mismo en los tres estratos; si dejara de
    # serlo, esto es su promedio sobre quienes eligen.
    u = cfg.ultimos
    dec = sum(r["bienestar_decision_por_dia"][-u:]) / u
    exp = sum(r["bienestar_por_dia"][-u:]) / u
    beta = float(abs(esc.btv[esc.elige].mean()))

    return {
        "n_agentes": esc.N,
        "eligen": int(esc.elige.sum()),
        "modos": list(MODOS_CIUDAD),
        "dias": cfg.dias,
        "escala": cfg.escala,
        "split_equilibrio": esc.split_equilibrio,
        "split_ultimos": r["split_ultimos"],
        "split_por_dia": r["split_por_dia"],
        "phi": ventanas_phi,
        "por_mejor": grupos,
        "dispersion_iguales": r["dispersion_iguales"],
        "abandono_auto": r["abandono_auto"],
        "abandono_metro": r["abandono_metro"],
        "suerte_mala_auto": r["share_fin_mala_suerte_auto"],
        "suerte_buena_auto": r["share_fin_buena_suerte_auto"],
        "brecha_percepcion_min": (dec - exp) / beta,
    }


def resumen_escenario(esc: EscenarioCiudad, *, clave: str, k_modos: int) -> EscenarioResumenDict:
    """La ficha del escenario que se le devuelve a la interfaz."""
    return {
        "clave": clave,
        "k_modos": k_modos,
        "n_agentes": esc.N,
        "eligen": int(esc.elige.sum()),
        "modos": list(MODOS_CIUDAD),
        "split_equilibrio": esc.split_equilibrio,
    }
