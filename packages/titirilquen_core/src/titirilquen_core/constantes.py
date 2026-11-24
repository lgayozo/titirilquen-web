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

#: Especificación `umbrales="suaves"` (oct-2026, ver `demand/utility.py`).
#: Pendiente (1/min) del corte CMNL de caminata y bici, `ln φ = −ln(1 +
#: e^{ω(t − corte)})`: φ pasa de 0,92 a 0,08 en ±5 min alrededor del corte.
#: Supuesto, no calibrado.
OMEGA_CORTE_SUAVE: Final[float] = 0.5

#: Umbral de percepción multiplicativo de la dominancia del metro por caminar
#: directo (Cascetta y Papola 2009, ec. 3): el metro es dominado cuando su
#: tiempo generalizado supera `a` veces el de caminar. Supuesto, no calibrado.
A_DOMINANCIA_METRO: Final[float] = 1.2

#: Pendiente (1/min generalizado) de esa dominancia suave. Supuesto.
OMEGA_DOMINANCIA_METRO: Final[float] = 0.25

#: Valor social del tiempo, $/hora-pasajero. Precios Sociales 2026 del Sistema
#: Nacional de Inversiones, Tabla 2.1, «Viaje en vehículo».
#:
#: **Se actualiza cada año.** Es un valor de norma, no una calibración: entra en
#: la evaluación social (costo del tiempo agregado), no en la elección de modo,
#: que usa el valor del tiempo CONDUCTUAL de cada estrato.
#:
#: Esta constante y las `PRECIO_SOCIAL_*` de abajo son sólo los valores POR
#: DEFECTO de `SimulationConfig.precios_sociales`: el cálculo lee la
#: configuración, que se edita en la página Calibración y viaja con el
#: escenario. Acá queda la vigencia que trae el simulador de fábrica.
VOT_SOCIAL_CLP_HORA: Final[float] = 3338.0

#: Año de los precios sociales por defecto.
VIGENCIA_PRECIOS_SOCIALES: Final[int] = 2026

#: Ponderadores del SNI (tabla 2.1) para el tiempo de espera y de acceso
#: caminando del transporte público mayor, sobre el tiempo en vehículo. El
#: viaje entero a pie NO está en esa tabla: pondera 1.
PONDERADOR_SNI_ESPERA: Final[float] = 2.0
PONDERADOR_SNI_ACCESO: Final[float] = 2.0

# Precios Sociales 2026 (MDSF, `reference/Precios-Sociales-2026.pdf`), moneda
# del 31 de diciembre de 2025. Valores de norma: se actualizan cada año. Entran
# sólo al costo de recursos de `bienestar.py`, nunca a la elección de modo.

#: Combustible del automóvil, $/litro (tabla 4.3). Sin impuesto específico ni
#: IVA: es lo que le cuesta a la sociedad, no lo que paga el conductor.
PRECIO_SOCIAL_COMBUSTIBLE_AUTO_CLP_L: Final[float] = 760.0

#: Lubricante ($/litro), neumático ($/unidad) y vehículo nuevo ($) del
#: automóvil (tabla 4.4), y mano de obra de mantenimiento ($/hora, tabla 4.5).
PRECIO_SOCIAL_LUBRICANTE_AUTO_CLP_L: Final[float] = 8740.0
PRECIO_SOCIAL_NEUMATICO_AUTO_CLP: Final[float] = 87543.0
PRECIO_SOCIAL_VEHICULO_AUTO_CLP: Final[float] = 11360008.0
PRECIO_SOCIAL_MANTENCION_CLP_H: Final[float] = 6931.0

#: Precio de MERCADO de la bencina, $/litro: lo que paga el conductor, con
#: impuestos. NO es de norma. 1.086 es el que resulta de suponer que el 30 % del
#: precio es impuesto (supuesto de trabajo, nov-2026): 760 / (1 − 0,30). Es el
#: default de `demand.globales.precio_combustible_clp_l`, la palanca «Bencina».
PRECIO_MERCADO_COMBUSTIBLE_CLP_L: Final[float] = 1086.0

#: Precio social del carbono, $/tonelada de CO₂ equivalente (tabla 5.1).
PRECIO_SOCIAL_CARBONO_CLP_T: Final[float] = 71801.0

#: Viajes de conmutación por mes (2 por día laboral × 22 días). Convierte el
#: costo por viaje en carga mensual costo/ingreso (D-27) y el logsum por viaje en
#: la accesibilidad mensual que entra a la puja por suelo (D-34): el arriendo
#: `p` y el ingreso `y` son mensuales, así que el término de transporte también.
VIAJES_MES: Final[int] = 44

#: Tolerancia del loop acoplado suelo↔transporte, en $/hogar-mes: el acoplado
#: convergió cuando `max_h max_i |Φ(T) − T|_{h,i} / λ_h` baja de este valor
#: (D10 de la auditoría). En pesos y no en utiles porque λ_h varía ~3,9× entre
#: estratos: 1 util/mes —la tolerancia anterior— eran 806 a 3.122 $/mes según el
#: estrato. Con el paso exterior 1 la brecha de la base cae de ~130 a ~4 $/mes
#: en una vuelta y a 0 en la siguiente; con ρ = 54, a 0 en la cuarta; con la
#: población ×2,5 baja de ~1.140 a ~32 y queda entre 1,6 y 3,2 (medido,
#: docs/libro cap. 6, `paso`): 100 corta en la vuelta 2 sin dejar nada
#: relevante sobre la mesa.
TOL_ACOPLADO_CLP_MES: Final[float] = 100.0

#: Tope de vueltas del loop acoplado: default y cota de TODOS sus consumidores
#: (núcleo, API, worker, página acoplada y comparador; D-61). Antes eran 5 / 3 /
#: 3 / 12 / 8 y la API rechazaba el 12 de la interfaz. Con el paso exterior 1
#: la base corta en la vuelta 2 y los casos exigentes medidos en la 4 (ver
#: `TOL_ACOPLADO_CLP_MES`), así que 10 deja margen; la API lo usa además como
#: cota porque cada vuelta corre un MSA entero.
VUELTAS_ACOPLADO_MAX: Final[int] = 10

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
