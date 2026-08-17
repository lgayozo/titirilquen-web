"""Constantes del modelo que el frontend también necesita.

No son configuración —no se ajustan desde la interfaz— pero sí aparecen en
figuras, rótulos y validaciones del lado TypeScript. Sin un lugar único, cada
una termina copiada a mano en varios archivos: los cortes de factibilidad
llegaron a estar en tres sitios (`utility.py`, `utility.ts` y `CityStrip.tsx`),
con un comentario que advertía "dos copias derivan" en la que ya era la tercera.

Este módulo es la fuente; `tools/genera_contrato.py` lo emite como
`constantes.gen.ts`.
"""

from __future__ import annotations

from typing import Final, Literal

#: Orden canónico de los modos de transporte. Define el orden de las series en
#: toda figura y el layout del cubo `demanda_estrato` [estrato, MODO, celda].
MODOS: Final[tuple[str, ...]] = ("Auto", "Metro", "Bici", "Caminata")

#: Ídem incluyendo a quien no viaja. El teletrabajo no es un modo elegible —se
#: decide antes de la elección— pero sí es una categoría del reparto.
MODOS_CON_TELETRABAJO: Final[tuple[str, ...]] = (*MODOS, "Teletrabajo")

#: Todo lo que puede pasarle a un agente, incluido quedarse sin ninguna
#: alternativa factible. Es el conjunto de claves de todo `reparto_modal`, y
#: como `Literal` viaja al contrato TypeScript: ahí `reparto_modal.Auot` deja de
#: compilar en vez de ser `undefined` en tiempo de ejecución.
CategoriaModal = Literal["Auto", "Metro", "Bici", "Caminata", "Teletrabajo", "Varado"]

#: La misma lista, para iterar. `Varado` va al final porque no es un modo: es la
#: ausencia de uno.
CATEGORIAS_MODALES: Final[tuple[str, ...]] = (*MODOS_CON_TELETRABAJO, "Varado")

#: Sobre este tiempo la caminata deja de ser una alternativa considerada (min).
#: Es un supuesto del modelo de elección, no un parámetro calibrable.
CORTE_CAMINATA_MIN: Final[float] = 30.0

#: Ídem para la bicicleta (min).
CORTE_BICI_MIN: Final[float] = 45.0

#: Valor social del tiempo, $/hora-pasajero. Precios Sociales 2026 del Sistema
#: Nacional de Inversiones, Tabla 2.1, «Viaje en vehículo».
#:
#: **Se actualiza cada año.** Es un valor de norma, no una calibración: entra en
#: la evaluación social (costo del tiempo agregado), no en la elección de modo,
#: que usa el valor del tiempo CONDUCTUAL de cada estrato.
VOT_SOCIAL_CLP_HORA: Final[float] = 3338.0
