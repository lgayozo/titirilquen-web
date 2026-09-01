# La subasta heteroscedástica, resuelta a mano

Side project. Resuelve el equilibrio de la subasta de suelo en el caso más
simple que existe —**dos estratos, cinco parcelas**— paso a paso, lo dibuja, y
lo verifica contra tres cosas independientes.

No es parte del núcleo ni del frontend: no lo importa nadie, no corre en CI, no
tiene tests. Es un banco de pruebas para poder afirmar, con evidencia, que el
módulo de uso de suelo resuelve lo que dice resolver.

## Para qué

«El modelo converge» no demuestra nada. El módulo real itera sobre doscientas
parcelas y tres estratos, y lo único que se ve del lado de afuera es un mapa que
parece razonable — que es exactamente lo que también se vería si el algoritmo
convergiera al lugar equivocado.

Acá el problema es tan chico que se puede resolver por métodos que no comparten
supuestos y comparar los números.

## El hallazgo que lo hace dibujable

Con dos estratos el equilibrio se reduce a **una ecuación escalar en una
incógnita**:

- `ū` tiene dos componentes, pero el modelo la determina sólo salvo una constante
  aditiva (por eso el núcleo hace `u_new -= u_new[0]`). Queda un grado de
  libertad, `δ = ū_Bajo − ū_Alto`.
- De las dos condiciones de equilibrio sólo una es independiente: sumarlas da
  `ΣS = ΣH`, que es una condición sobre los **datos**, no sobre `ū`.

O sea que la subasta entera es encontrar la raíz de una función escalar, y esa
función se puede dibujar en un solo eje.

## Correr

```bash
cd sandbox/hev-paso-a-paso
uv run python pasos.py      # los 10 pasos, y escribe salida/traza.json
uv run python figuras.py    # las 6 figuras, leídas del JSON
uv run python cuenta.py     # dónde y cuántas veces se resuelve el HEV
```

## ¿En qué momento se resuelve el logit heteroscedástico?

En ninguno en particular: es la operación **más interna**, y se resuelve entera
cada vez que se pide un valor de la función de exceso.

```
exceso(δ)                 ← un punto de la curva
 └─ colocados(ū)
     └─ q_hev(loc, θ)     ← ACÁ. El HEV entero, una vez.
         └─ _PESO @ z     ← la cuadratura, 401 nodos
```

Son **dos problemas anidados, no dos pasos en secuencia**:

- **El modelo de elección** (dadas las pujas y θ, ¿quién gana?) no es iterativo.
  Es una integral sin forma cerrada, y la cuadratura la resuelve a precisión de
  máquina de una sola pasada.
- **El equilibrio** (¿qué `ū` coloca a todos?) sí es iterativo, y llama al
  anterior en cada paso.

Medido con `cuenta.py`: una evaluación de `g(δ)` son 4.010 evaluaciones del
integrando; el balanceo entero, 68.170; dibujar la curva de la Fig. 01, 3.216.020.

Después abrir `informe.html`. **Necesita servirse por HTTP**, no por `file://`,
para que resuelvan las rutas relativas a `salida/` y a `../../docs/`:

```bash
python -m http.server 8123 --directory ../..
```

y entrar a `http://localhost:8123/sandbox/hev-paso-a-paso/informe.html`.

## Archivos

| archivo | qué es |
| --- | --- |
| `caso.py` | Los datos del problema. Nada se resuelve acá: es el enunciado. |
| `subasta.py` | La matemática, reimplementada desde el papel. **No importa el núcleo a propósito.** |
| `pasos.py` | La corrida: imprime los 10 pasos y deja `salida/traza.json`. |
| `figuras.py` | Las 6 figuras. No calcula nada: todo sale del JSON. |
| `cuenta.py` | Cuenta cuántas veces se resuelve el HEV en una corrida. Responde a «¿en qué momento se resuelve?». |
| `informe.html` | La presentación. Todos sus números salen de la traza. |
| `salida/` | Generado. Va versionado para que el informe se pueda leer sin correr Python. |

## Las verificaciones

| qué | resultado |
| --- | --- |
| Bisección pura contra el balanceo del núcleo | coinciden en `3,45·10⁻¹²` |
| Reimplementación independiente contra `titirilquen_core` | `δ` a `8,96·10⁻¹¹`, `Q` a `2,24·10⁻¹¹` |
| 100.000 subastas simuladas hogar por hogar | error máximo `0,0016`, dentro de `±1/√n = 0,0032` |
| Reducción al logit cerrado con `θ` uniformes | `3,33·10⁻¹⁶` |
| Unicidad: la función de exceso es monótona | verificado en 25 puntos de `[−6, 6]` |

La tercera es la más fuerte: no usa ninguna fórmula, y verifica de paso el
corrimiento `θ_h·ln(H_h)` —la parte de la formulación más fácil de escribir
mal—, porque la simulación saca las `H_h` pujas una por una y nunca lo usa.

## Lo que NO demuestra

- Es un caso de **dos** estratos. Con tres hay dos incógnitas y el argumento de
  monotonía en una dimensión ya no aplica: la unicidad en la ciudad completa
  sigue siendo una conjetura, no un teorema.
- No valida los parámetros. Que el modelo se resuelva bien no dice que α, ρ o λ
  tengan los valores correctos.
- La 4ª condición de equilibrio de Alonso sigue sin estar, así que los precios
  quedan determinados salvo una constante. Por eso se mira el gradiente y no el
  nivel.

## Relacionado

- `docs/informe-hev.html` — el informe del módulo real.
- `docs/hev-cuadratura.html` — de dónde sale la integral que este demo usa como
  caja negra.
- `docs/AUDITORIA_USO_SUELO.md` AU-06, `docs/DISCREPANCIES.md` D-08 — el problema
  de identificación de λ que el paso 9 demuestra resuelto.
