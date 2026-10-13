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

import math
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

#: Viajes de conmutación por mes (2 por día laboral × 22 días). Convierte el
#: costo por viaje en carga mensual costo/ingreso (D-27) y el logsum por viaje en
#: la accesibilidad mensual que entra a la puja por suelo (D-34): el arriendo
#: `p` y el ingreso `y` son mensuales, así que el término de transporte también.
VIAJES_MES: Final[int] = 44

#: `μ` del uso de suelo: la precisión del ruido de la utilidad de localizarse
#: (el `μ_h` de Martínez 2018, ec. 4.2), común a los estratos; la puja en dinero
#: tiene precisión `β_h = μ·λ_h` (ec. 4.3). NO es una normalización libre, como
#: la escala 1 del logit de transporte: fija cuánto pesa el ruido de elegir casa
#: frente a la utilidad de transporte, que ya tiene su escala. Vale 1/√VIAJES_MES
#: ≈ 0,151 por una ANALOGÍA, no por derivación: si la accesibilidad mensual suma
#: VIAJES_MES viajes y cada uno trae su shock Gumbel independiente, la
#: desviación del shock mensual crece como √VIAJES_MES (aproximación de segundo
#: momento: la suma de Gumbel no es Gumbel). En Martínez la escala se identifica
#: con rentas observadas, que el simulador no tiene. μ = 1 («un shock por casa,
#: como el de un viaje») da una ciudad casi determinista.
#:
#: Es constante y no campo del schema desde la v7 (oct-2026, D1 de la
#: auditoría): con `α` ya fijo en 1, mover μ es el único modo de mover la
#: sensibilidad de la puja a la accesibilidad, pero lo hace re-escalando a la vez
#: accesibilidad y densidad (sólo μ·α y μ·ρ están identificados), y la interfaz
#: lo vendía como «ruido». Se muestra en sólo lectura con esta justificación.
MU_SUELO: Final[float] = 1 / math.sqrt(VIAJES_MES)

#: Viajes por tour casa-trabajo-casa. La elección de modo es POR VIAJE de ida
#: (ida y vuelta simétricas, mismo modo), pero el parking se paga una vez por
#: tour: al llegar al trabajo, no al volver a casa. Por eso `costo_parking` es
#: un costo por DÍA y a cada viaje le toca `costo_parking / VIAJES_POR_TOUR`; al
#: mes suman VIAJES_MES/VIAJES_POR_TOUR = 22 pagos. Tarifa y bencina sí se
#: pagan en cada viaje.
VIAJES_POR_TOUR: Final[int] = 2

#: Fracción de la capacidad real de la vía que usa la BPR del auto: la
#: «capacidad práctica». Los valores α = 0,15 y β = 4 de la BPR se estimaron
#: con esa capacidad, la de nivel de servicio C, ≈ 80 % de la real; usarlos con
#: la capacidad real subestima sistemáticamente la congestión (Boyles, Lownes y
#: Unnikrishnan, *Transportation Network Analysis*, vol. I, p. 102). La
#: capacidad real es la de Greenshields o la `capacidad_pista` explícita, y es
#: contra ella que se reporta el v/c. Constante y no campo (D6 de la auditoría,
#: oct-2026): es parte de la definición de la BPR, no una política.
FACTOR_CAPACIDAD_PRACTICA: Final[float] = 0.8
