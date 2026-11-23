"""Aprendizaje día a día (instance-based learning) sobre el simulador.

La persona no conoce los tiempos: los aprende de lo que vive, y sólo vive el
modo que eligió. De esa asimetría salen los fenómenos que estos experimentos
miden — el atrapamiento tras una mala racha, el efecto de la variabilidad, y la
brecha entre la utilidad con la que se decide y la que se experimenta.

* `ibl`: las dos ecuaciones del tiempo percibido. Puras y vectorizadas.
* `persona`: una persona entre dos modos, con la red congelada (E1 y E2).
* `ciudad`: la poblacion entera, con la congestion respondiendo (E3 y E4).
* `config` y `ejecutar`: la puerta desde la interfaz — parametros validados
  adentro, un diccionario serializable afuera.
"""

from titirilquen_core.aprendizaje.ciudad import (
    EscenarioCiudad,
    cuota_del_mejor,
    dispersion_entre_iguales,
    phi_poblacion,
    preparar_escenario,
    simular_ciudad,
    softmax_filas,
    suerte_del_estreno,
)
from titirilquen_core.aprendizaje.config import ConfigCiudad, ConfigPersona
from titirilquen_core.aprendizaje.ejecutar import (
    REPLICAS_MUESTRA,
    TiemposCeldaDict,
    caso_desde_equilibrio,
    ejecutar_ciudad,
    ejecutar_desde_equilibrio,
    ejecutar_persona,
    preparar_caso,
    resumen_escenario,
    ventanas,
)
from titirilquen_core.aprendizaje.ibl import pesos_ibl, tiempo_percibido
from titirilquen_core.aprendizaje.persona import (
    CasoBinario,
    ResultadoPersona,
    cuota_por_persona,
    delta_critico,
    logistica,
    p_post_analitica,
    peso_shocks,
    phi,
    simular,
)

__all__ = [
    "REPLICAS_MUESTRA",
    "CasoBinario",
    "ConfigCiudad",
    "ConfigPersona",
    "EscenarioCiudad",
    "ResultadoPersona",
    "TiemposCeldaDict",
    "caso_desde_equilibrio",
    "cuota_del_mejor",
    "cuota_por_persona",
    "delta_critico",
    "dispersion_entre_iguales",
    "ejecutar_ciudad",
    "ejecutar_desde_equilibrio",
    "ejecutar_persona",
    "logistica",
    "p_post_analitica",
    "peso_shocks",
    "pesos_ibl",
    "phi",
    "phi_poblacion",
    "preparar_caso",
    "preparar_escenario",
    "resumen_escenario",
    "simular",
    "simular_ciudad",
    "softmax_filas",
    "suerte_del_estreno",
    "tiempo_percibido",
    "ventanas",
]
