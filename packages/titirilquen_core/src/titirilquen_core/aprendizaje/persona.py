"""Aprendizaje día a día de UNA persona entre dos modos, con la red congelada.

Es el motor de los experimentos E1 (una mala racha temprana) y E2 (variabilidad
del tiempo de viaje). La persona elige todos los días, vive el tiempo del modo
que eligió —y de ningún otro— y al día siguiente decide con el IBL sobre lo que
vivió. La red no responde: los tiempos de referencia son fijos. La ciudad
completa, con congestión endógena, es `aprendizaje.ciudad`.

**La escala.** El logit de transporte del núcleo normaliza μ = 1 y son los β los
que absorben la escala (`demand.choice.probabilidades_logit` calcula `e^V` a
secas). Por eso acá no hay un parámetro μ: para explorar otra escala se
multiplica `v_ref` y `beta` por el mismo factor, que es exactamente equivalente.
Ojo con interpretarlo como una perilla libre: los β están calibrados bajo esa
normalización.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.aprendizaje.ibl import tiempo_percibido


def logistica(z: NDArray[np.float64] | float) -> NDArray[np.float64] | float:
    """Λ(z) = 1/(1 + e^{−z}), el logit binario."""
    return 1.0 / (1.0 + np.exp(-z))


@dataclass(frozen=True)
class CasoBinario:
    """Una situación de elección entre dos modos, con los tiempos congelados.

    `tau` y `v_ref` van en el mismo orden (modo 0, modo 1). `tau` es el tiempo
    que pondera β —el que la persona aprende—, no el tiempo total de puerta a
    puerta: lo que queda fuera (espera, acceso) ya está dentro de `v_ref`.
    """

    tau: NDArray[np.float64]
    """(2,) tiempo de referencia que pondera β, en minutos."""
    v_ref: NDArray[np.float64]
    """(2,) utilidad con los tiempos de referencia, en útiles."""
    beta: float
    """Coeficiente del tiempo de viaje, en útiles/min. Negativo."""

    def __post_init__(self) -> None:
        if self.tau.shape != (2,) or self.v_ref.shape != (2,):
            raise ValueError("tau y v_ref deben ser de forma (2,)")
        if self.beta >= 0:
            raise ValueError(f"beta debe ser negativo, es {self.beta}")

    @property
    def mejor(self) -> int:
        """Índice del modo con más utilidad de referencia."""
        return 0 if self.v_ref[0] > self.v_ref[1] else 1

    @property
    def dv(self) -> float:
        """ΔV: ventaja del modo mejor sobre el otro, en útiles."""
        return float(abs(self.v_ref[0] - self.v_ref[1]))

    @property
    def ventaja_min(self) -> float:
        """A = ΔV/|β|: la misma ventaja en minutos.

        Es la forma invariante de escala de leerla: multiplicar toda la utilidad
        por k deja A igual.
        """
        return self.dv / abs(self.beta)

    @property
    def p_verdadera(self) -> float:
        """P*: la probabilidad de quien conoce los tiempos de referencia."""
        return float(logistica(self.dv))


# --- Fórmulas cerradas ----------------------------------------------------------


def peso_shocks(k: int, d: float) -> float:
    """W_k: peso conjunto de k experiencias consecutivas frente al prior.

    Si la persona usa el modo los días 1…k, al decidir el día k + 1 esas
    experiencias tienen antigüedad 1…k y el prior (día 0) tiene k + 1. Con
    d = 0 da k/(k+1), sin importar cuándo ocurrieron.
    """
    if k < 1:
        raise ValueError("k debe ser ≥ 1")
    act = np.arange(1, k + 1, dtype=float) ** (-d)
    return float(act.sum() / (act.sum() + (k + 1.0) ** (-d)))


def delta_critico(caso: CasoBinario, k: int, d: float) -> float:
    """Δ*: el shock, en minutos, que deja la ventaja percibida en cero.

    Δ* = A/W_k. Nótese que sólo depende de la ventaja en minutos y de la
    memoria: **no de la escala del logit**.
    """
    return caso.ventaja_min / peso_shocks(k, d)


def p_post_analitica(caso: CasoBinario, k: int, d: float, delta: float) -> float:
    """P del modo mejor al decidir justo después del k-ésimo shock.

    Λ(ΔV − |β|·W_k·Δ). A diferencia de Δ*, esto sí lleva la escala: multiplicar
    la utilidad por k multiplica el argumento del logit, así que el cruce por ½
    no se mueve pero la caída se vuelve más abrupta.
    """
    return float(logistica(caso.dv - abs(caso.beta) * peso_shocks(k, d) * delta))


# --- Simulación -----------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoPersona:
    """Lo que devuelve una corrida de `simular`."""

    p: NDArray[np.float64]
    """(replicas, dias) probabilidad de elegir el modo mejor cada día."""
    elige_mejor: NDArray[np.bool_]
    """(replicas, dias) lo que efectivamente eligió."""
    p_post: NDArray[np.float64]
    """(replicas,) P al decidir tras el k-ésimo shock; NaN si nunca llegó a k."""

    @property
    def llegan_a_k(self) -> float:
        """Fracción de réplicas que alcanzó las k experiencias del tratamiento.

        Baja mucho con shocks grandes: la persona abandona el modo antes de
        recibirlos todos, y eso es parte del resultado, no un defecto.
        """
        return float(np.mean(~np.isnan(self.p_post)))


def simular(
    caso: CasoBinario,
    *,
    d: float,
    sigma: tuple[float, float] = (0.0, 0.0),
    k: int = 0,
    delta: float = 0.0,
    replicas: int = 500,
    dias: int = 250,
    semilla: int = 42,
) -> ResultadoPersona:
    """`replicas` historias independientes de la misma persona, `dias` días.

    `sigma` = (σ del modo mejor, σ del peor) en minutos: el ruido del tiempo
    vivido. `k` y `delta` son el tratamiento de E1: las primeras `k` veces que
    la persona elige el modo mejor, su experiencia sale `delta` minutos peor.

    El prior del IBL es el tiempo de referencia en t' = 0, con a = 1 en los dos
    modos: así `b` está definido desde el día 1 y el prior decae con d como
    cualquier experiencia.
    """
    if dias < 1 or replicas < 1:
        raise ValueError("dias y replicas deben ser ≥ 1")
    rng = np.random.default_rng(semilla)
    m = caso.mejor
    sig = np.zeros(2)
    sig[m], sig[1 - m] = sigma

    x = np.zeros((replicas, dias + 1, 2))
    a = np.zeros((replicas, dias + 1, 2), dtype=bool)
    x[:, 0, :] = caso.tau  # prior: a(0) = 1, x(0) = τ
    a[:, 0, :] = True

    p = np.zeros((replicas, dias))
    elige_mejor = np.zeros((replicas, dias), dtype=bool)
    usos = np.zeros(replicas, dtype=int)  # veces que usó el modo mejor
    p_post = np.full(replicas, np.nan)
    filas = np.arange(replicas)

    for t in range(1, dias + 1):
        b = tiempo_percibido(x, a, t, d)
        v = caso.v_ref + caso.beta * (b - caso.tau)
        p_t = logistica(v[:, m] - v[:, 1 - m])
        if k > 0:
            recien = (usos == k) & np.isnan(p_post)
            p_post[recien] = p_t[recien]
        p[:, t - 1] = p_t
        mejor_hoy = rng.random(replicas) < p_t
        elige_mejor[:, t - 1] = mejor_hoy
        modo = np.where(mejor_hoy, m, 1 - m)
        eps = rng.normal(0.0, 1.0, size=(replicas, 2)) * sig
        shock = np.where(mejor_hoy & (usos < k), delta, 0.0)
        x[filas, t, modo] = caso.tau[modo] + eps[filas, modo] + shock
        a[filas, t, modo] = True
        usos += mejor_hoy

    return ResultadoPersona(p=p, elige_mejor=elige_mejor, p_post=p_post)


# --- Indicadores ----------------------------------------------------------------


def cuota_por_persona(p: NDArray[np.float64], ventana: tuple[int, int]) -> NDArray[np.float64]:
    """P̄_n: promedio de P_n(t) en la ventana de días, 1-indexada e inclusiva."""
    a, b = ventana
    if not 1 <= a <= b <= p.shape[1]:
        raise ValueError(f"ventana {ventana} fuera de los {p.shape[1]} días")
    return p[:, a - 1 : b].mean(axis=1)


def phi(caso: CasoBinario, p: NDArray[np.float64], ventana: tuple[int, int]) -> float:
    """Φ: qué fracción de la ventaja verdadera sobrevive al aprendizaje.

    (S − ½)/(P* − ½), donde S es la cuota media del modo mejor en la ventana.
    Φ = 1 reprodujo la decisión informada, 0 es tirar una moneda, y negativo
    significa que en promedio se elige el modo peor.
    """
    s = float(cuota_por_persona(p, ventana).mean())
    return (s - 0.5) / (caso.p_verdadera - 0.5)
