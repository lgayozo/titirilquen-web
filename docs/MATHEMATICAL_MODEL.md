# Modelo matemático — Titirilquen

Fuente única del modelo implementado en `packages/titirilquen_core`. Refleja el
**código** (fuente de verdad del proyecto). Donde difiere del Overleaf original,
se referencia la entrada de [`DISCREPANCIES.md`](DISCREPANCIES.md).

Notación: ciudad lineal de largo `L` km, discretizada en `N` celdas (`n_celdas`)
de ancho `Δx = L/N`. El CBD está en la celda central `c = ⌊N/2⌋`. La distancia
de la celda `i` al CBD es `d_i = |i − c|·Δx`. Todos los tiempos en minutos.

---

## 1. Demanda — elección de modo (logit multinomial)

Cada agente pertenece a un estrato `s ∈ {1,2,3}` (alto/medio/bajo) y una celda de
origen `i`. La utilidad sistemática de cada modo (`demand/utility.py`):

**Auto** (solo si el agente tiene auto):
```
V_auto = ASC_auto^s + β_tviaje^s · t_auto(i) + β_costo^s · (c_parking + c_comb·d_i)
```
**Metro** (acceso + espera + viaje, cada componente con su β):
```
V_metro = ASC_metro^s + β_tcaminata^s·t_acc + β_tespera^s·t_esp + β_tviaje^s·t_viaje + β_costo^s·c_tarifa
```
**Bici** — penalizaciones **aditivas** escalonadas y corte de factibilidad
(ver [D‑02](DISCREPANCIES.md)):
```
V_bici = −∞            si t_bici > 45
       = ASC_bici^s + β_tviaje^s·t_bici + Σ_k 1{t_bici > τ_k}·π_k^bici,   τ ∈ {10,20,30}
```
**Caminata** — usa `β_tcaminata` (no `β_tviaje`; ver [D‑03](DISCREPANCIES.md)),
umbrales `{5,15,25}` (ver [D‑05](DISCREPANCIES.md)) y corte a 30 min:
```
V_cam = −∞            si t_cam > 30
      = ASC_cam^s + β_tcaminata^s·t_cam + Σ_k 1{t_cam > τ_k}·π_k^walk,   τ ∈ {5,15,25}
con t_cam = d_i / v_caminata · 60
```

**Probabilidad logit** (`demand/choice.py`), sobre los modos factibles `J`:
```
P(m) = exp(V_m) / Σ_{j∈J} exp(V_j)
```
(Los β de cada modo absorben la escala; no hay parámetro de escala separado.)

**Asignación** (config `assignment`):
- `montecarlo`: cada agente sortea su modo con `P(·)` (microsimulación; estocástico).
- `expected`: asignación **fraccional** — la celda `i` recibe `Σ_agentes P(m)` viajes
  de cada modo (determinista, sin ruido entre iteraciones). Recomendado para el
  equilibrio; ver §4.

Iteración 0 (sin congestión): tiempos a flujo libre `d_i/v_m·60`, con `t_acc=10`,
`t_esp=5`.

---

## 2. Oferta

Los tres modos congestionables acumulan flujo **direccionalmente hacia el CBD**
(`q_i = D_i + q_{vecino hacia afuera}`), aplican BPR por tramo e **integran** los
tramos del origen al centro: `t_{i,centro} = Σ_{k=i}^{c} t_k`.

### 2.1 Auto (`supply/car.py`) — Greenshields + BPR
```
v_l = v_max · f_ancho(a)          f_ancho: 1.0 (a≥3.5), 0.9 (3≤a<3.5), 0.75 (a<3)
k_e = 1000 / (l_veh + gap)        (densidad de embotellamiento, veh/km)
Q   = v_l · k_e / 4               (Greenshields, por pista) ;  Q_dir = Q · N_pistas
t_i = (Δx/v_l)·60 · (1 + α·(q_i / Q_dir)^β)
```

### 2.2 Bici (`supply/bike.py`) — BPR + pendiente + piso de caminata
```
f_p = −0.0579·p + 0.9992  (subida, p>0)        ← ver D‑01 (Overleaf escribe 0.09992)
f_p = −0.0455·p + 1       (bajada/plano)
v = clamp(v_media·f_p, 5, 45) ;  t0 = (Δx/v)·60
t_i = min( t0·(1 + α·(q_i/Q)^β),  Δx/v_caminata·60 )      ← piso D‑15
```
El **piso** garantiza que un tramo en bici nunca tarde más que caminarlo (el
ciclista desmonta). Sin él, la BPR acumulada da tiempos absurdos en la periferia
bajo congestión (ver [D‑15](DISCREPANCIES.md)).

### 2.3 Tren (`supply/train.py`) — sistema cíclico
`n_s` estaciones equidistantes (siempre una en el CBD). Cada celda usa la estación
más cercana `s*(i)`. La demanda se acumula por tramo; el tramo crítico fija la
frecuencia:
```
f_op = clip( L_max / K,  f_min,  f_max )
```
Tiempo de viaje = acceso + espera + a bordo:
```
t_acc = |loc(s*) − x_i| / v_caminata · 60
t_viaje = |loc(s*) − x_c| / v_tren · 60
t_esp = (1/(2·f_op))·60 · factor(ρ_s)        ρ_s = carga_s / (f_max·K)
factor = 1                  si ρ_s ≤ 1
       = α_e · ρ_s^β_e      si ρ_s > 1        (código: α_e=0.5, β_e=4)
```
> **Nota (D‑12, D‑16):** el término de congestión de andén solo se activa cuando
> la carga supera `f_max·K` (capacidad a frecuencia máxima), lo que rara vez ocurre
> con ciudades de tamaño normal → la espera queda plana. Además las constantes del
> código (`α_e=0.5, β_e=4`) **difieren** de las del Overleaf (`α=10, β=10`).
> Pendiente de calibración con los autores.
>
> **Nota (D‑18 — efecto Mohring):** la frecuencia es **endógena a la demanda**
> (`f_op = clip(L_max/K, f_min, f_max)`), por lo que la espera `t_esp ≈ 30/f_op`
> baja cuando sube el patronaje y sube cuando baja — el **efecto Mohring**,
> ingrediente de la paradoja de Downs‑Thomson. Rango por defecto **realista de
> metro**: `f_min = 6` (~10 min, valle) y `f_max = 30` (~2 min, punta). La
> activación de la frecuencia exige `L_max > f_min·K`; por eso la **capacidad por
> tren `K = cap_tren` está calibrada a la escala del modelo (`300`)** — con el
> valor previo (`1200`) el umbral `6·1200 = 7.200` pax/h superaba la demanda típica
> y `f` quedaba clavada en `f_min` (frec_max inerte, espera fija). Con `K=300` la
> frecuencia responde (`f≈7,6`) y `frec_max` muerde. Pruebas empíricas: el canal
> Mohring es **medible** (espera baja al ganar pasajeros) pero **DT no emerge** con
> parámetros realistas, porque la espera es una fracción chica del tiempo total de
> metro (acceso + a bordo dominan) y la sustitución auto↔metro es modesta.
> Ver DISCREPANCIES.md D‑18 y `VERIFICACION_TRANSPORTE.md` H1.

---

## 3. Emisiones de CO₂ (`emissions.py`, ver D‑06)
A partir del estado físico final (flujo de autos y velocidad local vía BPR
inversa):
```
v_local = v_l / (1 + α·(q_auto/Q_dir)^β)
FE_auto(v) = 2467.4 · v^(−0.699)   [g/km],  v ∈ [1,120]
CO₂_auto = Σ_i q_auto(i)·Δx·FE_auto(v_local(i)) / 1000      [kg/h]
CO₂_metro = Σ_tramos carga·(factor_emision_metro·1000)·Δx / 1000
```
Bici y caminata: 0. Se reporta total y por modo (KPI en el Sandbox).

---

## 4. Equilibrio de transporte — MSA (`equilibrium/msa.py`)

Punto fijo demanda↔oferta por **método de promedios sucesivos** sobre los tiempos:
```
T_actual ← f·T_nuevo + (1−f)·T_actual,    f = 1/(it+1)
```
**Criterio de parada** (ver [D‑10](DISCREPANCIES.md) — añadido; el original solo
usaba `MAX_ITER`): converge cuando el residual
```
r = max sobre (modo, celda) |ΔT|          (auto, bici, metro)
```
es `< tolerance` en **2 iteraciones consecutivas**; si no, corta en `max_iter`.
Con `tolerance = 0` se respeta solo `max_iter`. Con `assignment = expected` el
residual decrece monótonamente y la corrida es reproducible.

---

## 5. Uso de suelo — bid‑rent (`land_use/`, ver `Suelo.tex`)

Modelo monocéntrico tipo Alonso‑Muth‑Mills. Utilidad lineal en el ingreso:
```
u_h = λ_h(y_h − p_i) + f_h(i),     f_h(i) = −α_h·T_h(i) − ρ_h·S_i
```
Disposición a pagar (ver [D‑17](DISCREPANCIES.md) — el Overleaf invierte el signo
de `f`):
```
w_h(u,i) = y_h − (u_h − f_h(i))/λ_h
```
Probabilidad de subasta (logit) y operador de punto fijo:
```
Q_hi = H_h·e^{β·w_hi} / Σ_g H_g·e^{β·w_gi}
u* = F(u*),   F(u)_h = (1/β)·ln( Σ_i S_i · e^{β z_hi} / Σ_g e^{β(z_gi − u_g)} ),
z_hi = H_h·e^{β(y_h + f_h(i)/λ_h)}
```
**Oferta `S`** (`land_use/supply.py`, ver [D‑13](DISCREPANCIES.md)): perfil
**determinista** redondeado a `Σ S = Σ H` (CBD excluido), con **forma
parametrizable** (`forma`): `normal` (campana, default), `uniforme`,
`exponencial` (`S ∝ e^{−d/σ}`), `meseta` (núcleo plano con borde neto),
`bimodal` (dos picos a ±`sep`) y `valle` (densidad creciente con la distancia —
triángulo invertido). El ancho/pendiente es `σ = oferta_sigma_frac ·
min(c, N−1−c)` (default 0.5 ⇒ σ≈L/4) y `forma_param` fija `sep` (solo bimodal;
en 1D un anillo coincide con bimodal). Permite estudiar cómo cambia el
equilibrio de asignación según la geometría urbana.

> El propio Overleaf nota que el logit con `λ_h` heterogéneo es inconsistente y
> sugiere logit‑heteroscedástico; el código incluye `solve_frechet` como
> alternativa (marcada "MALA"). Ver [D‑08](DISCREPANCIES.md).

---

## 6. Loop acoplado suelo↔transporte (`coupled.py`, V2 — no está en el Overleaf)

Itera (ver [D‑14](DISCREPANCIES.md)):
1. Resolver uso de suelo dado `T` → distribución de hogares.
2. Generar población y correr MSA → tiempos `T_new[h,i]` (promedio por estrato/celda).
3. Amortiguación MSA exterior: `T_state ← θ·T_new + (1−θ)·T_state`, `θ=1/(n+1)`.
4. Residual `‖T_new − T_state‖_∞`; repetir hasta `outer_tol` o `outer_max_iter`.

Celdas/estratos sin agentes de muestra conservan el valor previo (no se inyecta
ruido). Persiste un piso de residual por el remuestreo estocástico de población.

---

## Referencias
- Martínez, F. *Microeconomic Modeling in Urban Science*, cap. 3–5 (uso de suelo).
- Overleaf original en `reference/overleaf/` (no versionado).
- Divergencias código↔Overleaf y mejoras V2: [`DISCREPANCIES.md`](DISCREPANCIES.md);
  agenda de cambios al paper: [`OVERLEAF_CHANGES.md`](OVERLEAF_CHANGES.md).
