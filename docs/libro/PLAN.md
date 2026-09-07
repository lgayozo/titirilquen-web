# El libro de Titirilquén — plan

**Fecha:** 6 de septiembre de 2026. **Estado:** propuesta; las decisiones de la
sección 5 están abiertas.

Un libro por módulo que contenga, de forma estructurada y verificable, la
teoría, el cotejo con el código, los parámetros y su origen, los resultados,
las pruebas, las auditorías y las discusiones del simulador. Y una auditoría
nueva del repo completo, desde la arquitectura hasta los resultados, hecha
**como parte** de escribirlo: cada capítulo se audita antes de escribir sus
resultados.

## 0. Punto de partida

Lo que hay hoy ya es un embrión del libro, pero disperso:

- Ocho informes HTML sueltos en `docs/` (`informe-uso-suelo`, `informe-hev`,
  `hev-cuadratura`, `informe-bienestar`, `informe-wardrop`,
  `informe-downs-thomson`, `arquitectura`, `diagrama-flujo`), varios de ellos
  narrando unidades y parámetros anteriores a D-34.
- Tres sandboxes con figuras y JSON (`sandbox/hev-paso-a-paso`,
  `impacto-hev`, `impacto-rho`).
- 44 discrepancias (`DISCREPANCIES.md`) y 13 hallazgos (`AUDITORIA_USO_SUELO.md`).
- 141 tests en 21 archivos, 16 scripts de auditoría y diagnóstico.
- Ocho tutoriales MDX dentro de la app, en español e inglés.
- `tools/renderiza_ecuaciones.js` (LaTeX → MathML pre-renderizado) y
  `tools/verifica_mapa.py` (punteros `archivo:línea` verificados en `pytest`,
  hoy sólo sobre `arquitectura.html`).

## 1. Qué es el libro

Un capítulo por módulo del núcleo, todos con la misma plantilla. El orden sigue
las dependencias del código: es el orden en que se puede auditar sin supuestos
hacia adelante.

| Cap. | Módulo | Código | Material existente que se absorbe |
| --- | --- | --- | --- |
| 1 | La ciudad lineal | `city.py`, `CityConfig` | tutorial 02, D-26, D-28 |
| 2 | Oferta de transporte | `supply/car`, `supply/bike`, `supply/train`, `supply/oferta` | tutorial 03, `informe-wardrop`, D-12, D-16, D-18, D-21 |
| 3 | Demanda y elección modal | `demand/utility`, `demand/choice`, `population`, `presets` | tutorial 04, `diagnostico_calibracion`, D-01…D-05, D-33 |
| 4 | Equilibrio de transporte | `equilibrium/msa`, `emissions` | tutoriales 05 y 06, `informe-downs-thomson`, `informe-wardrop`, D-10, D-29, D-39 |
| 5 | Uso de suelo: oferta y subasta | `land_use/supply`, `equilibrium`, `hev`, `allocation`, `ciudad` | `informe-uso-suelo`, `informe-hev`, `hev-cuadratura`, los tres sandboxes, AU-01…AU-13, D-08, D-25, D-31, D-32 |
| 6 | Accesibilidad y acoplamiento | `land_use/accesibilidad`, `coupled` | D-14, D-22, D-23, D-24, D-34, D-40, D-42 |
| 7 | Bienestar e indicadores | `bienestar`, `coupled_metrics` | `informe-bienestar`, D-27, D-35…D-38 |
| 8 | Contrato y runtimes | `serializacion`, API, worker, `src/lib/gen`, goldens | `arquitectura.html`, `diagrama-flujo.html`, C-02 |
| 9 | Calibración: de dónde sale cada número | `presets`, `land_use/config`, SNI, el original | `COMPARACION_ORIGINAL`, D-33, D-34, β = 1/√44 |
| 10 | Consistencia entre módulos | transversal | `test_vot_consistente`, `test_linea_base`, unidades (D-26, D-27) |

### La plantilla de cada capítulo

Siete secciones, fijas y en este orden:

1. **Teoría.** Las ecuaciones con su fuente: Martínez (2018), Train (2009),
   Boyles et al., Precios Sociales 2026 del SNI, el Overleaf original.
2. **Cotejo con el código.** Tabla ecuación ↔ función con `archivo:línea`, y
   las diferencias explícitas (qué se simplificó, qué se corrigió, qué se
   extendió).
3. **Parámetros.** Cada número con su origen: *estimado*, *norma*, *heredado
   del original*, *decisión declarada*. Ninguno sin etiqueta.
4. **Resultados.** La línea base del módulo y sus figuras, todas generadas por
   script (ver §2).
5. **Pruebas.** Qué invariante fija cada test del módulo y qué **no** cubre.
6. **Auditorías.** Los hallazgos AU/D del módulo con su estado, más la ficha
   de la auditoría nueva (ver §3).
7. **Discusión.** Decisiones tomadas, alternativas medidas y descartadas,
   pendientes con nombre.

## 2. Infraestructura primero, para que el libro no mienta

Tres mecanismos que distinguen esto de «más informes». Van antes que cualquier
capítulo, porque sin ellos el libro se desfasa en el primer commit (el mapa de
arquitectura se desfasó cuatro veces sólo en la semana del 1 al 6 de
septiembre).

- **Punteros verificados.** Extender `tools/verifica_mapa.py` a todos los
  capítulos: cada `archivo:línea` del libro se comprueba en `pytest`, igual que
  hoy con `arquitectura.html`. Cuando un símbolo se mueve, el test dice dónde
  quedó y se corrige el número, nunca el test.
- **Números generados, nunca tipeados.** Cada capítulo tiene un
  `datos_capNN.py` que escribe un JSON (el patrón de `docs/_datos_informe` y
  de los sandboxes), y el HTML lee de ahí. Un test regenera los JSON y falla
  si el diff no es vacío: el mismo mecanismo que `sync:core` y los goldens.
  Una línea base que cambia obliga a regenerar el capítulo, y el commit lo
  declara.
- **Ecuaciones en MathML** con `tools/renderiza_ecuaciones.js`: LaTeX en
  `data-tex`, pre-renderizado, sin dependencia externa en el navegador.

Más un `docs/libro/index.html` con el índice, el estado de cada capítulo
(*borrador* / *auditado* / *vigente*) y la fecha del último dato regenerado.

Estructura propuesta:

```
docs/libro/
  PLAN.md                 este documento
  index.html              índice y estado
  plantilla.html          la plantilla de capítulo
  capNN-nombre.html       un archivo por capítulo
  datos/
    datos_capNN.py        genera datos/capNN.json
    capNN.json            los números que el capítulo muestra
  figuras/capNN-*.png     generadas por datos_capNN.py
```

## 3. La auditoría, capítulo por capítulo

Cada capítulo se audita **antes** de escribir sus secciones 4 a 7, con el
mismo protocolo:

- **(a) Lectura estática** ecuación ↔ código: la sección 2 es el producto.
- **(b) Reproducción y sensibilidad**: la línea base del módulo y un barrido
  de sus parámetros con el script del capítulo; dirección y magnitud contra lo
  que predice la teoría.
- **(c) Invariancias** que deben cumplirse: resolución de la grilla, escala de
  población, unidades, normalizaciones libres (β·α, nivel de λ).
- **(d) Consistencia con los módulos anteriores**: mismas unidades, misma
  población, mismo hogar (VoT, D-33/D-34).
- **(e) Lo que la UI dice contra lo que el núcleo calcula**: etiquetas,
  unidades en rótulos, «convergió» vs «terminó» (la lección de la auditoría
  externa del 2026-09-05, D-39).

Los hallazgos van a `DISCREPANCIES.md` como D-45 en adelante, con evidencia,
veredicto y estado, y de ahí a la sección 6 del capítulo. Los pendientes
parciales de la auditoría externa entran por esta vía:

- Cap. 4: mostrar `gap_final_min` en la tabla de transporte y decidir si el
  criterio de parada del MSA usa la brecha (mueve la línea base; es cambio de
  modelo y hay que declararlo).
- Cap. 5: exigir balance de hogares (`Σ_i S_i·Q_hi = H_h`) al declarar
  convergencia HEV.
- Cap. 6: los redondeos aceptados de D-44 (población entera que conserva `S_i`
  y no `H_h`; medio tramo en auto y bici), o corregirlos y declarar la línea
  base.

## 4. Secuencia

1. **Fase 0 — esqueleto y verificación.** Índice, plantilla, verificador de
   punteros extendido, pipeline de datos con su test, migración de
   `arquitectura.html` y `diagrama-flujo.html` al capítulo 8. Es la fase que
   decide si el resto vale la pena: si el verificador y el pipeline no quedan
   en `pytest`, no se escribe ningún capítulo.
2. **Fase 1 — capítulos 1 a 4 (transporte).** Son los que menos auditoría
   formal tienen. `informe-wardrop` e `informe-downs-thomson` se absorben.
3. **Fase 2 — capítulos 5 a 7 (suelo, acoplado, bienestar).** Donde más
   material hay y donde se concentró el cambio de septiembre de 2026. Los
   informes actuales se migran y se **actualizan**: todos narran las unidades
   y parámetros anteriores a D-34.
4. **Fase 3 — capítulos 8 a 10 y el dictamen.** Contrato, calibración,
   consistencia, y un dictamen consolidado: qué está validado, qué es decisión
   declarada, qué falta para uso aplicado.

Cada capítulo cierra con la suite verde, el índice al día y un commit propio
cuyo mensaje dice qué se auditó, qué se encontró y qué se decidió. Ningún
capítulo se declara *vigente* con un puntero roto o un JSON desfasado.

## 5. Decisiones abiertas

- **Dónde vive.** Propuesta: `docs/libro/` como HTML estático, hermano de los
  informes actuales y desplegable con la app. Alternativa: MDX dentro de la
  app, como los tutoriales — más integrado, pero acopla el libro al build del
  frontend y lo vuelve más difícil de leer fuera de él.
- **Los tutoriales.** ¿Siguen siendo la versión para estudiantes y el libro la
  versión para autores, o el libro los reemplaza? Cambia la profundidad de la
  sección 1 de cada capítulo.
- **Los informes existentes.** Migrarlos al capítulo correspondiente
  (recomendado: hoy contradicen las unidades vigentes) o dejarlos como
  antecedente histórico enlazado.
- **Idioma.** Español, como todo el repo. ¿Versión en inglés a futuro, como los
  tutoriales?

## 6. Riesgos y cómo se acotan

- **El libro se desfasa del código.** Es el riesgo principal y el que resuelve
  la fase 0: punteros y números verificados en `pytest`.
- **La auditoría encuentra un cambio de modelo a mitad de un capítulo.** Regla:
  se registra la discrepancia, se decide, se corrige, se regeneran los datos y
  recién entonces se escriben los resultados. Nunca se escribe sobre un estado
  que se sabe que va a cambiar.
- **Alcance.** La plantilla es fija y mínima; lo que no cabe en sus siete
  secciones va a `DISCREPANCIES.md` o a un sandbox, no al capítulo.
