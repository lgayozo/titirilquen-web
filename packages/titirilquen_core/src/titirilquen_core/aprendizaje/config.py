"""Configuración de un experimento de aprendizaje — la puerta desde la interfaz.

Un experimento se describe con tres cosas: a quién se le aplica (estrato y celda,
de donde sale el caso binario), qué tratamiento recibe (ruido y/o mala racha), y
cuánto dura. Los defaults reproducen los experimentos publicados.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from titirilquen_core.config import Modo, StratumId

#: Los dos modos entre los que se elige en los experimentos de una persona.
MODOS_BINARIOS: tuple[Modo, Modo] = ("Auto", "Metro")

#: Dónde va el ruido del tiempo de viaje, en los términos de E2.
CondicionRuido = Literal["ninguno", "ambos", "solo_mejor", "solo_peor"]


class ConfigPersona(BaseModel):
    """Un experimento de una persona entre dos modos, con la red congelada."""

    estrato: StratumId = Field(default=2, description="Estrato de ingreso de la persona.")
    celda: int = Field(default=135, ge=0, description="Celda de origen en la ciudad lineal.")

    dias: int = Field(
        default=250,
        ge=2,
        le=1000,
        description="Horizonte en días. El costo del IBL crece con el cuadrado.",
    )
    replicas: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Historias independientes de la misma persona.",
    )
    semilla: int = Field(default=42, description="Semilla del generador.")

    # --- memoria
    d: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description=(
            "Decaimiento del IBL. 0 promedia toda la historia por igual; más alto "
            "mira sólo lo reciente. Guevara, Tang y Gao (2018) estiman 1,28."
        ),
    )

    # --- tratamiento de E2: variabilidad
    condicion: CondicionRuido = Field(
        default="ninguno",
        description="En qué modo cae el ruido del tiempo vivido.",
    )
    sigma_min: float = Field(
        default=0.0,
        ge=0.0,
        le=240.0,
        description="Desviación estándar del tiempo vivido, en minutos.",
    )

    # --- tratamiento de E1: una mala racha temprana
    k_shocks: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Cuántas de las primeras veces que usa el modo mejor salen peores.",
    )
    delta_min: float = Field(
        default=0.0,
        ge=0.0,
        le=600.0,
        description="Cuánto peor sale cada una de esas veces, en minutos.",
    )

    @model_validator(mode="after")
    def _coherencia(self) -> ConfigPersona:
        if self.condicion != "ninguno" and self.sigma_min == 0.0:
            raise ValueError("con una condición de ruido, sigma_min debe ser > 0")
        if self.condicion == "ninguno" and self.sigma_min > 0.0:
            raise ValueError("sigma_min > 0 necesita una condición de ruido distinta de «ninguno»")
        if (self.k_shocks > 0) != (self.delta_min > 0.0):
            raise ValueError("k_shocks y delta_min van juntos: o los dos en cero, o ninguno")
        return self

    def sigmas(self, mejor_es_primero: bool = True) -> tuple[float, float]:
        """(σ del modo mejor, σ del peor), como los espera `persona.simular`."""
        del mejor_es_primero  # el orden lo resuelve `simular` con `caso.mejor`
        s = self.sigma_min
        return {
            "ninguno": (0.0, 0.0),
            "ambos": (s, s),
            "solo_mejor": (s, 0.0),
            "solo_peor": (0.0, s),
        }[self.condicion]


class ConfigCiudad(BaseModel):
    """Un experimento sobre la ciudad entera, con la congestión respondiendo.

    El horizonte por defecto es corto a propósito: el costo del IBL crece con su
    cuadrado y en el navegador 250 días no son viables. Los resultados
    publicados usan 250; acá se busca poder mover las palancas y ver.
    """

    k_modos: Literal[2, 3] = Field(
        default=2,
        description=(
            "2 = auto y metro, todos con auto (E3). 3 agrega la bici, que no "
            "lleva ruido y por eso hace visible la sustitución (E4)."
        ),
    )
    dias: int = Field(
        default=50,
        ge=3,
        le=250,
        description="Horizonte en días. El costo crece con el cuadrado.",
    )
    ultimos: int = Field(
        default=20, ge=1, le=100, description="Días finales que definen el estado final."
    )
    semilla: int = Field(default=42, description="Semilla del generador.")

    d: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Decaimiento del IBL. Guevara, Tang y Gao (2018) estiman 1,28.",
    )
    sigma_min: float = Field(
        default=0.0,
        ge=0.0,
        le=240.0,
        description="Desviación estándar del tiempo vivido, en minutos.",
    )
    ruido_auto: bool = Field(default=True, description="Si el auto lleva ruido.")
    ruido_metro: bool = Field(default=True, description="Si el metro lleva ruido.")
    ruido_bici: bool = Field(
        default=False,
        description=(
            "Si la bici lleva ruido. Dejarla sin él es el supuesto que hace "
            "visible hacia dónde se desplazan los viajes (E4)."
        ),
    )
    escala: float = Field(
        default=1.0,
        gt=0.0,
        le=20.0,
        description=(
            "Escala del logit. 1 es el simulador; otra es una sensibilidad de "
            "calibración y NO es inocua acá: el día 0 deja de ser equilibrio y "
            "la ciudad se corre sola, sin ningún ruido."
        ),
    )

    @model_validator(mode="after")
    def _coherencia_ciudad(self) -> ConfigCiudad:
        if self.ultimos > self.dias:
            raise ValueError("`ultimos` no puede pasar del horizonte")
        if self.sigma_min > 0 and not any(self.ruido()):
            raise ValueError("con sigma > 0 hace falta al menos un modo con ruido")
        return self

    def ruido(self) -> tuple[bool, ...]:
        """Qué modos aprendidos llevan ruido, en el orden de MODOS_CIUDAD."""
        todos = (self.ruido_auto, self.ruido_metro, self.ruido_bici)
        return todos[: self.k_modos]
