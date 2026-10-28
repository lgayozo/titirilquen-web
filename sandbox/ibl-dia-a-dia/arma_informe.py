"""Escribe `informe.html` entero desde `salida/experimentos.json`, `poblacion.json` y `ciudad4.json`.

    uv run python arma_informe.py
    node ../../tools/renderiza_ecuaciones.js     # data-tex → MathML

Ningún número del informe se tipea a mano: sale del JSON o de una fórmula del
propio `experimentos.py`. Los punteros «archivo:línea» se buscan en el código al
armar, así que no pueden quedar desactualizados.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from experimentos import E1_K, VENTANAS, gauss_logistica

AQUI = Path(__file__).parent
D = json.loads((AQUI / "salida" / "experimentos.json").read_text(encoding="utf-8"))
CASOS = {c["nombre"]: c for c in D["casos"]}
ESTRATO = {1: "Alto", 2: "Medio", 3: "Bajo"}


# --- formato --------------------------------------------------------------------


def num(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}".replace(".", ",").replace("-", "−")


def pp(x: float, n: int = 1) -> str:
    """Diferencia de cuotas en puntos porcentuales, con signo."""
    v = 100 * x
    s = num(abs(v), n)
    return ("+" if v > 0.05 else "−" if v < -0.05 else "") + s


def _atributo(t: str) -> str:
    """`<` y `>` crudos rompen el atributo (y la regex del renderizador): KaTeX tiene \\lt y \\gt."""
    return t.replace("<", "\\lt ").replace(">", "\\gt ")


def tex(t: str) -> str:
    return f'<span class="mat" data-tex="{_atributo(t)}"></span>'


def ec(t: str, n: int) -> str:
    return f'<div class="ecuacion" data-tex="{_atributo(t)}" data-id="({n})"></div>'


def linea(archivo: str, simbolo: str) -> str:
    """`archivo:línea` de `def`/`class simbolo` (o de la primera línea que lo asigna)."""
    texto = (AQUI / archivo).read_text(encoding="utf-8").splitlines()
    patron = re.compile(rf"^\s*((def|class) {simbolo}\b|{simbolo}\s*=)")
    for i, l in enumerate(texto, 1):
        if patron.match(l):
            return f"<code>{archivo}:{i}</code>"
    raise KeyError(f"{simbolo} no está en {archivo}")


def e1(caso, d, k=None, r=None):
    for f in D["e1"]:
        if f["caso"] == caso and f["d"] == d:
            if k is None and f.get("control"):
                return f
            if k is not None and f["k"] == k and f["r"] == r:
                return f
    raise KeyError((caso, d, k, r))


def e2(caso, d, cond, sigma):
    return next(
        f
        for f in D["e2"]
        if f["caso"] == caso and f["d"] == d and f["condicion"] == cond and f["sigma"] == sigma
    )


def fig(archivo: str, n: int, texto: str) -> str:
    return (
        f'<figure><img src="salida/{archivo}" alt="Figura {n}">'
        f'<figcaption><span class="n">Figura {n}</span>{texto}</figcaption></figure>'
    )


def tabla(n: int, nombre: str, cabecera: str, filas: str, explicacion: str) -> str:
    """Tabla con número y nombre arriba y, abajo, qué contiene y cómo leerla."""
    return (
        f'<p class="titulo-tabla"><span class="n">Tabla {n}</span>{nombre}</p>\n'
        f'<div class="envoltorio-tabla"><table>\n  <thead>{cabecera}</thead>\n'
        f"  <tbody>{filas}</tbody>\n</table></div>\n"
        f'<p class="pie-tabla">{explicacion}</p>'
    )


C1, C2, C3 = CASOS["C1"], CASOS["C2"], CASOS["C3"]
BETA = abs(C2["beta"])
RUIDO_LOGIT_MIN = 3.14159265 / 3**0.5 / BETA
DS = (0.0, 0.5, 1.28)
H_TXT = {"corto": "corto (1–10)", "medio": "mediano (11–50)", "largo": "largo (51–250)"}

P = json.loads((AQUI / "salida" / "poblacion.json").read_text(encoding="utf-8"))


def pob(sigma, d):
    return next(f for f in P["filas"] if f["sigma"] == sigma and f["d"] == d)


def ultimos(serie):
    return sum(serie[-P["ultimos"] :]) / P["ultimos"]


def brecha_min(f):
    """(19): tiempo de red menos tiempo percibido del modo elegido, en minutos."""
    return (ultimos(f["bienestar_decision_por_dia"]) - ultimos(f["bienestar_por_dia"])) / BETA


def delta_exp_min(f):
    """Bienestar experimentado contra σ = 0 (mismo d), en minutos por viaje."""
    f0 = pob(0.0, f["d"])
    return (ultimos(f["bienestar_por_dia"]) - ultimos(f0["bienestar_por_dia"])) / BETA


C4 = json.loads((AQUI / "salida" / "ciudad4.json").read_text(encoding="utf-8"))
COND_TXT = {"auto": "auto", "tp": "metro", "auto_tp": "auto y metro"}


def c4(cond, sigma, d):
    """Fila de E4; con σ = 0 es el control sin ruido, común a las tres condiciones."""
    cond = cond if sigma > 0 else "sin_ruido"
    return next(
        f for f in C4["filas"] if f["condicion"] == cond and f["sigma"] == sigma and f["d"] == d
    )


def delta_exp_c4(f):
    """Bienestar experimentado de E4 contra su control sin ruido (mismo d), en minutos por viaje."""
    f0 = c4(None, 0.0, f["d"])
    return (ultimos(f["bienestar_por_dia"]) - ultimos(f0["bienestar_por_dia"])) / BETA


# --- verificaciones que el texto afirma -----------------------------------------
# (9) contra simulación con d = 0: deben coincidir exactamente (sin ruido, el orden no importa).
err_d0 = max(
    abs(f["p_post_sim"] - f["p_post_analitica"])
    for f in D["e1"]
    if not f.get("control") and f["d"] == 0.0 and f["llegan_a_k"] > 0
)
err_d = {
    d: max(
        abs(f["p_post_sim"] - f["p_post_analitica"])
        for f in D["e1"]
        if not f.get("control") and f["d"] == d and f["llegan_a_k"] > 0.5
    )
    for d in (0.5, 1.28)
}
# (17) la aproximación normal de la ventaja percibida reproduce S.
err_normal = max(
    abs(gauss_logistica(q["m"], q["s"]) - q["S"])
    for f in D["e2"]
    for q in f["descomposicion"].values()
)
pve_max = min(f["descomposicion"]["largo"]["pve"] for f in D["e2"])
# Φ de largo plazo con ruido en ambos modos y σ = 80, según el decaimiento.
PHI_BAJO = [e2(c, d, "ambos", 80.0)["phi"]["largo"] for c in CASOS for d in (0.0, 0.5)]
PHI_ALTO = [e2(c, 1.28, "ambos", 80.0)["phi"]["largo"] for c in CASOS]
assert all(f["descomposicion"][w]["pve"] <= 1e-9 for f in D["e2"] for w in VENTANAS)
# §1 dice que en la ciudad, con σ = 80 y d = 0,5, el largo plazo conserva «toda» la ventaja.
assert pob(80.0, 0.5)["phi"]["todos"]["largo"] > 0.98

# --- portada e índice -------------------------------------------------------------

cabeza = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Titirilquen — Aprender el modo día a día</title>
<link rel="stylesheet" href="../../docs/libro/libro.css">
<style>
  /* Lo propio de este informe: figuras y tablas numéricas. El resto es libro.css. */
  figure {{ margin: 22px 0 8px; }}
  figure img {{ width: 100%; display: block; border: 1px solid var(--rule); }}
  figcaption {{
    font-family: "Segoe UI", system-ui, sans-serif; font-size: 12px; color: var(--muted);
    margin-top: 6px; max-width: 78ch; line-height: 1.5;
  }}
  figcaption .n, .titulo-tabla .n {{
    font-weight: 700; color: var(--accent); letter-spacing: .1em; text-transform: uppercase;
    margin-right: 8px; font-size: 11px;
  }}
  .titulo-tabla {{
    font-family: "Segoe UI", system-ui, sans-serif; font-size: 13px; font-weight: 600;
    margin: 22px 0 0; color: var(--ink);
  }}
  .pie-tabla {{ line-height: 1.5; margin-bottom: 14px; }}
  td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
  @media print {{ figure {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<div class="pagina">

<header class="portada">
  <div class="kicker">Titirilquen · Side project</div>
  <h1>Aprender el modo día a día</h1>
  <p class="bajada">
    Una persona elige cada día entre auto y metro con el tiempo que <em>cree</em>
    que tarda cada uno, y lo aprende de sus experiencias con un modelo por
    instancias (IBL). Dos experimentos: cuántas experiencias malas, y de qué
    tamaño, cambian su conducta (E1), y si más variabilidad en los tiempos
    vuelve la elección más aleatoria (E2), primero para una persona y después para
    la ciudad completa, con congestión (E3), y la ciudad de la app con sus cuatro
    modos y ruido en el auto, en el metro o en los dos (E4). Corto, mediano y largo plazo.
  </p>
  <p class="meta">
    Código: <code>sandbox/ibl-dia-a-dia/</code> · Correr: ver <a href="#reproducir">Reproducir</a><br>
    Escala del logit {tex("\\mu = 1")} (la del simulador) · {D["dias"]} días · {D["replicas"]} réplicas ·
    semilla {D["semilla"]} · núcleo titirilquen-scenario/v11 · 28-oct-2026
  </p>
</header>

<nav class="indice">
  <ol>
    <li><a href="#s1">Preguntas y respuestas cortas</a></li>
    <li><a href="#s2">El modelo</a> — ecuaciones (1)–(6)</li>
    <li><a href="#s3">Los indicadores</a> — ecuaciones (7)–(17)</li>
    <li><a href="#s4">E1 · Experiencias malas al inicio</a></li>
    <li><a href="#s5">E2 · Variabilidad del tiempo</a></li>
    <li><a href="#s6">E3 · La ciudad completa</a> — ecuaciones (18)–(19)</li>
    <li><a href="#s7">E4 · La ciudad con cuatro modos</a> — ecuación (20)</li>
    <li><a href="#s8">Qué concluir, y bajo qué supuestos</a></li>
    <li><a href="#reproducir">Reproducir paso a paso</a></li>
  </ol>
</nav>
"""

# --- §1 -------------------------------------------------------------------------------

f_c2_k1 = e1("C2", 0.5, 1, 2.0)
f_pers = e1("C2", 0.0, 10, 4.0)
s1 = f"""
<!-- ==================================================================== -->
<h2 id="s1"><span class="num">1</span>Preguntas y respuestas cortas</h2>

<p>
  Todo se mide sobre <strong>una persona</strong>: {D["replicas"]} réplicas de la misma
  persona, cada una con su propia secuencia aleatoria. No hay congestión ni
  interacción, salvo en E3, que repite la última pregunta con la ciudad completa. Las ventajas se dan en
  {tex("A")}, la ventaja del modo mejor expresada en minutos (ecuación 6).
</p>
<div class="paso"><h3>¿Qué tan extrema debe ser una experiencia, o cuántas, para cambiar la conducta?</h3><p>
    Para que en el <strong>corto plazo</strong> la persona pase a preferir el modo peor,
    el sobretiempo de cada experiencia mala tiene que superar
    {tex("\\Delta^{*}_k = A / W_k")} (ecuación 8). Con una sola experiencia y memoria sin
    decaimiento eso es {tex("2A")}; con muchas, tiende a {tex("A")}. En el caso intermedio
    (C2, {tex("A")} = {num(C2["ventaja_min"], 0)} min) son
    {num(C2["delta_critico"]["0.5"]["1"], 0)} min con una experiencia y
    {num(C2["delta_critico"]["0.5"]["10"], 0)} min con diez ({tex("d = 0{,}5")}).
  </p></div>
<div class="paso"><h3>¿Existe un valor crítico? ¿Bajo qué supuesto?</h3><p>
    Hay <strong>dos</strong>. El de corto plazo, (8), es exacto con
    {tex("d = 0")} y lo controlan el peso de la percepción inicial (una instancia) y la
    escala {tex("\\mu\\beta")}. El de <strong>persistencia</strong> lo fija la «deuda» que dejan
    los shocks: con {tex("d = 0")} hacen falta {tex("n^{*} = k(r-1) - 1")} experiencias buenas para
    recuperar la preferencia (ecuación 14), y la persona casi no las junta si dejó de
    elegir ese modo. En C2 y con {tex("d = 0")}, diez experiencias de {tex("4A")}
    ({num(4 * C2["ventaja_min"], 0)} min cada una) dejan al
    {num(100 * f_pers["ventanas"]["largo"]["invertidos"], 0)} % de las réplicas prefiriendo el
    modo peor durante los días 51–250.
  </p></div>
<div class="paso"><h3>¿Corto, mediano y largo plazo?</h3><p>
    El efecto típico es <strong>transitorio</strong>: una experiencia de {tex("2A")} baja la cuota del
    mejor {pp(-f_c2_k1["efecto"]["corto"]).lstrip("+")} pp en los días 1–10, {pp(-f_c2_k1["efecto"]["medio"]).lstrip("+")} pp
    en los días 11–50 y {pp(-f_c2_k1["efecto"]["largo"]).lstrip("+")} pp en los días 51–250 (C2, {tex("d = 0{,}5")}).
    Sólo los shocks que cruzan el umbral de persistencia llegan al largo plazo.
  </p></div>
<div class="paso"><h3>¿A mayor varianza del tiempo, la elección tiende a 50-50?</h3><p>
    La <strong>dirección</strong> se confirma: la dispersión de lo percibido siempre acerca la
    probabilidad a ½ (ecuación 17, en las {len(D["e2"])} corridas). Pero con {tex("\\mu = 1")}
    la <strong>magnitud</strong> es chica y sobre todo de corto plazo: con σ = 80 min el término
    más grande es {pp(pve_max)} pp en el largo plazo. Además el hot stove empuja en contra
    cuando el modo peor también tiene ruido: lo evita tras sus malas experiencias y
    se queda más en el mejor. Se acerca a 50-50 sólo con alternativas parejas, el ruido
    en el modo mejor y memoria con mucha recencia. En la ciudad completa (E3) pasa lo mismo:
    con σ = 80 min y {tex("d = 0{,}5")} se conserva el
    {num(100 * pob(80.0, 0.5)["phi"]["todos"]["corto"], 0)} % de la ventaja del modo mejor en el
    corto plazo y toda en el largo (Φ = {num(pob(80.0, 0.5)["phi"]["todos"]["largo"], 2)},
    ecuación 13); la partición no se mueve, pero
    personas iguales terminan distintas y el bienestar percibido sobrestima el vivido (§6.2).
    Con los cuatro modos (E4) el ruido saca viajes hacia la bici, y el promedio esconde signos
    opuestos: quien vive el ruido en su modo mejor pierde ventaja y quien lo vive en una
    alternativa la gana (§7.2).
  </p></div>

<div class="aviso neutro"><p>
  <strong>Por qué todo es «grande» en minutos.</strong> Con {tex("\\mu = 1")} y
  {tex(f"\\beta = {num(C2['beta'], 4)}")} útiles/min (los tres estratos), el ruido del logit
  —la diferencia de dos Gumbel, desviación {tex("\\pi/\\sqrt{3}")}— equivale a
  {num(RUIDO_LOGIT_MIN, 0)} minutos. El IBL estimado con elecciones repetidas de una misma persona
  (datos de laboratorio de Ben-Elia y Shiftan) da {tex("\\beta")} = −0,198 y −0,086 por minuto según la
  ruta (Guevara, Tang y Gao, 2018, tabla 4); su experimento sintético usa −0,4 (tabla 1). Son de 2,6 a
  12 veces el del simulador. Por eso los resultados se dan también en
  múltiplos de {tex("A")}: con {tex("d = 0")} la ecuación (9) depende sólo de {tex("\\Delta V")} y de
  {tex("\\Delta/A")}, y vale para cualquier escala.
</p></div>
"""

# --- §2 -------------------------------------------------------------------------------

filas_casos = "".join(
    f"<tr><td>{c['nombre']}</td><td>{ESTRATO[c['estrato']]}</td><td class='n'>{num(c['km'], 1)}</td>"
    f"<td class='n'>{num(c['t_auto'], 1)}</td><td class='n'>{num(c['t_metro'], 1)}</td>"
    f"<td>{c['mejor']}</td><td class='n'>{num(c['dv'], 3)}</td><td class='n'>{num(c['ventaja_min'], 1)}</td>"
    f"<td class='n'>{num(c['p_verdadera'], 3)}</td></tr>"
    for c in D["casos"]
)
s2 = f"""
<!-- ==================================================================== -->
<h2 id="s2"><span class="num">2</span>El modelo</h2>

<p>
  Cada día {tex("t = 1, \\dots, T")} la persona {tex("n")} elige un modo {
    tex("i \\in \\{\\text{auto}, \\text{metro}\\}")
},
  viaja y guarda la experiencia. El tiempo que <em>percibe</em> de cada modo es un promedio ponderado
  de sus experiencias en ese modo, con pesos que decaen con la antigüedad. Son las ecuaciones (1)–(2)
  de Guevara, Tang y Gao (2018), que toman el IBL de Tang y Gao (2017):
</p>
{ec("w_{ni}(t',t) = \\frac{a_{ni}(t')\\,(t-t')^{-d}}{\\sum_{s=0}^{t-1} a_{ni}(s)\\,(t-s)^{-d}}", 1)}
<ul class="donde">
  <li>{tex("w_{ni}(t',t)")}: peso (adim., entre 0 y 1) de la experiencia del día {
    tex("t'")
} en lo que la
      persona {tex("n")} percibe del modo {tex("i")} al decidir el día {
    tex("t")
}. Los pesos de un modo suman 1.</li>
  <li>{tex("t")}: día de la decisión; {tex("t'")}: un día anterior, de 0 a {tex("t-1")};
      {tex("t - t'")}: antigüedad de esa experiencia (días). {
    tex("s")
} es sólo el índice de la suma.</li>
  <li>{tex("a_{ni}(t')")}: indicador (0 o 1) que vale 1 si ese día eligió {
    tex("i")
}. Sólo cuentan los días
      en que usó el modo.</li>
  <li>{tex("d \\ge 0")}: decaimiento de la memoria (adim.). {
    tex("d = 0")
} da el promedio simple de todas
      las experiencias; con {tex("d")} mayor pesan más las recientes. {tex("d = 0{,}5")} es el valor
      convencional y {
    tex("d = 1{,}28")
} el estimado con datos de laboratorio (Guevara et al. 2018, §3.2 y
      tabla 4). Se corren los tres.</li>
</ul>
{ec("b_{ni}(t) = \\sum_{t'=0}^{t-1} w_{ni}(t',t)\\, x_{ni}(t')", 2)}
<ul class="donde">
  <li>{tex("b_{ni}(t)")}: tiempo de viaje que la persona <em>cree</em> que tarda el modo {
    tex("i")
} el día
      {tex("t")} (min).</li>
  <li>{tex("x_{ni}(t')")}: tiempo que vivió en ese modo el día {tex("t'")} (min), ecuación (5).</li>
  <li>{
    tex("t' = 0")
} es la <strong>percepción inicial</strong>, que cuenta como una experiencia más:
      {tex("a_{ni}(0) = 1")} para los dos modos y {
    tex("x_{ni}(0) = \\tau_i")
}, el tiempo de equilibrio del
      simulador. El paper propone el flujo libre o un planificador de viajes; acá hace de «información de
      buena calidad».</li>
</ul>

<p>
  La utilidad es la del núcleo, <code>calcular_utilidades</code>, evaluada una vez con los tiempos de
  equilibrio. Como es lineal en el tiempo, el día {
    tex("t")
} basta corregirla por la diferencia entre lo
  percibido y el tiempo de equilibrio:
</p>
{ec("V_{ni}(t) = V_i^{\\mathrm{ref}} + \\beta\\,\\bigl(b_{ni}(t) - \\tau_i\\bigr)", 3)}
<ul class="donde">
  <li>{tex("V_{ni}(t)")}: utilidad del modo {tex("i")} para la persona el día {
    tex("t")
} (útiles).</li>
  <li>{
    tex("V_i^{\\mathrm{ref}}")
}: utilidad que da el núcleo con los tiempos de equilibrio (útiles). Incluye
      la constante modal, el costo y el acceso y la espera del metro, que no cambian día a día.</li>
  <li>{tex("\\beta")}: <code>b_tiempo_viaje</code> = {
    num(C2["beta"], 4)
} útiles/min, igual en los tres estratos.</li>
  <li>{tex("\\tau_i")}: tiempo de equilibrio que pondera {
    tex("\\beta")
} (min): el total del auto y el
      tiempo en vehículo del metro.</li>
  <li>{
    tex("b_{ni}(t) - \\tau_i")
}: cuánto más (o menos) cree que tarda que el equilibrio (min).</li>
</ul>
{
    ec(
        "P_n(t) = \\Lambda\\bigl(V_{n,m}(t) - V_{n,p}(t)\\bigr), \\qquad \\Lambda(z) = \\frac{1}{1+e^{-z}}",
        4,
    )
}
<ul class="donde">
  <li>{tex("P_n(t)")}: probabilidad (0–1) de que la persona elija el modo mejor el día {
    tex("t")
}.</li>
  <li>{tex("m")} y {tex("p")}: el modo <strong>mejor</strong> en media (el de mayor {
    tex("V^{\\mathrm{ref}}")
}) y
      el peor. Todo el informe mide la probabilidad del mejor.</li>
  <li>{tex("\\Lambda(z)")}: función logística; {
    tex("z")
} es la diferencia de utilidades (útiles). Es el logit
      binario del simulador con escala {tex("\\mu = 1")}: otra escala multiplicaría {tex("z")}.</li>
</ul>

<p>La experiencia del día es el tiempo verdadero más, según el experimento, un shock o un ruido:</p>
{
    ec(
        "x_{ni}(t) = \\tau_i + \\Delta\\,\\mathbf{1}[\\text{shock}] + \\varepsilon_{ni}(t), \\qquad \\varepsilon_{ni}(t) \\sim \\mathcal{N}(0, \\sigma_i^2)",
        5,
    )
}
<ul class="donde">
  <li>{
    tex("x_{ni}(t)")
}: tiempo que vive la persona en el modo que eligió (min). Sólo se registra para
      ese modo: del otro no sabe nada ese día.</li>
  <li>{
    tex("\\tau_i")
}: tiempo verdadero (min), igual todos los días: una persona sola no congestiona.</li>
  <li>{tex("\\Delta")}: sobretiempo de un shock (min). {
    tex("\\mathbf{1}[\\text{shock}]")
} vale 1 las
      primeras {
    tex("k")
} veces que la persona usa el modo mejor (E1) y 0 en otro caso; en E2 no hay shocks.</li>
  <li>{tex("\\varepsilon_{ni}(t)")}: ruido del día (min), normal con media 0 y desviación estándar
      {tex("\\sigma_i")} (min), independiente entre días y entre modos. En E1 {
    tex("\\sigma_i = 0")
}; en E2 el
      ruido va en los dos modos, sólo en el mejor o sólo en el peor. <strong>No se trunca</strong>: truncar
      en cero sube la media y se confunde con el efecto que se busca. Con σ grande una experiencia puede
      salir negativa; es percepción, no tiempo físico.</li>
</ul>

<p>La ventaja verdadera del mejor, en útiles, en minutos y como probabilidad:</p>
{
    ec(
        "\\Delta V = V_m^{\\mathrm{ref}} - V_p^{\\mathrm{ref}}, \\qquad A = \\frac{\\Delta V}{|\\beta|}, \\qquad P^{*} = \\Lambda(\\Delta V)",
        6,
    )
}
<ul class="donde">
  <li>{tex("\\Delta V")}: ventaja del modo mejor (útiles); positiva por definición.</li>
  <li>{
    tex("A")
}: la misma ventaja en minutos de viaje equivalentes (min). Es la unidad natural de los
      shocks: un shock de {tex("2A")} dura el doble de lo que el mejor le ahorra a la persona.</li>
  <li>{
    tex("P^{*}")
}: probabilidad (0–1) de elegir el mejor si la persona conociera los tiempos verdaderos.
      Es lo que da el simulador estático, y la referencia de todos los efectos.</li>
</ul>

<h3>2.1 Los tres casos: celdas reales del equilibrio</h3>
<p>
  Del equilibrio de la app (configuración por defecto, localización de equilibrio, sólo auto y metro,
  todos con auto) se eligieron tres celdas cuya {tex("P^{*}")} barre el rango. Con {
    tex("\\mu = 1")
} ninguna
  celda con metro factible pasa de una probabilidad de 0,85 a favor del auto ni de 0,65 a favor del
  metro (barrido de las celdas × 3 estratos hecho al elegir los casos; no está en el JSON); el caso más
  parejo (C1) es uno donde gana el metro, por costo: el auto es más rápido pero el estrato Bajo valora
  poco el tiempo. Hay uno por estrato.
</p>
{
    tabla(
        1,
        "Los tres casos: tiempos de equilibrio y ventaja verdadera del modo mejor",
        '<tr><th>Caso</th><th>Estrato</th><th class="n">Distancia al CBD (km)</th>'
        '<th class="n">Tiempo auto (min)</th><th class="n">Tiempo metro (min)</th><th>Modo mejor</th>'
        '<th class="n simb">ΔV (útiles)</th><th class="n simb">A (min)</th>'
        '<th class="n simb">P* (probabilidad, 0–1)</th></tr>',
        filas_casos,
        "Una fila por caso: una celda y un estrato reales del equilibrio de la app. Los tiempos son los"
        " de equilibrio puerta a puerta (el del metro suma acceso, espera y vehículo). ΔV es la"
        " diferencia de utilidad entre el modo mejor y el peor, ecuación (6); A es esa misma ventaja"
        " expresada en minutos; P* es la probabilidad de elegir el modo mejor cuando la persona conoce"
        " los tiempos verdaderos. Se leen de izquierda a derecha como un gradiente: de C1 (ventaja"
        " chica, casi indiferente) a C3 (ventaja grande). Celdas"
        f" {', '.join(str(c['celda']) for c in D['casos'])} de 201; la 100 es el CBD.",
    )
}
"""

# --- §3 -------------------------------------------------------------------------------

s3 = f"""
<!-- ==================================================================== -->
<h2 id="s3"><span class="num">3</span>Los indicadores</h2>

<p>
  Cada indicador tiene su ecuación, la descripción de sus componentes y la función que lo calcula
  (todas en <code>experimentos.py</code>, salvo (14), que se calcula al armar la tabla 4).
</p>

<h3>3.1 El valor crítico de corto plazo</h3>
<p>
  Si la persona vive {tex("k")} experiencias malas seguidas, al decidir el día siguiente esas
  experiencias tienen antigüedad {tex("1, \\dots, k")} días y la percepción inicial {tex("k+1")}. Su peso
  conjunto en (1) es
</p>
{ec("W_k(d) = \\frac{\\sum_{j=1}^{k} j^{-d}}{\\sum_{j=1}^{k} j^{-d} + (k+1)^{-d}}", 7)}
<ul class="donde">
  <li>{tex("W_k(d)")}: fracción (0–1) del tiempo percibido que explican las {tex("k")} experiencias malas,
      justo después de la última ({linea("experimentos.py", "peso_shocks")}).</li>
  <li>{tex("k")}: número de experiencias malas; {tex("j")}: antigüedad de cada una (días), de 1 (la última) a
      {tex("k")} (la primera).</li>
  <li>{tex("(k+1)^{-d}")}: peso sin normalizar de la percepción inicial, que tiene {tex("k+1")} días de antigüedad.</li>
  <li>Con {tex("d = 0")}, {tex("W_k = k/(k+1)")}, sin importar cuándo ocurrieron las experiencias.</li>
</ul>
<p>
  El tiempo percibido del mejor sube {tex("W_k\\Delta")} y su ventaja percibida cae a
  {tex("\\Delta V - |\\beta| W_k \\Delta")}. Se anula —la persona pasa a preferir el modo peor— en
</p>
{ec("\\Delta^{*}_k = \\frac{A}{W_k(d)}", 8)}
<ul class="donde">
  <li>{tex("\\Delta^{*}_k")}: <strong>valor crítico</strong> (min): sobretiempo que debe tener <em>cada una</em>
      de las {tex("k")} experiencias para dejar la ventaja percibida en cero, o sea {tex("P = \\tfrac12")}
      ({linea("experimentos.py", "delta_critico")}).</li>
  <li>{tex("A")}: ventaja verdadera en minutos, (6); {tex("W_k")}: peso de los shocks, (7). Como
      {tex("W_k \\lt 1")}, siempre {tex("\\Delta^{*}_k \\gt A")}: no basta un shock del tamaño de la ventaja.</li>
</ul>
<p>Y la probabilidad de elegir el mejor justo después del {tex("k")}-ésimo shock es</p>
{ec("P_{\\text{post}} = \\Lambda\\bigl(\\Delta V - |\\beta|\\, W_k\\, \\Delta\\bigr) = \\Lambda\\Bigl(\\Delta V \\bigl(1 - W_k\\, r\\bigr)\\Bigr), \\qquad r = \\frac{\\Delta}{A}", 9)}
<ul class="donde">
  <li>{tex("P_{\\text{post}}")}: probabilidad (0–1) de elegir el mejor al decidir justo después de la
      {tex("k")}-ésima experiencia mala ({linea("experimentos.py", "p_post_analitica")}; la simulación la
      registra en <code>p_post</code> de {linea("experimentos.py", "simular")}).</li>
  <li>{tex("\\Delta")}: sobretiempo de cada experiencia mala (min); {tex("r")}: el mismo en múltiplos de la
      ventaja (adim.).</li>
  <li>{tex("|\\beta| W_k \\Delta")}: utilidad que la persona le descuenta al mejor por los shocks (útiles).</li>
  <li>La segunda forma muestra que, con {tex("d = 0")}, el resultado depende sólo de {tex("\\Delta V")} y
      {tex("r")}: no de la escala en minutos.</li>
</ul>

<h3>3.2 Cuotas por horizonte y sus distribuciones</h3>
<p>Los tres horizontes son {", ".join(H_TXT.values())} días. Para la réplica {tex("n")} en el horizonte {tex("H")}:</p>
{ec("\\bar P_n^{H} = \\frac{1}{|H|} \\sum_{t \\in H} P_n(t)", 10)}
<ul class="donde">
  <li>{tex("\\bar P_n^{H}")}: probabilidad media (0–1) de que la réplica {tex("n")} elija el mejor en el
      horizonte {tex("H")} ({linea("experimentos.py", "cuota_por_persona")}).</li>
  <li>{tex("H")}: conjunto de días del horizonte; {tex("|H|")}: su número de días (10, 40 o 200).</li>
  <li>{tex("P_n(t)")}: de (4). Se promedia la <em>probabilidad</em> del modelo, no la elección sorteada: la
      distribución de {tex("\\bar P_n^H")} entre réplicas muestra lo que la historia le hizo a cada una,
      sin el ruido de Bernoulli de la elección del día.</li>
</ul>
{ec("S^{H} = \\frac{1}{R} \\sum_{n=1}^{R} \\bar P_n^{H}, \\qquad E^{H} = S^{H}_{\\text{trat}} - S^{H}_{\\text{ctrl}}", 11)}
<ul class="donde">
  <li>{tex("S^{H}")}: cuota esperada del modo mejor en el horizonte (0–1): el promedio de (10) sobre las
      réplicas ({linea("experimentos.py", "resumen_ventanas")}).</li>
  <li>{tex("R")} = {D["replicas"]}: número de réplicas, la misma persona con historias aleatorias distintas.</li>
  <li>{tex("E^{H}")}: efecto del tratamiento (en las tablas, en pp = 100 × la diferencia): cuota con shocks
      ({tex("\\text{trat}")}) menos cuota sin shocks ({tex("\\text{ctrl}")}). Los dos usan la misma semilla
      (<em>números aleatorios comunes</em>), así la diferencia no es ruido de muestreo.</li>
</ul>

<h3>3.3 Recuperación y persistencia</h3>
{ec("g(t) = \\bar s_{\\text{trat}}(t) - \\bar s_{\\text{ctrl}}(t), \\quad \\bar s(t) = \\frac{1}{R}\\sum_n P_n(t); \\qquad t_{1/2} = \\min\\{t > t_0 : g(t) \\ge g(t_0)/2\\} - t_0", 12)}
<ul class="donde">
  <li>{tex("\\bar s(t)")}: probabilidad media de elegir el mejor el día {tex("t")} (0–1), promedio sobre
      réplicas; es la curva de la figura 2.</li>
  <li>{tex("g(t)")}: brecha del día {tex("t")}, con shocks menos sin shocks (0–1; en pp en el texto).
      Es negativa mientras dura el efecto.</li>
  <li>{tex("t_0")}: día de la brecha máxima (día). {tex("t_{1/2}")}: <strong>vida media</strong> (días):
      los días desde {tex("t_0")} hasta recuperar la mitad de la brecha
      ({linea("experimentos.py", "vida_media")}).</li>
</ul>
<p>Para el largo plazo interesa además cuántas réplicas quedaron invertidas, y cuánto de la ventaja sobrevive:</p>
{ec("I^{H} = \\frac{1}{R}\\,\\#\\{n : \\bar P_n^{H} < \\tfrac12\\}, \\qquad \\Phi^{H} = \\frac{S^{H} - \\tfrac12}{P^{*} - \\tfrac12}", 13)}
<ul class="donde">
  <li>{tex("I^{H}")}: fracción de réplicas <em>invertidas</em> (0–1; en las tablas, % de réplicas): las que en
      ese horizonte eligen el peor más de la mitad de los días.</li>
  <li>{tex("\\#\\{\\cdot\\}")}: número de réplicas que cumplen la condición.</li>
  <li>{tex("\\Phi^{H}")}: fracción de la ventaja que sobrevive (adim.). {tex("\\Phi = 1")}: la variabilidad no
      cambió nada; {tex("\\Phi = 0")}: moneda al aire; {tex("\\Phi \\lt 0")}: prefiere el peor;
      {tex("\\Phi \\gt 1")}: más concentrada en el mejor que sin ruido. Se calcula en
      {linea("experimentos.py", "e2")}.</li>
</ul>
<p>
  <strong>Umbral de persistencia.</strong> Con {tex("d = 0")}, después de {tex("k")} shocks y
  {tex("n_b")} experiencias normales en el mejor, el sobretiempo que la persona percibe es
  {tex("k\\Delta/(k+1+n_b)")} (min): {tex("k+1+n_b")} experiencias pesan igual y sólo {tex("k")} traen el
  shock. La preferencia vuelve cuando eso baja de {tex("A")}, es decir, cuando {tex("n_b")} llega a
</p>
{ec("n^{*} = k\\,(r - 1) - 1", 14)}
<ul class="donde">
  <li>{tex("n^{*}")}: número de viajes normales (sin shock) en el modo mejor que hacen falta para volver a
      preferirlo (viajes). Si sale negativo, la preferencia nunca se invirtió. Exacta con {tex("d = 0")}.</li>
  <li>{tex("k")}: experiencias malas; {tex("r = \\Delta/A")}: su tamaño en múltiplos de la ventaja (adim.).</li>
  <li>Mientras prefiere el peor, la persona elige el mejor con probabilidad cercana a {tex("P_{\\text{post}}")}
      por día, así que juntar {tex("n^{*}")} viajes toma del orden de {tex("n^{*}/P_{\\text{post}}")} días. Ésa
      es la trampa del <em>hot stove</em> (Denrell y March, 2001): lo que corregiría la creencia es
      justamente lo que la persona dejó de hacer.</li>
</ul>

<h3>3.4 Separar variabilidad y hot stove</h3>
<p>En E2, la ventaja que percibe cada réplica cada día se recupera de su probabilidad, invirtiendo (4):</p>
{ec("\\widehat{\\Delta V}_n(t) = \\ln\\frac{P_n(t)}{1-P_n(t)}", 15)}
<ul class="donde">
  <li>{tex("\\widehat{\\Delta V}_n(t)")}: ventaja del mejor que percibe la réplica {tex("n")} el día
      {tex("t")} (útiles). Sin ruido es igual a {tex("\\Delta V")} de (6).</li>
  <li>{tex("\\hat m")} y {tex("\\hat s")}: su media y su desviación estándar (útiles) sobre réplicas y días
      del horizonte.</li>
</ul>
<p>Si sólo hubiera dispersión, centrada en la ventaja verdadera, la cuota del mejor sería</p>
{ec("P_{\\text{disp}} = \\mathbb{E}\\bigl[\\Lambda(\\Delta V + \\hat s Z)\\bigr], \\qquad Z \\sim \\mathcal{N}(0,1)", 16)}
<ul class="donde">
  <li>{tex("P_{\\text{disp}}")}: cuota esperada del mejor (0–1) con la dispersión observada {tex("\\hat s")}
      pero con la media en la ventaja verdadera {tex("\\Delta V")}.</li>
  <li>{tex("Z")}: variable normal estándar (adim.); {tex("\\mathbb{E}[\\cdot]")}: esperanza sobre {tex("Z")},
      calculada por cuadratura de Gauss–Hermite ({linea("experimentos.py", "gauss_logistica")}).</li>
</ul>
<p>La diferencia total se parte en dos ({linea("experimentos.py", "descomposicion")}):</p>
{ec("S - P^{*} = \\underbrace{(P_{\\text{disp}} - P^{*})}_{\\text{dispersión: variabilidad}} + \\underbrace{(S - P_{\\text{disp}})}_{\\text{sesgo: hot stove}}", 17)}
<ul class="donde">
  <li>{tex("S - P^{*}")}: cambio de la cuota del mejor por la variabilidad (0–1; en pp en tablas y figuras),
      con {tex("S")} de (11) y {tex("P^{*}")} de (6).</li>
  <li><strong>Dispersión</strong>, {tex("P_{\\text{disp}} - P^{*}")}: el <em>payoff variability effect</em>
      (Erev y Barron, 2005). Ruido simétrico en lo percibido acerca {tex("\\Lambda")} a ½. Un test verifica que
      {tex("\\mathbb{E}[\\Lambda(m+sZ)]")} decrece con {tex("s")} (<code>test_experimentos.py</code>).</li>
  <li><strong>Sesgo</strong>, {tex("S - P_{\\text{disp}}")}: el corrimiento de la media percibida. Una mala
      experiencia hace elegir menos ese modo y por eso se corrige menos que una buena. Es el hot stove.</li>
  <li>Control de la aproximación: {tex("\\mathbb{E}[\\Lambda(\\hat m + \\hat s Z)]")} reproduce {tex("S")} con
      error máximo de {pp(err_normal, 2).lstrip("+")} pp en todas las corridas. Ese error queda dentro del
      término de sesgo: sesgos de ese orden no se distinguen de cero.</li>
</ul>
"""

# --- §4 E1 ------------------------------------------------------------------------------

filas_crit = ""
for c in D["casos"]:
    for d in DS:
        dc = c["delta_critico"][str(d)]
        filas_crit += (
            f"<tr><td>{c['nombre']}</td><td class='n'>{num(c['ventaja_min'], 1)}</td><td class='n'>{num(d, 2)}</td>"
            + "".join(f"<td class='n'>{num(dc[str(k)], 0)}</td>" for k in E1_K)
            + "</tr>"
        )

filas_h = ""
for k in (1, 3, 10):
    for r in (1.0, 2.0, 4.0, 6.0):
        f = e1("C2", 0.5, k, r)
        tm = "—" if f["vida_media"] is None else num(f["vida_media"], 0)
        filas_h += (
            f"<tr><td class='n'>{k}</td><td class='n'>{num(r, 0)}</td><td class='n'>{num(f['delta_min'], 0)}</td>"
            f"<td class='n'>{num(f['p_post_sim'], 3)}</td>"
            + "".join(f"<td class='n'>{pp(f['efecto'][w])}</td>" for w in VENTANAS)
            + f"<td class='n'>{tm}</td><td class='n'>{num(100 * f['ventanas']['largo']['invertidos'], 0)} %</td></tr>"
        )

filas_pers = ""
for nombre in ("C1", "C2", "C3"):
    for k in (3, 10):
        for r in (2.0, 4.0, 6.0):
            f = e1(nombre, 0.0, k, r)
            n_ast = k * (r - 1) - 1
            espera = n_ast / max(f["p_post_analitica"], 1e-9)
            filas_pers += (
                f"<tr><td>{nombre}</td><td class='n'>{k}</td><td class='n'>{num(r, 0)}</td>"
                f"<td class='n'>{num(n_ast, 0)}</td><td class='n'>{num(f['p_post_analitica'], 3)}</td>"
                f"<td class='n'>{'&gt; 10⁴' if espera > 1e4 else num(espera, 0)}</td>"
                f"<td class='n'>{num(100 * f['ventanas']['largo']['invertidos'], 0)} %</td></tr>"
            )

s4 = f"""
<!-- ==================================================================== -->
<h2 id="s4"><span class="num">4</span>E1 · Experiencias malas al inicio</h2>

<p>
  <strong>Diseño.</strong> Sin ruido ({
    tex("\\sigma = 0")
}): sin shocks la persona no aprende nada y su
  probabilidad se queda en {tex("P^{*}")} todos los días (control). En el tratamiento, las primeras
  {tex("k")} veces que usa el modo mejor vive {tex("\\Delta = r \\cdot A")} minutos de más, con
  {tex("k \\in \\{1, 2, 3, 5, 10\\}")} y {tex("r")} de 0,5 a 6. Tres casos × tres {tex("d")} × 35
  combinaciones, {D["replicas"]} réplicas cada una.
</p>

<h3>4.1 El valor crítico se cumple</h3>
{
    fig(
        "e1-critico.png",
        1,
        "Probabilidad de elegir el modo mejor justo después de la k-ésima experiencia mala, caso C2."
        " Un panel por decaimiento d. Eje horizontal: tamaño de cada shock en múltiplos de la"
        f" ventaja, Δ/A (adim.; A = {num(C2['ventaja_min'], 0)} min). Eje vertical: probabilidad"
        " (0–1). Cada color es un número k de experiencias malas; la curva es la fórmula (9) y los"
        " puntos, la media de las 500 réplicas simuladas. Línea discontinua: probabilidad sin shocks,"
        f" P* = {num(C2['p_verdadera'], 3)}; línea de puntos: ½. Se lee buscando dónde cada curva"
        " cruza ½: ese Δ/A es el valor crítico (8). Que puntos y curvas coincidan valida la fórmula.",
    )
}
<p>
  Con {tex("d = 0")} la simulación coincide con (9) hasta el redondeo (diferencia máxima
  {
    num(err_d0, 4)
} en probabilidad): sin ruido el tiempo percibido sólo depende de cuántas experiencias
  hubo, no de cuándo. Con {tex("d > 0")} difiere un poco (máximo {
    num(err_d[0.5], 3)
} en probabilidad con
  {tex("d = 0{,}5")} y {num(err_d[1.28], 3)} con {
    tex("d = 1{,}28")
}): tras el primer shock la persona a veces elige el
  metro, los shocks dejan de ser consecutivos y la percepción inicial envejece menos de lo que (7)
  supone.
</p>
{
    tabla(
        2,
        "Valor crítico de corto plazo Δ*ₖ: sobretiempo por experiencia que invierte la preferencia",
        '<tr><th rowspan="2">Caso</th><th rowspan="2" class="n simb">A (min)</th>'
        '<th rowspan="2" class="n simb">d (adim.)</th>'
        f'<th colspan="{len(E1_K)}" class="n">Δ*ₖ (min), según el número k de experiencias malas</th></tr>'
        "<tr>" + "".join(f"<th class='n'>k = {k}</th>" for k in E1_K) + "</tr>",
        filas_crit,
        "Ecuación (8). Cada celda es cuántos minutos de más debe durar <em>cada una</em> de las k"
        " primeras experiencias en el modo mejor para que, al decidir el día siguiente, la persona"
        " prefiera el modo peor (P &lt; ½). Las filas cruzan los tres casos con los tres decaimientos"
        " d; las columnas, el número de experiencias malas. Se lee: por ejemplo, en C2 con d = 0 una"
        f" sola experiencia debe durar {num(C2['delta_critico']['0.0']['1'], 0)} min más que lo normal;"
        f" diez experiencias, {num(C2['delta_critico']['0.0']['10'], 0)} min cada una."
        " Dividido por A, cada fila con d = 0 da (k+1)/k, igual en los tres casos.",
    )
}
<p>
  Tres lecturas. (i) En múltiplos de {tex("A")} el resultado no depende del caso: con {tex("d = 0")}
  es {tex("(k+1)/k")}, o sea {tex("2A")} con una experiencia, {tex("1{,}33A")} con tres y
  {
    tex("1{,}1A")
} con diez. (ii) Más experiencias bajan el umbral pero con rendimientos decrecientes: el
  piso es {tex("A")}. (iii) Más recencia ({
    tex("d")
} mayor) lo baja, porque la experiencia mala pesa más
  frente a la percepción inicial: con {tex("d = 1{,}28")} una sola basta si mide {tex("1{,}4A")}.
</p>

<h3>4.2 Corto, mediano y largo plazo</h3>
{
    fig(
        "e1-trayectorias.png",
        2,
        "Trayectoria día a día después de las experiencias malas, caso C2, d = 0,5. Izquierda: una"
        " experiencia mala (k = 1); derecha: cinco (k = 5). Eje horizontal: día (1 a 250). Eje"
        " vertical: probabilidad media de elegir el modo mejor, s̄(t) (0–1), promedio de las 500"
        " réplicas. Línea gris discontinua: sin shocks (control, constante en P*). Líneas naranjas:"
        " shocks de 1, 2, 4 y 6 veces A, más oscuras cuanto mayores. Líneas verticales: fin del corto"
        " (día 10) y del mediano plazo (día 50). Se lee como una caída y una recuperación: la"
        " profundidad depende de Δ y k; la duración, de si la persona vuelve a probar el modo. Con"
        " k = 5 y Δ = 6A la recuperación no termina en 250 días.",
    )
}
{
    fig(
        "e1-horizontes.png",
        3,
        "Efecto de las experiencias malas por horizonte, caso C2, d = 0,5. Un panel por horizonte:"
        " corto (días 1–10), mediano (11–50) y largo (51–250). Eje horizontal: tamaño de cada shock,"
        " Δ/A (adim.). Eje vertical: efecto E sobre la cuota del modo mejor (pp), ecuación (11): cuota"
        " con shocks menos cuota sin shocks. Cada color es un número k de experiencias malas. Se lee"
        " comparando paneles: el mismo shock pesa mucho en el corto plazo y casi nada en el largo,"
        " salvo las combinaciones de k y Δ grandes, que se quedan.",
    )
}
{
    tabla(
        3,
        "Efecto de las experiencias malas por horizonte (caso C2, d = 0,5)",
        '<tr><th rowspan="2" class="n simb">k (experiencias)</th>'
        '<th rowspan="2" class="n simb">r = Δ/A (adim.)</th><th rowspan="2" class="n simb">Δ (min)</th>'
        '<th rowspan="2" class="n">P post (probabilidad, 0–1)</th>'
        '<th colspan="3" class="n">Efecto E sobre la cuota del mejor (pp)</th>'
        '<th rowspan="2" class="n">Vida media t½ (días)</th>'
        '<th rowspan="2" class="n">Invertidas en el largo plazo (% de réplicas)</th></tr>'
        '<tr><th class="n">corto, días 1–10</th><th class="n">mediano, 11–50</th>'
        '<th class="n">largo, 51–250</th></tr>',
        filas_h,
        "Cada fila es un tratamiento: k experiencias malas de Δ minutos de más cada una. P post es la"
        " probabilidad de elegir el modo mejor justo después de la k-ésima (ecuación 9; sin shocks"
        f" sería P* = {num(C2['p_verdadera'], 3)}). E es la diferencia entre la cuota media del mejor"
        " con y sin shocks en cada horizonte (ecuación 11), en puntos porcentuales: −10 pp significa"
        " que la persona eligió el mejor 10 de cada 100 días menos. t½ son los días que tarda en"
        " recuperar la mitad de la caída (ecuación 12); «—» = no la recupera en 250 días. La última"
        " columna es el porcentaje de réplicas que en los días 51–250 prefiere el modo peor"
        " (ecuación 13). Se lee bajando por columna: la caída se concentra en el corto plazo y sólo"
        " las filas de abajo (deuda k·r grande) llegan al largo.",
    )
}
<p>
  El patrón es el mismo en los tres casos y los tres {
    tex("d")
}: el efecto se concentra en el corto plazo,
  se diluye en el mediano y desaparece en el largo, <em>salvo</em> cuando la deuda {
    tex("k \\cdot r")
} es
  grande. Ahí el mediano y el largo plazo pesan más que el corto: la persona ya no vuelve al modo y el
  efecto se congela.
</p>

<h3>4.3 El umbral de persistencia</h3>
{
    tabla(
        4,
        "Umbral de persistencia: experiencias buenas necesarias y espera para juntarlas (d = 0)",
        '<tr><th>Caso</th><th class="n simb">k (experiencias malas)</th>'
        '<th class="n simb">r = Δ/A (adim.)</th><th class="n simb">n* (experiencias buenas)</th>'
        '<th class="n">P post (probabilidad, 0–1)</th><th class="n">Espera ≈ n*/P post (días)</th>'
        '<th class="n">Invertidas en el largo plazo (% de réplicas)</th></tr>',
        filas_pers,
        "Con d = 0, donde la ecuación (14) es exacta. n* es cuántas experiencias normales en el modo"
        " mejor necesita la persona para volver a preferirlo después de k shocks de tamaño r·A. Como"
        " lo elige con probabilidad cercana a P post, juntarlas toma del orden de n*/P post días. La"
        " última columna es lo que efectivamente pasó en la simulación. Se lee comparando las dos"
        " últimas columnas: cuando la espera supera con holgura los 200 días del largo plazo, la"
        " mayoría de las réplicas queda invertida. La espera es una cota gruesa: mientras la persona"
        " se recupera P sube, así que la sobreestima.",
    )
}
<p>
  La regla funciona como orden de magnitud: cuando {
    tex("n^{*}/P_{\\text{post}}")
} queda muy por encima de
  los 200 días del largo plazo, la mayoría de las réplicas termina invertida; cuando queda por debajo,
  casi ninguna. No es un corte limpio, porque la espera real es aleatoria.
</p>

<h3>4.4 Distribuciones</h3>
{
    fig(
        "e1-distribuciones.png",
        4,
        "Distribución entre réplicas de la probabilidad media de elegir el modo mejor, caso C2,"
        " d = 0,5, tres experiencias malas (k = 3). Un panel por horizonte. Eje horizontal: P̄ₙ, la"
        " probabilidad media de cada réplica en ese horizonte (0–1), ecuación (10), en tramos de"
        " 0,05. Eje vertical: fracción de las 500 réplicas en cada tramo (0–1). Gris: sin shocks;"
        " naranjo: Δ = 2A; negro: Δ = 6A. Línea de puntos: ½. Se lee como un histograma: sin shock"
        " todas las réplicas están en P*; con Δ = 2A todas bajan juntas y vuelven; con Δ = 6A, en el"
        " largo plazo la distribución se abre: unas réplicas volvieron a P* y otras siguen en el"
        " modo peor.",
    )
}
<p>
  La media esconde que los shocks grandes <strong>polarizan</strong>: en el largo plazo no hay una
  persona «a medias», hay réplicas que se recuperaron y réplicas que no. Lo que decide de qué lado cae
  cada una es si volvió a probar el modo a tiempo, que es puro azar del logit.
</p>
"""

# --- §5 E2 ------------------------------------------------------------------------------

filas_phi = ""
for nombre in ("C1", "C2", "C3"):
    for cond in ("ambos", "solo_mejor", "solo_peor"):
        for d in (0.5, 1.28):
            f = e2(nombre, d, cond, 80.0)
            q = f["descomposicion"]["largo"]
            filas_phi += (
                f"<tr><td>{nombre}</td><td>{cond.replace('_', ' ')}</td><td class='n'>{num(d, 2)}</td>"
                + "".join(f"<td class='n'>{num(f['phi'][w], 2)}</td>" for w in VENTANAS)
                + f"<td class='n'>{pp(q['pve'])}</td><td class='n'>{pp(q['sesgo'])}</td></tr>"
            )

s5 = f"""
<!-- ==================================================================== -->
<h2 id="s5"><span class="num">5</span>E2 · Variabilidad del tiempo</h2>

<p>
  <strong>Diseño.</strong> Sin shocks. Ruido {
    tex("\\varepsilon \\sim \\mathcal{N}(0, \\sigma^2)")
} con
  σ ∈ {{0, 10, 20, 40, 80}} min, en tres condiciones: <em>ambos</em> modos (la prueba limpia del efecto de
  variabilidad: las medias no cambian), <em>sólo el mejor</em> y <em>sólo el peor</em>. Las dos últimas
  separan el hot stove, que actúa contra el modo con ruido. En útiles, σ = 80 min es
  {num(80 * BETA, 2)} útiles: comparable al ruido del logit ({num(3.14159265 / 3**0.5, 2)} útiles).
</p>

<h3>5.1 ¿Más varianza, más 50-50?</h3>
{
    fig(
        "e2-phi.png",
        5,
        "Cuánto de la ventaja del modo mejor sobrevive a la variabilidad, largo plazo (días 51–250),"
        " d = 0,5. Un panel por condición: ruido en ambos modos, sólo en el mejor, sólo en el peor."
        " Eje horizontal: desviación estándar del tiempo vivido en útiles, σ·|β| (útiles; 1 útil ≈"
        f" {num(1 / BETA, 0)} min), para poner los tres casos en la misma escala. Eje vertical: Φ"
        " (adim.), ecuación (13). Un color por caso. Línea discontinua en 1: la variabilidad no"
        " cambió nada; línea de puntos en 0: moneda al aire. Se lee mirando cuánto baja cada curva:"
        " si se acerca a 0, la elección se volvió aleatoria.",
    )
}
{
    fig(
        "e2-decaimiento.png",
        6,
        "El efecto de variabilidad según horizonte y memoria, caso C2, ruido en ambos modos. Un panel"
        " por horizonte. Eje horizontal: desviación estándar del tiempo vivido, σ (min). Eje"
        " vertical: Φ (adim.), ecuación (13). Tipo de línea: decaimiento d = 0 (puntos), 0,5"
        " (continua) y 1,28 (discontinua). Se lee comparando paneles y líneas: el efecto es mayor en"
        " el corto plazo y, con más recencia (d = 1,28), no se apaga en el largo.",
    )
}
{
    tabla(
        5,
        "Variabilidad de 80 minutos: cuánto de la ventaja sobrevive y por qué",
        '<tr><th rowspan="2">Caso</th><th rowspan="2">Ruido en</th>'
        '<th rowspan="2" class="n simb">d (adim.)</th>'
        '<th colspan="3" class="n">Φ, fracción de la ventaja que sobrevive (adim.)</th>'
        '<th colspan="2" class="n">Largo plazo: S − P* (pp)</th></tr>'
        '<tr><th class="n">corto, días 1–10</th><th class="n">mediano, 11–50</th>'
        '<th class="n">largo, 51–250</th><th class="n">por dispersión</th>'
        '<th class="n">por sesgo</th></tr>',
        filas_phi,
        "Todas las filas con σ = 80 min de desviación estándar en el tiempo vivido"
        f" ({num(80 * BETA, 2)} útiles, comparable al ruido del logit, {num(3.14159265 / 3**0.5, 2)}"
        " útiles). Φ (ecuación 13) vale 1 si la variabilidad no cambió la"
        " cuota del modo mejor, 0 si la dejó en 50-50 y más de 1 si la concentró aún más en el"
        " mejor. Las dos últimas columnas parten la diferencia entre la cuota de largo plazo y P*"
        " (ecuación 17): «dispersión» es el efecto de variabilidad propiamente tal (siempre hacia"
        " ½, signo negativo cuando el mejor es más probable) y «sesgo» el corrimiento por hot stove."
        " Se lee por bloques de condición: con ruido sólo en el mejor Φ cae; con ruido en el peor"
        " sube; con ruido en ambos los dos términos se compensan.",
    )
}
<p>
  Tres resultados. <strong>(i) El horizonte manda.</strong> Con {
    tex("d \\le 0{,}5")
} el efecto es de corto
  plazo: la percepción promedia cada vez más experiencias y su ruido baja como
  {tex("\\sigma/\\sqrt{n}")}. Con {tex("d = 1{,}28")} la serie {tex("\\sum_j j^{-d}")} converge: las
  últimas experiencias conservan un peso fijo por muchas que se acumulen, el ruido no se promedia y el
  efecto llega al largo plazo. <strong>(ii) Alternativas parejas.</strong> El caso más cercano a 50-50 es C1 (la ventaja más
  chica) con el ruido en el mejor. <strong>(iii) El ruido en el peor protege.</strong> Con ruido
  en el modo peor, Φ pasa de 1 en el mediano y largo plazo: el hot stove juega a favor, porque la persona huye del peor tras una mala
  experiencia y no vuelve a corregirla.
</p>

<h3>5.2 Dispersión contra sesgo</h3>
{
    fig(
        "e2-descomposicion.png",
        7,
        "De dónde sale el cambio en la cuota de largo plazo, caso C2, d = 0,5. Un panel por"
        " condición de ruido. Eje horizontal: desviación estándar del tiempo vivido, σ (min). Eje"
        " vertical: contribución a S − P*, la diferencia entre la cuota del modo mejor y la"
        " probabilidad sin ruido (pp), ecuación (17). Barra azul: dispersión de lo percibido, el"
        " efecto de variabilidad (siempre negativo: hacia ½). Barra naranja: sesgo de la media"
        " percibida, el hot stove (su signo depende de dónde está el ruido). Raya negra: el total."
        " Se lee comparando el largo de las dos barras: cuando son parecidas y de signo opuesto, se"
        " compensan y la cuota casi no se mueve.",
    )
}
<p>
  La dispersión empuja <strong>siempre</strong> hacia ½: es el efecto que pregunta la hipótesis, y está
  en las {
    len(D["e2"])
} corridas. El sesgo cambia de signo según dónde esté el ruido: negativo con ruido
  sólo en el mejor, positivo cuando el peor también lo tiene. Con ruido en ambos modos y
  {tex("d \\le 0{,}5")} los dos se compensan y la cuota de largo plazo casi no se mueve
  ({tex("\\Phi")} entre {num(min(PHI_BAJO), 2)} y {num(max(PHI_BAJO), 2)}, adimensional, con
  σ = 80 min); con {tex("d = 1{,}28")} gana la dispersión ({tex("\\Phi")} entre
  {num(min(PHI_ALTO), 2)} y {num(max(PHI_ALTO), 2)}). Por eso «más varianza → más 50-50» se
  observa en el agregado sólo si el ruido está en el modo mejor o la memoria es muy reciente.
</p>

<h3>5.3 Distribuciones</h3>
{
    fig(
        "e2-distribuciones.png",
        8,
        "Heterogeneidad que crea la variabilidad entre réplicas de la misma persona, caso C2,"
        " d = 0,5, ruido en ambos modos, largo plazo (días 51–250). Eje horizontal: P̄ₙ, la"
        " probabilidad media de elegir el modo mejor de cada réplica (0–1), ecuación (10), en tramos"
        " de 0,05. Eje vertical: fracción de las 500 réplicas en cada tramo (0–1). Una línea por"
        " σ: 0 (gris), 20, 40 y 80 min (azul, más intenso cuanto mayor). Línea de puntos: ½. Se lee"
        " por el ancho: sin ruido todas las réplicas están en P*; con más σ la distribución se"
        " ensancha, aunque su centro casi no se mueve.",
    )
}
<p>
  Aunque la media apenas cambia, la variabilidad sí crea <strong>heterogeneidad</strong>: con σ = 80 min
  las réplicas de una misma persona terminan con una probabilidad de elegir el mejor de entre
  {num(e2("C2", 0.5, "ambos", 80.0)["ventanas"]["largo"]["cuantiles"][0], 2)} y
  {num(e2("C2", 0.5, "ambos", 80.0)["ventanas"]["largo"]["cuantiles"][4], 2)} (percentiles 5 y 95).
  Para la ciudad completa eso importa más que la media: es dispersión de conducta que el logit
  estático no produce.
</p>
"""

# --- §6 E3 ------------------------------------------------------------------------------

SIGMAS_P = sorted({f["sigma"] for f in P["filas"]})
ruidosas = [f for f in P["filas"] if f["sigma"] > 0]
max_split = max(abs(f["split_ultimos"][0] - pob(0.0, f["d"])["split_ultimos"][0]) for f in ruidosas)
max_exp = max(abs(delta_exp_min(f)) for f in ruidosas)
ctrl = [pob(0.0, d) for d in DS]
ctrl_phi = [f["phi"]["todos"][w] for f in ctrl for w in VENTANAS]
ctrl_disp = [f["dispersion_iguales"] for f in ctrl]
f80 = pob(80.0, 0.5)
f80r = pob(80.0, 1.28)
phi_c2_80 = e2("C2", 0.5, "ambos", 80.0)["phi"]
assert all(abs(x - 1) < 0.01 for x in ctrl_phi) and all(abs(x - 1) < 0.05 for x in ctrl_disp)

filas_phi_pob = ""
for sigma in (20.0, 40.0, 80.0):
    for d in DS:
        f, g = pob(sigma, d)["phi"]["todos"], e2("C2", d, "ambos", sigma)["phi"]
        filas_phi_pob += (
            f"<tr><td class='n'>{num(sigma, 0)}</td><td class='n'>{num(d, 2)}</td>"
            + "".join(f"<td class='n'>{num(f[w], 2)}</td>" for w in VENTANAS)
            + "".join(f"<td class='n'>{num(g[w], 2)}</td>" for w in VENTANAS)
            + "</tr>"
        )

filas_iguales = ""
for sigma in (0.0, 20.0, 40.0, 80.0):
    for d in DS:
        f, f0 = pob(sigma, d), pob(0.0, d)
        cm = f["cuota_mejor_auto_metro"]["todos"] - f0["cuota_mejor_auto_metro"]["todos"]
        filas_iguales += (
            f"<tr><td class='n'>{num(sigma, 0)}</td><td class='n'>{num(d, 2)}</td>"
            f"<td class='n'>{pp(f['split_ultimos'][0] - f0['split_ultimos'][0])}</td>"
            f"<td class='n'>{pp(cm)}</td><td class='n'>{num(f['dispersion_iguales'], 2)}</td>"
            f"<td class='n'>{num(round(delta_exp_min(f), 2) + 0.0, 2)}</td><td class='n'>{num(brecha_min(f), 2)}</td></tr>"
        )

s6 = f"""
<!-- ==================================================================== -->
<h2 id="s6"><span class="num">6</span>E3 · La ciudad completa</h2>

<p>
  <strong>Diseño.</strong> La pregunta de E2, ahora con las {
    f"{P['N']:,}".replace(",", ".")
} personas de la ciudad a la vez
  (<code>poblacion.py</code>). Es la ciudad de la app con dos cambios: todos tienen auto y sólo se
  elige entre auto y metro, como en E1 y E2. El día 0 es el equilibrio del simulador: sus tiempos
  son la percepción inicial de todos. Cada día todos eligen con lo que perciben, los flujos cargan la
  red y cada persona vive el tiempo de su modo en su celda más un ruido propio
  {tex("\\varepsilon \\sim \\mathcal{N}(0, \\sigma^2)")}, en los dos modos (en el metro, sobre el
  tiempo en vehículo; acceso y espera quedan en los del equilibrio). Quien vive a menos de 1 km del CBD
  no tiene metro: carga la red pero no elige. σ ∈ {{{", ".join(num(x, 0) for x in SIGMAS_P)}}} min,
  {tex("d")} ∈ {{0; 0,5; 1,28}}, {P["dias"]} días y los horizontes de E1 y E2. Una corrida por
  combinación con la misma semilla: cada σ se compara con σ = 0 usando los mismos números aleatorios.
</p>
<p>
  <strong>Control.</strong> Con σ = 0 la ciudad se queda en el equilibrio del simulador: Φ entre
  {num(min(ctrl_phi), 3)} y {num(max(ctrl_phi), 3)} en los tres horizontes y la razón de dispersión
  (18) de {num(sum(ctrl_disp) / len(ctrl_disp), 2)}. Todo lo que sigue es efecto del ruido.
</p>

<h3>6.1 ¿Más varianza, más 50-50? En la ciudad, también sólo en el corto plazo</h3>
<p>
  Φ es la ecuación (13) con {tex("S")} y {tex("P^{*}")} promediados sobre las personas que pueden
  elegir: el modo mejor y {
    tex("P^{*}_n")
} de cada una son los del equilibrio. El resultado repite el
  de E2: con σ = 80 min y {tex("d = 0{,}5")}, Φ vale {
    num(f80["phi"]["todos"]["corto"], 2)
} en el corto
  plazo, {num(f80["phi"]["todos"]["medio"], 2)} en el mediano y {
    num(f80["phi"]["todos"]["largo"], 2)
} en
  el largo (C2 en E2: {num(phi_c2_80["corto"], 2)}, {num(phi_c2_80["medio"], 2)} y
  {num(phi_c2_80["largo"], 2)}). Sólo con mucha recencia ({
    tex("d = 1{,}28")
}) el efecto llega al largo
  plazo: Φ = {num(f80r["phi"]["todos"]["largo"], 2)}.
</p>
{
    fig(
        "e3-phi.png",
        9,
        "Cuánto de la ventaja del modo mejor sobrevive a la variabilidad en la ciudad, por horizonte."
        " Un panel por horizonte. Eje horizontal: desviación estándar del tiempo vivido, σ (min). Eje"
        " vertical: Φ de la población (adim.), ecuación (13) promediada sobre las personas. Tipo de"
        " línea: decaimiento d = 0 (puntos), 0,5 (continua) y 1,28 (discontinua). Es el par de la"
        " figura 6 (una persona, C2): se lee igual, comparando paneles y líneas.",
    )
}
{
    tabla(
        6,
        "La ciudad contra una persona: fracción de la ventaja que sobrevive",
        '<tr><th rowspan="2" class="n">σ (min)</th><th rowspan="2" class="n simb">d (adim.)</th>'
        '<th colspan="3" class="n">Φ ciudad (adim.)</th><th colspan="3" class="n">Φ caso C2, E2 (adim.)</th></tr>'
        "<tr>" + "".join(f'<th class="n">{H_TXT[w]}</th>' for w in VENTANAS) * 2 + "</tr>",
        filas_phi_pob,
        "Una fila por σ y decaimiento d, con ruido en los dos modos. Φ es la fracción de la ventaja"
        " del modo mejor que sobrevive: 1, nada cambió; 0, moneda al aire. A la izquierda la ciudad"
        " completa, con congestión; a la derecha una persona sola (caso C2, tabla 1). Se lee por"
        " columnas: el corto plazo pierde ventaja en los dos; el largo, sólo con d = 1,28.",
    )
}

<h3>6.2 Lo que la media no muestra</h3>
<p>
  La partición modal casi no se mueve: con cualquier σ y {
    tex("d")
}, la cuota del auto en los últimos
  {P["ultimos"]} días cambia a lo sumo {pp(max_split).lstrip("+")} pp, y el bienestar experimentado
  {num(max_exp, 2)} min por viaje. Mirar sólo la partición haría concluir que la variabilidad no
  importa. Dos cosas sí cambian.
</p>
<p>
  <strong>Personas iguales terminan distintas.</strong> En cada grupo {
    tex("g")
} de personas del mismo
  estrato y celda, con los dos modos, se compara la varianza del share de días en auto de cada persona,
  {tex("s_n")}, con la que daría la misma probabilidad sin historia, la binomial de {tex("T")} =
  {P["ultimos"]} días:
</p>
{
    ec(
        "R = \\frac{\\sum_g n_g\\,\\widehat{\\mathrm{Var}}_g(s_n)}"
        "{\\sum_g n_g\\,\\bar s_g (1 - \\bar s_g)/T}",
        18,
    )
}
<p>
  {tex("R = 1")}: la historia no diferenció a nadie. Con σ = 80 min, {tex("R")} =
  {num(f80["dispersion_iguales"], 2)} con {tex("d = 0{,}5")} y {
    num(f80r["dispersion_iguales"], 2)
} con
  {tex("d = 1{,}28")}: es la heterogeneidad de §5.3, ahora en la población.
</p>
<p>
  <strong>La utilidad con que se decide sobrestima la que se vive.</strong> Cada persona elige el
  modo que hoy percibe mejor, y lo percibe mejor en parte por suerte: un sesgo de selección. Medido en
  minutos, es cuánto más lento es el modo elegido de lo que se creía, promediado sobre personas y los
  últimos {P["ultimos"]} días, con {tex("\\tau_{nj}(t)")} el tiempo de la red ese día y
  {tex("b_{nj}(t)")} el percibido (2):
</p>
{ec("B = \\overline{\\tau_{n j_n(t)}(t) - b_{n j_n(t)}(t)}", 19)}
<p>
  Con σ = 80 min, {tex("B")} = {num(brecha_min(pob(80.0, 0.0)), 2)} min con {tex("d = 0")},
  {num(brecha_min(f80), 2)} con {tex("d = 0{,}5")} y {num(brecha_min(f80r), 2)} con
  {tex("d = 1{,}28")}. Crece con la recencia porque la percepción queda dominada por las últimas
  experiencias, que son ruidosas. Por eso el bienestar no puede medirse con el logsum de las
  utilidades percibidas: lo sobrestimaría en esa magnitud.
</p>
{
    fig(
        "e3-iguales.png",
        10,
        "Lo que la variabilidad deja en la ciudad aunque la partición no cambie. Eje horizontal en los"
        " dos paneles: desviación estándar del tiempo vivido, σ (min). Izquierda: razón de dispersión"
        " entre personas iguales R (adim.), ecuación (18); la línea discontinua en 1 es la binomial."
        " Derecha: brecha B entre el tiempo de red y el percibido del modo elegido (min por viaje),"
        " ecuación (19). Tipo de línea: decaimiento d = 0 (puntos), 0,5 (continua) y 1,28"
        " (discontinua). Se lee siguiendo cada línea hacia la derecha: cuánto crece con σ y cuánto"
        " más con recencia.",
    )
}
{
    tabla(
        7,
        "La ciudad con variabilidad: partición, dispersión y bienestar",
        '<tr><th class="n">σ (min)</th><th class="n simb">d (adim.)</th>'
        '<th class="n">Δ cuota auto (pp)</th><th class="n">Δ cuota del modo mejor (pp)</th>'
        '<th class="n simb">R (adim.)</th><th class="n">Δ bienestar experimentado (min/viaje)</th>'
        '<th class="n simb">B (min/viaje)</th></tr>',
        filas_iguales,
        f"Una fila por σ y decaimiento d; todo en los últimos {P['ultimos']} días de {P['dias']}."
        " Las Δ son contra σ = 0 con el mismo d. Cuota del modo mejor: entre quienes pueden elegir, la"
        " fracción de viajes en el modo de mayor utilidad verdadera. R, ecuación (18): 1 es la"
        " binomial. Bienestar experimentado: utilidad verdadera del modo elegido, en minutos"
        f" (÷|β| = {num(BETA, 4)}). B, ecuación (19). Se lee por columnas: las Δ quedan cerca de 0"
        " mientras R y B crecen.",
    )
}
"""

# --- §7 E4 ------------------------------------------------------------------------------

MODOS4 = C4["modos"]
SIGMAS_C4 = sorted({f["sigma"] for f in C4["filas"]})
ctrl4 = [c4(None, 0.0, d) for d in DS]
ctrl4_phi = [f["phi"]["todos"][w] for f in ctrl4 for w in VENTANAS] + [
    v[w] for f in ctrl4 for v in f["phi"]["por_mejor"].values() for w in VENTANAS
]
ctrl4_split = max(
    abs(a - b)
    for f in ctrl4
    for a, b in zip(f["split_ultimos"], C4["split_equilibrio"], strict=True)
)
ctrl4_disp = [f["dispersion_iguales"] for f in ctrl4]
assert ctrl4_split < 0.001 and all(abs(x - 1) < 0.01 for x in ctrl4_phi)
assert all(abs(x - 1) < 0.05 for x in ctrl4_disp)


def dsplit(cond, d, k, sigma=80.0):
    return c4(cond, sigma, d)["split_ultimos"][k] - c4(cond, 0.0, d)["split_ultimos"][k]


# El texto afirma: con σ = 80 el modo con ruido pierde cuota y la bici gana, con todo d.
RUIDO_EN = {c: [k for k, r in enumerate(C4["condiciones"][c]) if r] for c in COND_TXT}
assert all(dsplit(c, d, k) < 0 for c in COND_TXT for d in DS for k in RUIDO_EN[c])
assert all(dsplit(c, d, 2) > 0 for c in COND_TXT for d in DS)
bici_max = max(dsplit(c, d, 2) for c in COND_TXT for d in DS)
# «Con d ≤ 0,5 los cambios son de décimas de punto.»
assert max(abs(dsplit(c, d, k)) for c in COND_TXT for d in (0.0, 0.5) for k in range(4)) < 0.01
split4_max = max(abs(dsplit(c, d, k)) for c in COND_TXT for d in DS for k in range(4))
ab0 = sum(f["abandono_metro"] for f in ctrl4) / len(ctrl4)
ab_max = max(c4(c, 80.0, d)["abandono_metro"] for c in COND_TXT for d in DS)


def phi_m(cond, d, m, w="medio"):
    return c4(cond, 80.0, d)["phi"]["por_mejor"][m][w]


def caida(cond, d, m, w="medio"):
    """Cuota del modo mejor menos P*, entre quienes lo tienen como mejor: la pérdida en puntos."""
    g = c4(cond, 80.0, d)["phi"]["por_mejor"][m]
    return g["s"][w] - g["p_estrella"]


def margen(m):
    """P* − 1/J del grupo: el denominador de (20). Es del equilibrio, igual en toda condición."""
    g = c4("auto", 80.0, 0.5)["phi"]["por_mejor"][m]
    return g["p_estrella"] - g["uniforme"]


# Quien vive el ruido en su modo mejor pierde ventaja; quien lo vive sólo en alternativas, no.
# En Φ el metro parece perder mucho más que el auto, pero en puntos pierden lo mismo: lo que
# cambia es el denominador de (20), tres veces más chico para el metro.
assert all(phi_m("tp", d, "Metro") < phi_m("auto", d, "Auto") < 1 for d in (0.5, 1.28))
assert all(abs(caida("tp", d, "Metro") - caida("auto", d, "Auto")) < 0.005 for d in DS)
assert margen("Metro") < margen("Auto") / 2
uni_metro = c4("auto", 80.0, 0.5)["phi"]["por_mejor"]["Metro"]["uniforme"]
sin_ruido_mejor = [
    phi_m(c, d, m)
    for c in COND_TXT
    for d in DS
    for k, m in enumerate(MODOS4)
    if k not in RUIDO_EN[c]
]
assert min(sin_ruido_mejor) > 0.95
agg = {c: c4(c, 80.0, 0.5)["phi"]["todos"] for c in COND_TXT}
f4r = c4("auto_tp", 80.0, 1.28)
exp4_max = max(
    abs(delta_exp_c4(c4(c, s_, d))) for c in COND_TXT for s_ in SIGMAS_C4[1:] for d in DS
)
n_mejor = {m: v["n"] for m, v in c4("auto", 80.0, 0.5)["phi"]["por_mejor"].items()}

filas_mejor = ""
for c, ruido_en in COND_TXT.items():
    for m in MODOS4:
        filas_mejor += (
            f"<tr><td>{ruido_en}</td><td>{m}</td>"
            f"<td class='n'>{f'{n_mejor[m]:,}'.replace(',', '.')}</td>"
            f"<td class='n'>{num(100 * margen(m), 1)}</td>"
            + "".join(
                f"<td class='n'>{num(round(phi_m(c, d, m), 2) + 0.0, 2)}</td>"
                f"<td class='n'>{pp(caida(c, d, m))}</td>"
                for d in (0.5, 1.28)
            )
            + "</tr>"
        )

filas_c4 = ""
for c, ruido_en in COND_TXT.items():
    for d in DS:
        f = c4(c, 80.0, d)
        filas_c4 += (
            f"<tr><td>{ruido_en}</td><td class='n'>{num(d, 2)}</td>"
            + "".join(f"<td class='n'>{pp(dsplit(c, d, k))}</td>" for k in range(4))
            + f"<td class='n'>{num(f['dispersion_iguales'], 2)}</td>"
            f"<td class='n'>{num(round(delta_exp_c4(f), 2) + 0.0, 2)}</td>"
            f"<td class='n'>{num(round(brecha_min(f), 2) + 0.0, 2)}</td>"
            f"<td class='n'>{num(100 * f['abandono_metro'], 1)}</td></tr>"
        )

s7 = f"""
<!-- ==================================================================== -->
<h2 id="s7"><span class="num">7</span>E4 · La ciudad con cuatro modos</h2>

<p>
  <strong>Diseño.</strong> La ciudad de la app tal cual, con sus {
    f"{C4['N']:,}".replace(",", ".")
} personas
  (<code>poblacion.py ciudad</code>): cada hogar tiene o no auto según su estrato y se elige entre
  los cuatro modos. Quien no tiene auto no lo elige; quien vive a menos de 1 km del CBD no tiene metro.
  El día 0 es otra vez el equilibrio del simulador. El IBL aprende el tiempo del auto, del metro (en
  vehículo) y de la bici, que se congestiona; la caminata no se aprende, porque su tiempo es
  geométrico y no cambia. El ruido {tex("\\varepsilon \\sim \\mathcal{N}(0, \\sigma^2)")} entra en
  tres condiciones: sólo en el auto, sólo en el metro y en los dos; nunca en la bici ni en la
  caminata. σ ∈ {{{", ".join(num(x, 0) for x in SIGMAS_C4)}}} min, {tex("d")} ∈ {{0; 0,5; 1,28}},
  {C4["dias"]} días y un control sin ruido por {tex("d")}, todos con la misma semilla.
</p>
<p>
  <strong>Control.</strong> Con σ = 0 la partición de los últimos {C4["ultimos"]} días es la del
  equilibrio ({
    ", ".join(
        f"{m.lower()} {num(100 * x, 2)}"
        for m, x in zip(MODOS4, C4["split_equilibrio"], strict=True)
    )
} %)
  con a lo sumo {num(100 * ctrl4_split, 2)} pp de diferencia; Φ queda entre {num(min(ctrl4_phi), 3)}
  y {num(max(ctrl4_phi), 3)}, también separado por modo mejor, y {tex("R")} en
  {num(sum(ctrl4_disp) / len(ctrl4_disp), 2)}.
</p>

<h3>7.1 El ruido saca viajes del modo que lo tiene, y la bici los recibe</h3>
<p>
  Con σ = 80 min el modo con ruido pierde cuota en todas las condiciones y con todo {tex("d")}, y la
  bici gana en todas: hasta {pp(bici_max)} pp, con ruido en los dos modos y {tex("d = 1{,}28")}.
  Es lo que E3 no podía mostrar: con bici y caminata sin ruido, la elección migra hacia ellas. Es
  coherente con el hot stove de E2, aunque aquí no se aisló: una experiencia mala hace evitar el modo ruidoso, y quien lo evita no
  junta las experiencias buenas que lo compensarían. Con {tex("d \\le 0{,}5")} los cambios son de
  décimas de punto; ningún modo se mueve más de {pp(split4_max).lstrip("+−")} pp. La partición
  agregada, otra vez, casi no cambia.
</p>
{
    fig(
        "e4-particion.png",
        11,
        "A qué modo se van los viajes cuando el tiempo de uno es variable. Un panel por condición de"
        " ruido. Eje horizontal: desviación estándar del tiempo vivido, σ (min). Eje vertical: cambio"
        f" de la cuota de cada modo en los últimos {C4['ultimos']} días contra el control sin ruido"
        " (pp). Color: el modo. Tipo de línea: decaimiento d = 0,5 (continua) y 1,28 (discontinua). Se"
        " lee por panel: baja el modo con ruido, sube la bici.",
    )
}

<h3>7.2 El promedio esconde signos opuestos</h3>
<p>
  Con más de dos modos, el punto de comparación de (13) ya no es ½ sino el reparto uniforme entre los
  {tex("J_n")} modos que tiene cada persona. Con las medias sobre todas las personas:
</p>
{
    ec(
        "\\Phi = \\frac{\\bar S - \\overline{1/J_n}}{\\bar P^{*} - \\overline{1/J_n}}",
        20,
    )
}
<p>
  Con {tex("J_n = 2")} es (13). Con σ = 80 min y {tex("d = 0{,}5")}, Φ de la ciudad vale
  {num(agg["auto"]["corto"], 2)}, {num(agg["auto"]["medio"], 2)} y {num(agg["auto"]["largo"], 2)}
  en los tres horizontes con ruido en el auto, pero {num(agg["tp"]["corto"], 2)},
  {num(agg["tp"]["medio"], 2)} y {num(agg["tp"]["largo"], 2)} con ruido en el metro: en el mediano y
  largo plazo, más ventaja que sin ruido. Separado por el modo mejor de cada persona (figura 12, tabla 9) se ve por qué.
  Quien vive el ruido en su modo mejor pierde ventaja; quien lo vive sólo en sus alternativas la
  conserva o la gana: en el mediano plazo, Φ ≥ {
    num(min(sin_ruido_mejor), 2)
} para todos ellos, y hasta
  {num(phi_m("tp", 1.28, "Bici"), 2)} para quienes tienen la bici como modo mejor con ruido en el
  metro. Son las condiciones «sólo el mejor» y «sólo el peor» de E2, ahora mezcladas dentro de la
  ciudad, y se compensan en el promedio.
</p>
<p>
  En Φ, el metro parece el modo mejor más sensible. Con ruido sólo en su modo y en el mediano plazo,
  quienes lo tienen como mejor conservan Φ = {num(phi_m("tp", 0.5, "Metro"), 2)} de la ventaja con
  {tex("d = 0{,}5")} y {num(phi_m("tp", 1.28, "Metro"), 2)} con {tex("d = 1{,}28")}; quienes tienen
  el auto, con ruido sólo en el auto, {num(phi_m("auto", 0.5, "Auto"), 2)} y
  {num(phi_m("auto", 1.28, "Auto"), 2)}. Pero en puntos la cuota del modo mejor cae lo mismo:
  {pp(caida("tp", 0.5, "Metro"))} y {pp(caida("auto", 0.5, "Auto"))} pp con {tex("d = 0{,}5")},
  {pp(caida("tp", 1.28, "Metro"))} y {pp(caida("auto", 1.28, "Auto"))} pp con {tex("d = 1{,}28")}.
  Lo distinto es el denominador de (20). Quienes tienen el metro como mejor eligen casi todos entre
  dos modos ({tex("\\overline{1/J_n}")} = {num(uni_metro, 2)}) y su modo mejor está apenas
  {num(100 * margen("Metro"), 1)} pp sobre el reparto uniforme; los del auto, {
    num(100 * margen("Auto"), 1)
} pp.
  La misma pérdida es una fracción mucho mayor de una ventaja más chica, y Φ &lt; 0 sólo dice que la
  pérdida superó ese margen. Para comparar grupos hay que mirar las dos medidas (tabla 9).
</p>
{
    fig(
        "e4-phi-mejor.png",
        12,
        "Cuánto de la ventaja sobrevive según cuál sea el modo mejor de cada persona, en el mediano"
        " plazo (días 11–50). Un panel por condición de ruido. Eje horizontal: desviación estándar del"
        " tiempo vivido, σ (min). Eje vertical: Φ (adim.), ecuación (20), sobre las personas con ese"
        " modo mejor en el equilibrio; la línea discontinua en 1 es «nada cambió» y la punteada en 0,"
        " el reparto uniforme. Color: el modo mejor. Tipo de línea: d = 0,5 (continua) y 1,28"
        " (discontinua). Se lee por color: bajo 1 si el ruido está en ese modo, sobre 1 si está en una"
        " alternativa. La caída del metro se ve más grande que la del auto porque su P* − 1/J es"
        " chico (tabla 9).",
    )
}
{
    tabla(
        9,
        "Ventaja que sobrevive y pérdida en puntos, por modo mejor (σ = 80 min, días 11–50)",
        '<tr><th rowspan="2">Ruido en</th><th rowspan="2">Modo mejor</th>'
        '<th rowspan="2" class="n">Personas</th>'
        '<th rowspan="2" class="n">P* − 1/J (pp)</th>'
        '<th colspan="2" class="n">d = 0,5</th><th colspan="2" class="n">d = 1,28</th></tr>'
        "<tr>"
        + '<th class="n">Φ (adim.)</th><th class="n">Δ cuota del mejor (pp)</th>' * 2
        + "</tr>",
        filas_mejor,
        "Una fila por condición de ruido y modo mejor en el equilibrio, en el mediano plazo. P* − 1/J:"
        " cuánto está el modo mejor sobre el reparto uniforme en el equilibrio, el denominador de (20)."
        " Φ, ecuación (20): 1, nada cambió; 0, reparto uniforme; menos de 0, usa su modo mejor menos que"
        " el reparto uniforme. Δ cuota del mejor: cuota de días en el modo mejor menos P*. Se lee por"
        " pares de columnas: con el mismo Δ en puntos, Φ cae más donde P* − 1/J es chico (el metro).",
    )
}

<h3>7.3 Lo demás, como en E3</h3>
<p>
  Personas iguales terminan distintas y la decisión sobrestima la experiencia, más con recencia: con
  ruido en los dos modos, σ = 80 min y {tex("d = 1{,}28")}, {tex("R")} =
  {num(f4r["dispersion_iguales"], 2)} y {tex("B")} = {num(brecha_min(f4r), 2)} min por viaje. El
  bienestar experimentado cambia a lo sumo {
    num(exp4_max, 2)
} min por viaje. Lo nuevo es el abandono:
  la fracción de quienes tienen metro y no lo usaron ningún día de los últimos {
    C4["ultimos"]
} pasa de
  {num(100 * ab0, 1)} % sin ruido a {num(100 * ab_max, 1)} % con ruido en el metro y
  {tex("d = 1{,}28")}.
</p>
{
    tabla(
        10,
        "La ciudad con cuatro modos: partición, dispersión, bienestar y abandono (σ = 80 min)",
        '<tr><th rowspan="2">Ruido en</th><th rowspan="2" class="n simb">d (adim.)</th>'
        '<th colspan="4" class="n">Δ cuota (pp)</th><th rowspan="2" class="n simb">R (adim.)</th>'
        '<th rowspan="2" class="n">Δ bienestar experimentado (min/viaje)</th>'
        '<th rowspan="2" class="n simb">B (min/viaje)</th>'
        '<th rowspan="2" class="n">Abandono del metro (%)</th></tr>'
        "<tr>" + "".join(f'<th class="n">{m}</th>' for m in MODOS4) + "</tr>",
        filas_c4,
        f"Una fila por condición de ruido y decaimiento d; todo en los últimos {C4['ultimos']} días de"
        f" {C4['dias']}. Las Δ son contra el control sin ruido con el mismo d. R, ecuación (18), con"
        " grupos de personas del mismo estrato, celda y tenencia de auto, sobre el share de días en su"
        " modo mejor. Bienestar experimentado en minutos (÷|β|). B, ecuación (19). Abandono: fracción"
        " de quienes tienen metro que no lo usaron ningún día; sin ruido es"
        f" {num(100 * ab0, 1)} %. Se lee por columnas, como la tabla 7.",
    )
}
"""

# --- §8 ----------------------------------------------------------------------------------

s8 = f"""
<!-- ==================================================================== -->
<h2 id="s8"><span class="num">8</span>Qué concluir, y bajo qué supuestos</h2>

<ol>
  <li><strong>Hay un valor crítico de corto plazo y es simple:</strong> {tex("\\Delta^{*}_k = A/W_k")}.
      Una experiencia mala cambia la preferencia si dura más del doble de la ventaja; muchas, si cada una
      supera la ventaja. Exacto con {tex("d = 0")}, aproximado con recencia.</li>
  <li><strong>La persistencia tiene otro umbral</strong>, (14): no depende del tamaño de cada shock sino de
      la deuda total {tex("k \\cdot r")} contra la tasa con que la persona vuelve a probar. Es el hot stove
      propiamente tal, y con {tex("\\mu = 1")} exige shocks de horas.</li>
  <li><strong>El efecto de variabilidad existe pero es chico con {tex("\\mu = 1")}</strong>, es de corto
      plazo con {tex("d \\le 0{,}5")}, y el hot stove lo compensa cuando el ruido está en los dos modos.
      Lo que sí deja es heterogeneidad entre personas iguales.</li>
  <li><strong>En la ciudad completa (E3) pasa lo mismo, y la media lo esconde.</strong> La partición y
      el bienestar experimentado no cambian, pero personas iguales se diferencian, (18), y deciden con
      un modo que creen más rápido de lo que es, (19): el logsum de lo percibido sobrestima el
      bienestar, más cuanto más recencia.</li>
  <li><strong>Con los cuatro modos (E4), el ruido saca viajes hacia la bici y el promedio esconde
      signos opuestos.</strong> Quien vive el ruido en su modo mejor lo usa menos —en puntos, lo mismo
      si es el auto o el metro—, y quien lo vive en una alternativa lo usa más, (20). La partición sigue moviéndose
      poco y crece el abandono del metro.</li>
</ol>

<h3>8.1 Los supuestos que mueven los números</h3>
<ul>
  <li><strong>La escala.</strong> {tex("\\mu\\beta")} decide cuántos minutos es «mucho». Con el
      {tex("\\beta")} de elección repetida de la literatura ({tex("-0{,}2")}/min) los minutos de este
      informe se dividen por ~6; los resultados en múltiplos de {tex("A")} y en útiles no cambian.</li>
  <li><strong>El peso de la percepción inicial.</strong> Una instancia, {tex("a_{ni}(0) = 1")}, como en
      Guevara et al. (2018). Con {tex("m")} instancias, (7) da {tex("k/(k+m)")} con {tex("d = 0")}: una
      persona con más información previa resiste más. Es el <em>initial condition problem</em> del
      mismo paper, visto desde la simulación.</li>
  <li><strong>El decaimiento.</strong> {tex("d")} cambia poco el corto plazo y mucho el largo: con
      {tex("d > 1")} la memoria no promedia y los efectos de variabilidad persisten.</li>
  <li><strong>Φ con ventajas chicas.</strong> (13) y (20) dividen por {tex("P^{*} - 1/J")}; donde es
      chico, Φ amplifica. Para comparar grupos con ventajas distintas, mirar también la pérdida en
      puntos (tabla 9).</li>
  <li><strong>Congestión y costo de cambiar.</strong> En E1 y E2 una persona sola no mueve los
      tiempos; E3 y E4 sí cargan la red cada día. En ninguno hay inercia ni hábito más allá del IBL.</li>
</ul>

<h3>8.2 Lo que queda</h3>
<ul>
  <li><strong>Bici y caminata sin ruido.</strong> En E4 son el refugio por construcción; con ruido
      en la bici, la migración de §7.1 tendría otro destino.</li>
  <li><strong>Acceso y espera del metro fijos.</strong> En E3 y E4 el IBL aprende el tiempo en vehículo;
      acceso y espera quedan en los del equilibrio.</li>
  <li><strong>Una semilla por combinación.</strong> Las diferencias contra σ = 0 usan los mismos números
      aleatorios, pero no hay réplicas de la ciudad.</li>
</ul>

<h3>8.3 Referencias</h3>
<ul class="refs">
  <li>Guevara, C. A., Tang, Y. y Gao, S. (2018). The initial condition problem with complete history
      dependency in learning models for travel choices. <em>Transportation Research Part B</em> 117,
      850–861. — <code>papers/2018 Guevara Tang Gao TRB.pdf</code></li>
  <li>Henríquez-Jara, B. y Guevara, C. A. (2025). An Experience-Based Choice Model (EBCM): Formulation,
      identification, behavioural insights and well-being assessment. <em>Journal of Choice
      Modelling</em> 55, 100552. — <code>papers/1-s2.0-S1755534525000156-main.pdf</code></li>
  <li>Tang, Y. y Gao, S. (2017). An exploratory study of instance-based learning for route choice with
      random travel times. <em>Journal of Choice Modelling</em> 24, 22–33. (Citado por los dos
      anteriores; no revisado directamente.)</li>
  <li>Denrell, J. y March, J. G. (2001), sobre el <em>hot stove effect</em>, y Erev, I. y Barron, G.
      (2005), sobre el <em>payoff variability effect</em>: citados de memoria, sin verificar contra el
      texto.</li>
</ul>
"""

# --- Reproducir -----------------------------------------------------------------------

mapa = [
    ("(1)", "pesos del IBL", linea("ibl.py", "pesos_ibl")),
    ("(2)", "tiempo percibido", linea("ibl.py", "tiempo_percibido")),
    ("(3)–(5)", "utilidad, logit, experiencia", linea("experimentos.py", "simular")),
    ("(6)", "ΔV, A, P*", linea("experimentos.py", "Caso")),
    ("(7)", "W_k", linea("experimentos.py", "peso_shocks")),
    ("(8)", "Δ*", linea("experimentos.py", "delta_critico")),
    ("(9)", "P post", linea("experimentos.py", "p_post_analitica")),
    ("(10)", "P̄ por persona", linea("experimentos.py", "cuota_por_persona")),
    ("(11), (13)", "S, E, I, cuantiles, histograma", linea("experimentos.py", "resumen_ventanas")),
    ("(12)", "vida media", linea("experimentos.py", "vida_media")),
    ("(13)", "Φ", linea("experimentos.py", "e2")),
    ("(14)", "n*", linea("arma_informe.py", "n_ast")),
    (
        "(15)–(17)",
        "ventaja percibida, dispersión y sesgo",
        linea("experimentos.py", "descomposicion"),
    ),
    ("(16)", "Gauss–Hermite", linea("experimentos.py", "gauss_logistica")),
    ("(13), ciudad", "Φ de la población", linea("poblacion.py", "_phi")),
    ("(18)", "R, dispersión entre iguales", linea("poblacion.py", "_dispersion_iguales")),
    ("(19)", "B, decisión − experiencia", linea("poblacion.py", "simular")),
    ("(20)", "Φ con J modos, por modo mejor", linea("poblacion.py", "_phi")),
    ("E4", "condiciones de ruido", linea("poblacion.py", "CONDICIONES")),
]
filas_mapa = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in mapa)
reproducir = f"""
<!-- ==================================================================== -->
<h2 id="reproducir">Reproducir paso a paso</h2>

<pre><code>cd sandbox/ibl-dia-a-dia
uv sync --extra dev --reinstall-package titirilquen-core   # el núcleo del repo, no uno cacheado
uv run --extra dev pytest                                  # las fórmulas (7)–(9), (12) y (16)
uv run python experimentos.py           # ~5 min → salida/experimentos.json
uv run python poblacion.py              # ~20 min → salida/poblacion.json (E3)
uv run python poblacion.py ciudad       # ~15 min → salida/ciudad4.json (E4)
uv run python figuras_experimentos.py   # figuras 1–12, desde los tres JSON
uv run python arma_informe.py           # este informe, desde los tres JSON
node ../../tools/renderiza_ecuaciones.js   # data-tex → MathML</code></pre>

<p>
  Cada número del texto sale de <code>salida/experimentos.json</code>: <code>casos</code> (tabla de §2.1,
  {tex("W_k")} y {tex("\\Delta^*")}), <code>e1</code> (una fila por caso, {tex("d")}, {tex("k")},
  {tex("r")}, más el control) y <code>e2</code> (una por caso, {
    tex("d")
}, condición, σ). E3 sale de <code>salida/poblacion.json</code>: una fila por σ y {tex("d")}.
  E4, de <code>salida/ciudad4.json</code>: una fila por condición, σ y {tex("d")}, más el
  control sin ruido.
  Las figuras no calculan nada.
</p>
{
    tabla(
        11,
        "Dónde está cada ecuación en el código",
        "<tr><th>Ecuación (número del informe)</th><th>Qué calcula</th><th>Archivo:línea</th></tr>",
        filas_mapa,
        "Una fila por ecuación del informe, con la función que la implementa. Las líneas se buscan"
        " en el código cada vez que se arma el informe, así que siempre apuntan a la versión vigente.",
    )
}
<p class="pie-tabla">
  Tests: <code>test_ibl.py</code> (propiedades de (1)–(2)) y <code>test_experimentos.py</code>: (7)
  igual a los pesos de <code>ibl.py</code>, (9) igual a la simulación con {
    tex("d = 0")
}, (8) anula la
  ventaja, la dispersión acerca a ½, y sin ruido ni shock no hay aprendizaje.
  Los scripts de la versión anterior del informe (<code>persona.py</code>, <code>pve.py</code>,
  <code>sensibilidad.py</code>) siguen en la carpeta; <code>poblacion.py</code> es ahora E3 y E4.
</p>

</div>
</body>
</html>
"""

html = cabeza + s1 + s2 + s3 + s4 + s5 + s6 + s7 + s8 + reproducir
(AQUI / "informe.html").write_text(html, encoding="utf-8", newline="\n")
print(f"  informe.html: {len(html):,} caracteres")
