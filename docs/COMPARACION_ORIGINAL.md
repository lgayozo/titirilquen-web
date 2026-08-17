# Comparación con el simulador original

Contraste entre esta web y el simulador **Titirilquen** original
([github.com/lehyt2163/Titirilquen](https://github.com/lehyt2163/Titirilquen)),
del que este proyecto es trabajo derivado — ver [`NOTICE.md`](../NOTICE.md) para
la atribución.

**Veredicto en una línea:** el esqueleto matemático es el mismo; la calibración
es otra, y en tres puntos el original tenía errores que esta versión corrige.

Agosto 2026 · rama `ciudad-equilibrio-mejoras` · original en `fe66d0b`.

> **Cifras re-medidas el 2026-08-16** con `scripts/comparar_original.py`. El
> bid-rent (§6.4) reproduce al decimal; la tabla de reparto modal (§4.1) se
> movió ~1 pp respecto de la primera redacción, por la recalibración posterior
> del núcleo, y está actualizada acá. Ninguna conclusión del documento cambia.

## Cómo reproducir estas cifras

El código original **no está versionado** aquí (repo aparte, GPL-3.0). Clónalo a
`reference/`, que está en `.gitignore`:

```bash
git clone https://github.com/lehyt2163/Titirilquen.git reference/titirilquen-original
```

Y corre, desde `packages/titirilquen_core` (~1 min):

```bash
uv run python scripts/comparar_original.py
```

Todas las tablas de este documento salen de ahí. El script **ejecuta** ambas
implementaciones en vez de compararlas por lectura; extrae las funciones puras
del original con `ast` porque `app.py` es una app Streamlit y un `import`
levantaría la UI.

> **Alcance.** Cubre el núcleo de **transporte** (§1–§4) y el módulo **Ciudad /
> uso de suelo** (§5). La comparación código ↔ Overleaf es un ejercicio distinto
> y vive en [`DISCREPANCIES.md`](DISCREPANCIES.md).

---

## 1. La estructura es la misma

Verificado ejecutando ambas implementaciones sobre las mismas entradas:

| Componente | Veredicto |
| --- | --- |
| BPR + Greenshields (auto) | **Idéntico** — diferencia 0.00e+00 en 4 de 5 casos |
| Utilidad logit multinomial | Misma forma: `ASC + β·t + β·c + Σ penalizaciones escalonadas` |
| Paso del MSA | Mismo, `f = 1/(it+1)` |
| Arranque en flujo libre | Mismo (`t_espera = 5`, `t_acceso = 10` en la iteración 0) |
| Bici (BPR + factor de pendiente) | Misma forma, misma constante `0.9992` |

La única diferencia en el auto aparece en `ancho = 3.0 m` exacto: el original
cae al factor 0,75 (`3 < a`) y esta versión aplica 0,9 (`a >= 3.0`), que es lo
que dice el Overleaf. Con el slider de paso 0,1 ese punto es alcanzable, así que
importa. Corrección deliberada.

## 2. Tres correcciones estructurales

### 2.1 El factor de saturación de andén tenía el signo invertido

Original: `factor = 1 si ρ ≤ 1, else 0.5·ρ⁴`. Actual: `factor = 1 + 0.5·ρ⁴`.

| ρ = carga/capacidad | original | actual |
| --- | --- | --- |
| 1,0000 | 1,000 | 1,500 |
| **1,0001** | **0,500** | 1,500 |
| 1,05 | 0,608 | 1,608 |
| 1,20 | 1,037 | 2,037 |

Al cruzar la saturación la espera **se partía a la mitad**, y recién en ρ = 1,189
volvía a superar el valor no saturado. Salto discontinuo y con el signo al revés:
el sistema premiaba saturarse. El actual usa una BPR continua y monótona.

### 2.2 El original no cobraba por detenerse

En el original `t_viaje = distancia / v_tren`, sin término de detención: agregar
estaciones acortaba el acceso **sin ningún costo**, y el óptimo de número de
estaciones era degenerado en infinito. Esta versión suma `0,5 min` por parada
intermedia (ni la de subida, donde el viajero ya va adentro, ni la del CBD, donde
se baja).

Viajero a 5 km del CBD, ciudad de 20 km:

| n° estaciones | t acceso | t marcha | t detención | total |
| --- | --- | --- | --- | --- |
| 4 | 15,63 | 8,57 | 0,00 | 24,20 |
| 10 | 6,25 | 8,57 | 0,50 | 15,32 |
| **20** | 3,12 | 8,57 | 2,00 | **13,70** |
| 40 | 1,56 | 8,57 | 4,50 | 14,63 |
| 80 | 0,78 | 8,57 | 9,50 | 18,85 |

Con el término de detención aparece un óptimo interior (~20 estaciones para este
viajero). En el original la columna «detención» es 0 en toda la tabla.

### 2.3 El original no declaraba convergencia: la asumía

`MAX_ITER = 12` fijo, sin criterio de tolerancia, y al terminar imprimía
«Equilibrio Alcanzado» pasara lo que pasara. Esta versión corta por residuo y
reporta si convergió (D-10 en [`DISCREPANCIES.md`](DISCREPANCIES.md)).

## 3. Los parámetros

### 3.1 El valor subjetivo del tiempo era insostenible

VST implícito = `(b_tiempo_viaje / b_costo) × 60`. Referencia: VST social del
SNI 2026 = **$3.338/h**.

| Estrato | Original $/h | Actual $/h | Original / SNI |
| --- | --- | --- | --- |
| Alto | **41.250** | 6.200 | 12,4× |
| Medio | 9.930 | 3.100 | 3,0× |
| Bajo | 1.500 | 1.600 | 0,4× |

$41.250/h para el estrato alto es más de doce veces el valor social. Nota
metodológica: **`b_tiempo_viaje` no se movió en ningún estrato** — toda la
corrección se hizo vía `b_costo`, que reescala el VST sin tocar las razones entre
tiempos.

### 3.2 La espera pesaba menos que el tiempo en vehículo

| Estrato | espera/viaje orig. | espera/viaje act. | caminata/viaje orig. | caminata/viaje act. |
| --- | --- | --- | --- | --- |
| Alto | 0,91 | 2,00 | 2,73 | 1,70 |
| Medio | **0,73** | 2,00 | 1,33 | 1,70 |
| Bajo | 1,00 | 2,00 | 1,67 | 1,70 |

El original decía que un minuto esperando en el andén molesta **menos** que un
minuto viajando sentado, lo que contradice la literatura empírica (rango habitual
1,5–2,5). Esta versión fija 2,0, el centro de ese rango — y por eso la
sensibilización del [informe de Downs-Thomson](informe-downs-thomson.html) barre
1,5× y 2,5× como piso y techo.

### 3.3 Defaults de oferta

| Parámetro | Original | Actual |
| --- | --- | --- |
| capacidad_tren (pax) | 1200 | 1000 |
| **frec_min (tr/h)** | **10** | **2** |
| frec_max (tr/h) | 20 | 40 |
| num_estaciones | 10 | 10 |
| capacidad ciclovía | 800 | 2500 |
| num_pistas | 2 | 2 |
| costo_parking ($) | 6000 | 2000 |
| tarifa_metro ($) | 800 | 800 |
| bencina ($/km) | 120 | 120 |

`frec_min` no era configurable en el original: iba hardcodeado en la llamada a
`oferta_tren()`. Es el parámetro que más importa — ver §4.2.

## 4. Cuánto cambian los resultados

### 4.1 Reparto modal

Motor **actual** con los parámetros indicados **del original**, todo lo demás
fijo. Esto aísla el efecto de la calibración del efecto de los cambios de código;
no pretende reproducir al original, cuya población, `n_celdas` (1001 vs 201) y
mezcla de estratos también difieren.

| Escenario | %auto | %metro | %bici | %camin | f_op |
| --- | --- | --- | --- | --- | --- |
| Actual (calibración 2026) | 17,0 | 32,7 | 23,0 | 8,0 | 5,9 |
| Betas del original | 22,7 | 34,8 | 17,6 | 5,4 | 6,3 |
| Metro del original (K=1200, fmin=10) | 16,4 | 33,9 | 22,4 | 7,8 | 10,0 |
| Parking $6.000 (original) | 3,2 | 41,0 | 25,5 | 10,9 | 7,4 |

> **Cuidado con la última fila.** El original tenía parking a $6.000 pero también
> un `b_costo` ~6,6× más chico en magnitud. Los dos cambios se compensan en
> parte, así que esa fila **no** representa al original: es la calibración actual
> con un parking que, bajo el `b_costo` de hoy, sobre-castiga al auto.

### 4.2 El piso de frecuencia mataba el mecanismo de Downs-Thomson

Si `f_op ≠ f_teórica`, el piso está mordiendo y la frecuencia **deja de responder
a la demanda**. Sin ese canal no hay efecto Mohring, y sin efecto Mohring no
puede haber Downs-Thomson.

| Escenario | f_op | f_teórica | ¿muerde? |
| --- | --- | --- | --- |
| Actual (frec_min = 2) | 5,9 | 5,9 | no |
| Metro del original (frec_min = 10) | 10,0 | 5,1 | **sí** |

Con `frec_min = 10` la frecuencia queda clavada en el piso. Esto explica por qué
el [informe](informe-downs-thomson.html) necesitó mover el default a `K=1000,
frec_min=2` para que la paradoja fuera observable: no es un ajuste para «hacer
que salga», es remover un tope que bloqueaba el canal causal.

## 5. Otros cambios

- **Mezcla de estratos**: 10/40/50 → **20/50/30** (alto/medio/bajo). La ciudad
  simulada es hoy bastante más rica. Ojo: las auditorías previas a agosto 2026
  midieron sobre 10/40/50, así que sus líneas base no son comparables — ver el
  comentario en [`auditoria_transporte.py`](../packages/titirilquen_core/scripts/auditoria_transporte.py).
- **Emisiones reformuladas**: `factor_emision_auto` / `factor_emision_metro`
  (kg/km) → `factor_flota_auto` + `factor_emision_metro_tren_km`. El metro ahora
  emite por **tren-km**, no por pasajero-km, que es lo correcto: el tren circula
  vayan o no vayan pasajeros.
- **Acceso al metro con beta propio** (`b_tiempo_acceso`); el original reciclaba
  `b_tiempo_caminata`, mezclando el acceso a la estación con el modo caminata.
- **Discretización**: `n_celdas` 1001 (hardcodeado) → 201 configurable.
- **Asignación**: el original solo sorteaba modo por agente (Monte Carlo). Hoy
  hay tres métodos: `montecarlo`, `expected` y `todo_o_nada`.

## 6. Módulo Ciudad (uso de suelo)

Mismo ejercicio sobre `Ciudad2.py` → `land_use/` + `population.py`. El original
mete en un solo archivo lo que la UI presenta separado: el bid-rent y la
generación de población.

### 6.1 El punto fijo es la misma ecuación

Ejecutando ambos solvers sobre las mismas entradas:

| Salida | máx \|dif\| | Veredicto |
| --- | --- | --- |
| `u` (utilidades) | 5,7e-09 | **igual** |
| `p` (precios) | 5,1e-09 | **igual** |
| `Q` (composición) | 2,1e-01 | **distinto** |

Las diferencias en `u` y `p` están por debajo de la tolerancia del propio solver
(1e-8): son ruido de convergencia. El operador de punto fijo —ec. 5.4 de
Martínez, con `logsumexp` y normalización `ū -= ū[0]`— es idéntico.

Lo que difiere es la `Q` final. El original la arma con `log(S_i)`, que es
constante por columna y **se cancela en la normalización**, y omite `log(H_h)`,
que no es constante. El core pondera por `H_h`.

### 6.2 La consecuencia: el original no conserva la población

`Σ_i S_i·Q[h,i]` debe devolver `H_h` — cada estrato coloca exactamente los
hogares que tiene:

| Estrato | H objetivo | Original | Core | Error del original |
| --- | --- | --- | --- | --- |
| Alto | 2.000 | 3.051,8 | **2.000,0** | **+52,6 %** |
| Medio | 5.000 | 3.433,3 | **5.000,0** | −31,3 % |
| Bajo | 3.000 | 3.514,8 | **3.000,0** | +17,2 % |

Le pides 2.000 hogares de estrato alto y coloca 3.052. El core conserva exacto.
Es D-25.

> El test exige `Σ S = Σ H`. Las columnas de `Q` suman 1 (toda parcela se llena),
> así que con capacidad ≠ demanda la conservación es imposible por construcción,
> para cualquier solver — no es un defecto del original.

### 6.3 El equilibrio del original depende de la discretización

Misma ciudad física de 20 km, distinto `n_celdas`; sonda a una **distancia
física fija** de 2 km del CBD:

| n_celdas | Q[alto] original | Q[alto] core |
| --- | --- | --- |
| 51 | 0,5419 | 0,3217 |
| 101 | 0,6333 | 0,3208 |
| 201 | 0,6899 | 0,3203 |
| 401 | 0,7127 | 0,3200 |

Al refinar 8× la grilla el original **deriva un +32 %**; el core se mueve −0,5 %.

La causa: en el original `T[h,i] = |i − CBD|` va en **índices de celda** y `S` en
**hogares por celda**, las dos dependientes de `dx`. Cambiar `n_celdas` reescala
`alpha` y `rho` sin que nadie lo escriba. En la práctica, comparar dos corridas
del original con distinta discretización es comparar dos calibraciones
distintas. El core usa minutos y hogares/km (D-26).

### 6.4 Los parámetros no son comparables sin convertir

Como cambiaron las unidades, los números crudos engañan. Con `dx = 20/1001 km`
y `v_ref = 30 km/h`:

| | Original crudo | Original convertido | Actual | Razón |
| --- | --- | --- | --- | --- |
| `alpha` alto | 1,30 | **32,53** útiles/min | 6,50 | 0,20× |
| `alpha` medio | 1,20 | 30,03 | 6,00 | 0,20× |
| `alpha` bajo | 1,10 | 27,53 | 5,50 | 0,20× |
| `rho` (los tres) | 1,00 | **0,0200** útiles/(hab/km) | 0,10 | 5,00× |

**Leer «alpha 1,3 → 6,5» como un aumento invierte el signo del cambio.** En
unidades comparables el original pesaba el tiempo de viaje **5× más** que hoy, y
castigaba la densidad **5× menos**.

### 6.5 Impacto: dónde vive cada estrato

Motor actual, unidades fijas; solo cambian `alpha`/`rho`/`y` (los del original,
convertidos):

| Calibración | Estrato | d media al CBD | % a menos de 2 km |
| --- | --- | --- | --- |
| Actual | alto | 1,24 km | 81,2 % |
| | medio | 2,95 km | 32,2 % |
| | bajo | 6,36 km | 1,3 % |
| Original (convertido) | alto | **0,70 km** | **99,7 %** |
| | medio | 2,91 km | 25,6 % |
| | bajo | 6,79 km | 0,0 % |

El **ordenamiento cualitativo es el mismo** —ricos al centro, pobres a la
periferia—: eso lo da la estructura del bid-rent, no la calibración. Lo que
cambia es la intensidad: el original apiña al estrato alto casi por completo
dentro de 2 km, y deja la periferia sin un solo hogar de ingresos altos.

### 6.6 Otros cambios del módulo

| | Original (`Ciudad2.py`) | Actual (`land_use/`) |
| --- | --- | --- |
| Ingresos | `[120, 50, 10]` (abstractos) | `[3,5M, 1,5M, 0,5M]` ($/mes) |
| Oferta `S` | **muestreada** (N draws de una normal, sin semilla) | determinista (mayor residuo sobre el perfil analítico) |
| Formas de ciudad | solo normal | 6 (normal, uniforme, exponencial, meseta, bimodal, valle) |
| Asignación a parcelas | barrido por rondas, RNG global sin semilla | mismo algoritmo, RNG inyectable |
| Si `Σ S ≠ Σ H` | imprime y retorna, dejando `parcelas` vacías | lanza `ValueError` |
| Solvers | logit **y** Fréchet | solo logit |
| Banda de densidad | implícita (vía `S` y `rho`) | explícita, `densidad_min/max` = 200/800 |

Dos consecuencias de la primera fila: la ciudad del original **cambia en cada
corrida** (ni `Ciudad2.py` ni `app.py` fijan semilla de `np.random`), y el perfil
de oferta sale dentado por el muestreo en vez de suave.

Los ingresos son los que `app.py` **pasa** al instanciar `Ciudad` (línea 458), no
los del default de la clase (`[100, 20, 4]`), que nunca se usan.

**Peso muerto que sí se fue:** la jornada laboral (`prob_jornada_flexible`,
`prob_part_time`, horas de entrada/salida) se calculaba pero **no entraba en la
utilidad**, ni en el original ni acá — era herencia, no regresión (D-07). En la
cirugía de arquitectura de agosto 2026 esos campos se **eliminaron del schema**:
el reparto modal no se movió ni 0,1 pp, que es la demostración de que estaban
muertos.

**Pendiente:** el bid-rent no está verificado numéricamente contra el original al
mismo nivel que el transporte. Es el siguiente ejercicio si hace falta.
