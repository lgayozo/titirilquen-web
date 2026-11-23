"""Informe del experimento E4 — la ciudad de cuatro modos.

Lee las dos escalas del logit y escribe `informe-e4.html`:

    uv run python poblacion.py ciudad              -> salida/ciudad4.json
    uv run python poblacion.py ciudad --guevara    -> salida/ciudad4-guevara.json
    uv run python figuras_experimentos.py          (y --guevara)
    uv run python informe_e4.py
    node ../../tools/renderiza_ecuaciones.js

Ningun numero se tipea a mano: todos salen de los dos JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from informe_comun import ec, fig, linea, miles, ntex, num, pagina, pp, sim, tabla, tex

AQUI = Path(__file__).parent
SALIDA = AQUI / "salida"
BASE = json.loads((SALIDA / "ciudad4.json").read_text(encoding="utf-8"))
GUEV = json.loads((SALIDA / "ciudad4-guevara.json").read_text(encoding="utf-8"))

# El beta del nucleo, para pasar utiles a minutos: `poblacion.py` mide el bienestar
# en utiles del NUCLEO (mu entra solo en el softmax), asi que la conversion usa el
# mismo beta en las dos escalas. El de los JSON de E1/E2 viene escalado.
_E12 = json.loads((SALIDA / "experimentos.json").read_text(encoding="utf-8"))
BETA = abs(next(c for c in _E12["casos"] if c["nombre"] == "C2")["beta"]) / _E12.get("escala", 1.0)

K = GUEV["filas"][0]["mu"]
MODOS = BASE["modos"]
SIGMAS = sorted({f["sigma"] for f in BASE["filas"] if f["sigma"] > 0})
DECS = sorted({f["d"] for f in BASE["filas"]})
CONDS = tuple(BASE["condiciones"])
D_REF = 1.28
U = BASE["ultimos"]
NOM_COND = {
    "auto": "sólo en el auto",
    "tp": "sólo en el metro",
    "auto_tp": "en el auto y en el metro",
}
NOM_W = {"corto": "días 1–10", "medio": "días 11–50", "largo": "días 51–250"}
# `condiciones` trae un booleano por modo APRENDIDO, no por modo: la caminata no se
# aprende (su tiempo es geométrico), así que ni figura en la lista ni lleva ruido.
N_APRENDIDOS = len(BASE["condiciones"][CONDS[0]])


def lleva_ruido(cond: str, i: int) -> bool:
    """Si el modo `i` lleva ruido en esa condición."""
    fila = BASE["condiciones"][cond]
    return bool(fila[i]) if i < len(fila) else False


# Los modos que nunca llevan ruido: su tiempo no tiene variabilidad en este diseño.
SIN_RUIDO = [m for i, m in enumerate(MODOS) if not any(lleva_ruido(c, i) for c in CONDS)]


def f4(D: dict, cond: str, sigma: float, d: float) -> dict:
    """La fila de E4 de una celda del diseño."""
    return next(
        x for x in D["filas"] if x["condicion"] == cond and x["sigma"] == sigma and x["d"] == d
    )


def base0(D: dict, d: float) -> dict:
    """El control sin ruido de esa memoria."""
    return f4(D, "sin_ruido", 0.0, d)


def par(cond: str, sigma: float, d: float) -> tuple[dict, dict]:
    return f4(BASE, cond, sigma, d), f4(GUEV, cond, sigma, d)


def brecha_min(f: dict) -> float:
    """Utilidad de decisión menos la experimentada, en minutos de viaje."""
    dec = sum(f["bienestar_decision_por_dia"][-U:]) / U
    exp = sum(f["bienestar_por_dia"][-U:]) / U
    return (dec - exp) / BETA


def dsplit(D: dict, cond: str, sigma: float, d: float) -> list[float]:
    """Cambio de cuota por modo contra el control sin ruido, en puntos."""
    r, b = f4(D, cond, sigma, d), base0(D, d)
    return [a - c for a, c in zip(r["split_ultimos"], b["split_ultimos"], strict=True)]


# --- 1. Preguntas ---------------------------------------------------------------


def s1() -> str:
    smax = SIGMAS[-1]
    d_auto = dsplit(BASE, "auto", smax, D_REF)
    i_bici = MODOS.index("Bici")
    b_tp = f4(BASE, "tp", smax, D_REF)
    g_tp = f4(GUEV, "tp", smax, D_REF)
    pm = b_tp["phi"]["por_mejor"]
    return f"""
<h2 id="preguntas">1. Preguntas de investigación</h2>

<p>E3 pone ruido en <strong>todos</strong> los modos que la gente aprende. Pero en una
ciudad real la variabilidad no se reparte pareja: el auto tiene congestión, el metro
tiene su propia irregularidad, y caminar tarda lo que tarda. E4 pregunta qué pasa cuando
el ruido está en unos modos y no en otros. Cuatro preguntas, con los
{tex(r"\beta")} del simulador.</p>

<p><strong>P1. ¿A dónde van los viajes que el ruido expulsa?</strong> Al modo que no lo
tiene. Con {tex(r"\sigma")} = {num(smax, 0)} min sólo en el auto, la cuota del auto cae
{num(100 * abs(d_auto[MODOS.index("Auto")]), 1)} puntos y
{" y ".join(SIN_RUIDO)} {"reciben" if len(SIN_RUIDO) > 1 else "recibe"} buena parte: la
bici sola gana {num(100 * abs(d_auto[i_bici]), 1)} puntos. <strong>La variabilidad no
sólo empeora las decisiones: redistribuye viajes</strong>, y lo hace hacia donde no hay
nada que aprender.</p>

<p><strong>P2. ¿A quién daña?</strong> A quien tiene el ruido en <em>su</em> modo mejor,
y a nadie más. Con el ruido sólo en el metro, quienes deberían usar el metro quedan en
{tex(r"\Phi")} = {num(pm["Metro"]["largo"], 2)}; quienes deberían usar la bici, en
{num(pm["Bici"]["largo"], 2)} —<em>mejor</em> que sin ruido—. Es la asimetría de E2, pero
acá no se impone por diseño: <strong>sale sola de quién es cada persona</strong>.</p>

<p><strong>P3. ¿Sirve mirar el promedio?</strong> No, y E4 lo muestra con un caso
incómodo: en esa misma celda el {tex(r"\Phi")} agregado de toda la ciudad vale
{num(b_tp["phi"]["todos"]["largo"], 2)} — <strong>por encima de 1</strong>, o sea «la
ciudad elige mejor que con información perfecta». Un promedio que no sólo tranquiliza:
miente de signo.</p>

<p><strong>P4. ¿Cuánto depende de la calibración?</strong> El tamaño, no el mecanismo.
Con los {tex(r"\beta")} de la literatura (§4) el grupo del metro pasa de
{num(pm["Metro"]["largo"], 2)} a
{num(g_tp["phi"]["por_mejor"]["Metro"]["largo"], 2)} y la redistribución se multiplica.
La §4.4 muestra además por qué en la ciudad esa columna no es una reescala inocua.</p>
"""


# --- 2. El experimento ----------------------------------------------------------


def s2() -> str:
    filas = "".join(
        f"<tr><td>{m}</td><td class='n'>{num(100 * v, 2)}</td>"
        f"<td>{'sí' if any(lleva_ruido(c, i) for c in CONDS) else 'no'}</td>"
        f"<td>{'sí' if i < N_APRENDIDOS else 'no'}</td></tr>"
        for i, (m, v) in enumerate(zip(MODOS, BASE["split_equilibrio"], strict=True))
    )
    t1 = tabla(
        1,
        "La ciudad de cuatro modos, día 0",
        "<tr><th>modo</th><th class='n'>cuota de equilibrio (%)</th>"
        "<th>puede llevar ruido</th><th>se aprende</th></tr>",
        filas,
        f"La configuración de la app tal cual: tenencia de auto por estrato y los cuatro "
        f"modos. El ruido va sobre el auto y sobre el metro, nunca sobre la bici ni la "
        f"caminata. Se aprenden auto, metro y bici —la bici se congestiona en la "
        f"ciclovía—; la caminata no, porque su tiempo es geométrico y no tiene ni "
        f"congestión ni ruido. <strong>Que {' y '.join(SIN_RUIDO)} no "
        f"{'lleven' if len(SIN_RUIDO) > 1 else 'lleve'} ruido es el punto del "
        f"experimento</strong>, no una omisión: es lo que permite ver hacia dónde se "
        f"desplazan los viajes.",
    )
    return f"""
<h2 id="experimento">2. El experimento</h2>

<p>La misma mecánica de E3 —{miles(BASE["N"])} agentes, {BASE["dias"]} días, la red cargando
y respondiendo cada día— con dos diferencias. La primera: los cuatro modos de la app, con
la tenencia de auto por estrato, así que cada persona elige entre los {tex("J_n")} modos
que le son factibles y no entre dos. La segunda, que es la pregunta de E4:
<strong>el ruido va sobre unos modos y no sobre otros</strong>.</p>

<p>Tres condiciones:</p>
<ul>
{"".join(f"<li><strong>Ruido {NOM_COND[c]}</strong></li>" for c in CONDS)}
</ul>

<p>más un control sin ruido. Cruzadas con {len(SIGMAS)} niveles —{tex(r"\sigma")} ∈
{{{", ".join(num(s, 0) for s in SIGMAS)}}} min— y {len(DECS)} de memoria —{tex("d")} ∈
{{{", ".join(num(d, 2) for d in DECS)}}}—, en las dos escalas del logit de la §4.</p>

{t1}

<p>Con más de dos modos, el punto de indiferencia de {tex(r"\Phi")} ya no es ½ sino
{tex("1/J_n")}, el reparto uniforme entre los modos factibles de cada persona. Eso
importa al leer la tabla 6: donde {tex("P^*")} está cerca de {tex("1/J_n")}, el
denominador es chico y {tex(r"\Phi")} amplifica.</p>
"""


# --- 3. El modelo ---------------------------------------------------------------


def s3() -> str:
    return f"""
<h2 id="modelo">3. El modelo</h2>

<p>Es el de E3, con {tex("J_n")} modos en vez de dos. Lo repetimos corto para que este
informe se lea solo.</p>

<p>Cada persona cree que el modo {tex("i")} tarda el promedio ponderado de lo que
<strong>vivió</strong> en ese modo, con los días recientes pesando más y los días en que
no lo eligió sin entrar:</p>

{ec(r"b_{ni}(t) \;=\; \sum_{t' \lt t} w_{ni}(t', t)\, x_{ni}(t'), \qquad w_{ni} \;\propto\; a_{ni}(t')\,(t - t')^{-d}", 1)}

<p>{tex("x_{ni}(t')")} es el tiempo que la red entregó ese día en su celda, más su
{tex(r"\varepsilon")} propio <em>si ese modo lleva ruido en esa condición</em>. El prior
es el tiempo de equilibrio del día 0 ({linea("ibl.py", "tiempo_percibido")}).</p>

{ec(r"V_{ni}(t) \;=\; \bar V_i \;+\; \beta\,\bigl(b_{ni}(t) - \tau_i\bigr), \qquad P_{ni}(t) \;=\; \frac{e^{\mu V_{ni}(t)}}{\sum_{j} e^{\mu V_{nj}(t)}}", 2)}

<p>{tex(r"\bar V_i")} sale del núcleo, así que constantes modales, costo,
penalizaciones y factibilidad quedan como las calcula el simulador. La caminata no se
aprende: su tiempo es geométrico y vive entero en {tex(r"\bar V")}.</p>

<p>El indicador central generaliza el de E2 al caso de varios modos:</p>

{ec(r"\Phi \;=\; \frac{\bar S - \overline{1/J}}{\bar P^{*} - \overline{1/J}}", 3)}

<p>donde {tex(r"\bar S")} es la cuota media del modo que de verdad es mejor para cada
persona y {tex(r"\bar P^{*}")} la de quien conoce los tiempos de equilibrio. Con dos
modos {tex("1/J")} = ½ y es la de E2 tal cual. Se calcula en total y, lo que acá
importa, <strong>separando a la gente por cuál es su modo mejor</strong>
({linea("poblacion.py", "_phi")}).</p>

<p>Y la brecha entre lo que se cree y lo que se vive, en minutos:</p>

{ec(r"B \;=\; \frac{\mathbb{E}\bigl[V^{\text{decisión}}\bigr] - \mathbb{E}\bigl[V^{\text{experimentada}}\bigr]}{|\beta|}", 4)}

<p>Los dos bienestares están en útiles del núcleo —{tex(r"\mu")} entra sólo en la
ec. (2), no multiplica {tex("V")}—, así que {tex("B")} es comparable entre escalas con
el mismo {tex(r"\beta")} = {num(-BETA, 4)} útiles/min.</p>
"""


# --- 4. La escala ---------------------------------------------------------------


def _t_reeq() -> str:
    """El dia 0 contra el equilibrio al que llega cada escala sin nada de ruido."""
    dia0 = BASE["split_equilibrio"]
    cb, cg = base0(BASE, D_REF), base0(GUEV, D_REF)
    filas = "".join(
        f"<tr><td>{m}</td>"
        f"<td class='n'>{num(100 * dia0[i], 2)}</td>"
        f"<td class='n'>{num(100 * cb['split_ultimos'][i], 2)}</td>"
        f"<td class='n'>{num(100 * cg['split_ultimos'][i], 2)}</td></tr>"
        for i, m in enumerate(MODOS)
    )
    salto = 100 * (cg["split_ultimos"][0] - dia0[0])
    return tabla(
        3,
        "El día 0 deja de ser equilibrio — cuota (%) sin nada de ruido",
        f"<tr><th>modo</th><th class='n'>día 0 (MSA, {sim('μ')} = 1)</th>"
        f"<th class='n'>control (simulador)</th>"
        f"<th class='n'>control (β × {num(K, 1)})</th></tr>",
        filas,
        f"Las tres columnas son la misma ciudad, sin ningún ruido. Con {sim('μ')} = 1 la "
        f"dinámica se queda donde el MSA la dejó —es el control de que todo está bien "
        f"conectado—. Con los β de la literatura el auto salta {num(abs(salto), 1)} puntos el "
        f"primer día y se asienta ahí: el logit más afilado concentra la demanda y la "
        f"congestión acomoda el resto. Por eso {sim('Φ')} del control vale "
        f"{num(cg['phi']['todos']['largo'], 3)} y no 1.",
    )


def s4() -> str:
    bsim, blit = BETA, BETA * K
    t2 = tabla(
        2,
        "Guevara, Tang y Gao (2018), tabla 4, dataset completo",
        "<tr><th>parámetro</th><th class='n'>d</th><th class='n'>TIMEF</th>"
        "<th class='n'>TIMES</th><th class='n'>LRISK</th><th class='n'>FRISKY</th>"
        "<th class='n'>CWA</th></tr>",
        "<tr><td>estimación</td><td class='n'>1,28</td><td class='n'>−0,198</td>"
        "<td class='n'>−0,086</td><td class='n'>0,864</td><td class='n'>0,405</td>"
        "<td class='n'>5,71</td></tr>"
        "<tr><td>error estándar</td><td class='n'>0,137</td><td class='n'>0,015</td>"
        "<td class='n'>0,013</td><td class='n'>0,144</td><td class='n'>0,12</td>"
        "<td class='n'>0,192</td></tr>",
        "TIMEF multiplica el tiempo <em>percibido</em> de la ruta rápida (su ec. 15), "
        "no el real: es el análogo exacto de nuestro tiempo del IBL. TIMES es el de la "
        "ruta lenta — son dos coeficientes específicos de alternativa dentro del mismo "
        "modelo, no un rango. De acá sale también el d = 1,28 que usamos de referencia, "
        "que el paper subraya como estimado y no fijado.",
    )
    razon = (
        r"\frac{|\beta|_{\text{lit}}}{|\beta|_{\text{sim}}} \;=\; \frac{"
        + ntex(blit, 3)
        + "}{"
        + ntex(bsim, 4)
        + r"} \;=\; "
        + ntex(blit / bsim, 3)
    )
    return f"""
<h2 id="escala">4. La calibración de {tex(r"\beta")}, y qué tan lejos puede estar</h2>

<p>Todo lo que sigue está calculado con los {tex(r"\beta")} del simulador. Esta sección
explica qué son, por qué la literatura de elección repetida sugiere valores bastante
mayores, y por qué eso se reporta como <strong>sensibilidad</strong> y no como
corrección.</p>

<h3>4.1 {tex(r"\mu")} = 1 no es una medición, es una convención</h3>

<p>En un logit sólo se identifica el producto {tex(r"\mu\beta")}: multiplicar la escala
por un número y dividir los coeficientes por el mismo deja <em>exactamente</em> las
mismas probabilidades. Por eso el logit de transporte del simulador fija
{tex(r"\mu")} = 1 —{linea("../../packages/titirilquen_core/src/titirilquen_core/demand/choice.py", "probabilidades_logit", "titirilquen_core/demand/choice.py")}
calcula {tex("e^V")} a secas, sin ninguna escala— y son los {tex(r"\beta")} los que la
absorben.</p>

<p>La consecuencia importa: <strong>{tex(r"\mu")} no es una perilla disponible, ya está
consumida</strong>. Los {tex(r"\beta")} valen lo que valen porque, con
{tex(r"\mu")} = 1, reproducen una partición modal observada. (El {tex(r"\mu")} del uso
de suelo es otra cosa: ahí sí es un parámetro de escenario, porque fija cuánto pesa el
ruido de localizarse frente a una accesibilidad que ya trae su propia escala.)</p>

<h3>4.2 Qué dice la literatura de elección repetida</h3>

<p>Guevara, Tang y Gao (2018) estiman un IBL con los datos de laboratorio de ruta de
Ben-Elia y Shiftan (2010) —que es casi exactamente el experimento que estos informes
simulan— y obtienen:</p>

{t2}

<p>Su coeficiente de tiempo es {num(-blit, 3)} útiles/min contra los
{num(-bsim, 4)} del simulador:</p>

{ec(razon, 5)}

<h3>4.3 Por qué no lo adoptamos</h3>

<p>Tomar ese número <em>no</em> es «elegir otra escala». Como {tex(r"\mu")} ya está
normalizado, equivale a afirmar que los {tex(r"\beta")} de transporte del simulador son
seis veces chicos — es decir, que la elección modal del modelo es mucho más ruidosa de
lo que sería en la realidad. Y eso contradice su calibración, que es lo que fija esos
{tex(r"\beta")}.</p>

<p>Hay además una razón de fondo: <strong>la escala del logit no es transferible entre
contextos de elección</strong>. El dato de Guevara viene de elegir entre dos rutas que
difieren sólo en tiempo, en laboratorio, con información en pantalla. Elegir entre auto,
metro, bici y caminata en una ciudad real es una decisión con mucha más heterogeneidad
no observada — y esa heterogeneidad es precisamente lo que un {tex(r"\beta")} chico
representa. Su valor no es «el verdadero» que el simulador debería copiar.</p>

<p>Por eso los resultados van con los {tex(r"\beta")} del simulador y las tablas traen
una columna <strong>«{tex(r"\beta")} × {num(blit / bsim, 1)}»</strong> como
sensibilidad de calibración: dice cuánto crecería cada efecto si la elección modal fuera
tan determinista como sugiere el laboratorio. Cuando un efecto se vea chico, esa columna
contesta la pregunta obligada — <em>¿chico de verdad, o chico porque el modelo elige con
demasiado ruido?</em></p>

<h3>4.4 En la ciudad, la sensibilidad no es neutral</h3>

<p>En los experimentos de una persona la red está congelada y subir la escala sólo afila
la elección. Acá no: el día 0 es el equilibrio que calcula el MSA del núcleo con
{tex(r"\mu")} = 1, y con los {tex(r"\beta")} multiplicados ese reparto deja de ser un
punto fijo. La ciudad se corre sola, sin ningún ruido.</p>

{_t_reeq()}

<p>Es la forma más directa de ver lo de la §4.1: los {tex(r"\beta")} estaban calibrados
para reproducir esa partición, así que multiplicarlos la rompe. De ahí dos reglas de
lectura: <strong>la línea base es el control sin ruido de cada columna</strong>, y
<strong>los {tex(r"\Phi")} no se comparan entre columnas en valor absoluto</strong> —lo
comparable es cuánto cae cada uno al subir {tex(r"\sigma")}.</p>
"""


# --- 5. Resultados --------------------------------------------------------------


def _t3() -> str:
    cb, cg = base0(BASE, D_REF), base0(GUEV, D_REF)
    # Primera fila: el control sin ruido. Sin el, con los β de la literatura no se
    # distingue el efecto del ruido del reequilibrio de la seccion 4.1.
    filas = (
        "<tr><td><em>sin ruido</em></td><td class='n'>0</td>"
        + "".join(
            f"<td class='n'><em>{num(cb['phi']['todos'][w], 3)}</em></td>"
            f"<td class='n'><em>{num(cg['phi']['todos'][w], 3)}</em></td>"
            for w in ("corto", "medio", "largo")
        )
        + "</tr>"
    )
    for c in CONDS:
        for s in SIGMAS:
            a, g = par(c, s, D_REF)
            filas += (
                f"<tr><td>{NOM_COND[c]}</td><td class='n'>{num(s, 0)}</td>"
                + "".join(
                    f"<td class='n'>{num(a['phi']['todos'][w], 3)}</td>"
                    f"<td class='n'>{num(g['phi']['todos'][w], 3)}</td>"
                    for w in ("corto", "medio", "largo")
                )
                + "</tr>"
            )
    cab = (
        f"<tr><th rowspan='2'>ruido</th><th rowspan='2' class='n'>{sim('σ')} (min)</th>"
        + "".join(f"<th colspan='2'>{NOM_W[w]}</th>" for w in ("corto", "medio", "largo"))
        + "</tr><tr>"
        + "".join(
            f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in range(3)
        )
        + "</tr>"
    )
    return tabla(
        5,
        f"Φ agregado de la ciudad, {sim('d')} = {num(D_REF, 2)}",
        cab,
        filas,
        f"Promedio sobre toda la población, ec. (3). <strong>La primera fila es el "
        f"control sin ruido: el impacto del ruido es la caída respecto de ella</strong>, "
        f"no el nivel. Con los β de la literatura ese control ya vale "
        f"{num(base0(GUEV, D_REF)['phi']['todos']['largo'], 3)} por el reequilibrio de la "
        f"§4.1, no por el ruido. Ojo con los valores por encima de 1: "
        "no son un error, significan que la ciudad en conjunto elige su modo mejor más "
        "seguido que con información perfecta. La tabla 6 muestra lo que ese promedio "
        "esconde.",
    )


def _t4() -> str:
    smax = SIGMAS[-1]
    filas = ""
    for c in CONDS:
        db, dg = dsplit(BASE, c, smax, D_REF), dsplit(GUEV, c, smax, D_REF)
        filas += (
            f"<tr><td>{NOM_COND[c]}</td>"
            + "".join(
                f"<td class='n'>{pp(db[i], 2)}</td><td class='n'>{pp(dg[i], 2)}</td>"
                for i in range(len(MODOS))
            )
            + "</tr>"
        )
    cab = (
        "<tr><th rowspan='2'>ruido</th>"
        + "".join(f"<th colspan='2'>{m}</th>" for m in MODOS)
        + "</tr><tr>"
        + "".join(f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in MODOS)
        + "</tr>"
    )
    eq = "  ".join(
        f"{m} {num(100 * v, 2)} %"
        for m, v in zip(MODOS, base0(BASE, D_REF)["split_ultimos"], strict=True)
    )
    return tabla(
        4,
        f"A dónde van los viajes — cambio de cuota (pp) con {sim('σ')} = {num(smax, 0)} min, "
        f"{sim('d')} = {num(D_REF, 2)}",
        cab,
        filas,
        f"Contra el control sin ruido, cuya partición es: {eq}. El patrón es el mismo en "
        f"las dos escalas y más fuerte en la de Guevara: <strong>el modo que lleva ruido "
        f"pierde y {' y '.join(SIN_RUIDO)}, que nunca lo "
        f"{'llevan' if len(SIN_RUIDO) > 1 else 'lleva'}, "
        f"{'ganan' if len(SIN_RUIDO) > 1 else 'gana'}</strong>. No es que la bici se haya "
        f"vuelto mejor: es que dejó de competir contra algo que la gente puede evaluar "
        f"bien.",
    )


def _t5() -> str:
    smax = SIGMAS[-1]
    cb, cg = base0(BASE, D_REF), base0(GUEV, D_REF)
    # Primer bloque: el control sin ruido, modo por modo.
    filas = "".join(
        f"<tr><td><em>sin ruido</em></td><td>{m}</td><td>no</td>"
        f"<td class='n'>{miles(cg['phi']['por_mejor'][m]['n'])}</td>"
        f"<td class='n'>{num(cb['phi']['por_mejor'][m]['p_estrella'], 3)}</td>"
        f"<td class='n'>{num(cg['phi']['por_mejor'][m]['uniforme'], 3)}</td>"
        f"<td class='n'><em>{num(cb['phi']['por_mejor'][m]['largo'], 3)}</em></td>"
        f"<td class='n'><em>{num(cg['phi']['por_mejor'][m]['largo'], 3)}</em></td></tr>"
        for m in MODOS
        if m in cg["phi"]["por_mejor"]
    )
    for c in CONDS:
        a, g = par(c, smax, D_REF)
        for m in MODOS:
            if m not in g["phi"]["por_mejor"]:
                continue
            va, vg = a["phi"]["por_mejor"][m], g["phi"]["por_mejor"][m]
            lleva = lleva_ruido(c, MODOS.index(m))
            filas += (
                f"<tr><td>{NOM_COND[c]}</td><td>{m}</td>"
                f"<td>{'sí' if lleva else 'no'}</td>"
                f"<td class='n'>{miles(vg['n'])}</td>"
                f"<td class='n'>{num(va['p_estrella'], 3)}</td>"
                f"<td class='n'>{num(vg['uniforme'], 3)}</td>"
                f"<td class='n'>{num(va['largo'], 3)}</td>"
                f"<td class='n'>{num(vg['largo'], 3)}</td></tr>"
            )
    cab = (
        "<tr><th>ruido</th><th>su modo mejor</th><th>¿lleva ruido?</th>"
        "<th class='n'>personas</th>"
        f"<th class='n'>{sim('P*')} (simulador)</th>"
        f"<th class='n'>{sim('1/J')}</th>"
        f"<th class='n'>{sim('Φ')} (simulador)</th>"
        f"<th class='n'>{sim('Φ')} (β × {num(K, 1)})</th></tr>"
    )
    return tabla(
        6,
        f"Quién paga — Φ a largo plazo según cuál es su modo mejor "
        f"({sim('σ')} = {num(smax, 0)} min, {sim('d')} = {num(D_REF, 2)})",
        cab,
        filas,
        f"Ésta es la tabla del informe. <strong>El primer bloque es el control sin "
        f"ruido: contra él se lee todo lo demás.</strong> "
        f"La columna «¿lleva ruido?» dice si la "
        f"variabilidad cayó sobre el modo que a esa persona le convenía. Donde dice "
        f"<strong>sí</strong>, {sim('Φ')} se hunde; donde dice <strong>no</strong>, se "
        f"queda en 1 o lo pasa. Es la asimetría de E2 —«ruido sólo en el mejor» contra "
        f"«sólo en el peor»— pero acá no se impuso por diseño: cada persona cae de un lado "
        f"o del otro según quién es. {sim('P*')} y {sim('1/J')} están para leer con "
        f"cuidado los grupos donde el denominador de la ec. (3) es chico.",
    )


def _t6() -> str:
    cb, cg = base0(BASE, D_REF), base0(GUEV, D_REF)
    # Primera fila: el control sin ruido.
    filas = (
        "<tr><td><em>sin ruido</em></td><td class='n'>0</td>"
        f"<td class='n'><em>{num(cb['dispersion_iguales'], 2)}</em></td>"
        f"<td class='n'><em>{num(cg['dispersion_iguales'], 2)}</em></td>"
        f"<td class='n'><em>{num(brecha_min(cb), 2)}</em></td>"
        f"<td class='n'><em>{num(brecha_min(cg), 2)}</em></td></tr>"
    )
    for c in CONDS:
        for s in SIGMAS:
            a, g = par(c, s, D_REF)
            filas += (
                f"<tr><td>{NOM_COND[c]}</td><td class='n'>{num(s, 0)}</td>"
                f"<td class='n'>{num(a['dispersion_iguales'], 2)}</td>"
                f"<td class='n'>{num(g['dispersion_iguales'], 2)}</td>"
                f"<td class='n'>{num(brecha_min(a), 2)}</td>"
                f"<td class='n'>{num(brecha_min(g), 2)}</td></tr>"
            )
    cab = (
        f"<tr><th rowspan='2'>ruido</th><th rowspan='2' class='n'>{sim('σ')} (min)</th>"
        f"<th colspan='2'>dispersión entre iguales, {sim('R')}</th>"
        f"<th colspan='2'>{sim('B')}: se cree mejor por (min/viaje)</th></tr><tr>"
        + "".join(
            f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in range(2)
        )
        + "</tr>"
    )
    return tabla(
        7,
        f"Dependencia de la trayectoria y error de percepción, {sim('d')} = {num(D_REF, 2)}",
        cab,
        filas,
        f"<strong>La primera fila es el control sin ruido.</strong> "
        f"{sim('R')} = 1 significa que personas idénticas —mismo estrato, celda y tenencia "
        f"de auto— se comportan como si tiraran la misma moneda; más de 1, que la historia "
        f"las diferenció. {sim('B')} es la ec. (4). Los dos indicadores se definen igual "
        f"que en E3, así que los informes se pueden comparar.",
    )


def s5() -> str:
    return f"""
<h2 id="resultados">5. Resultados</h2>

<h3>5.1 A dónde van los viajes</h3>

{_t4()}

{fig("e4-particion.png", 1, f"Cambio de cuota por modo contra σ, un panel por condición, con los β del simulador ({tex(r'\mu')} = 1).")}

{fig("e4-particion-guevara.png", 2, f"Lo mismo con los β de la literatura ({tex(r'\mu')} = {num(K, 2)}).")}

<h3>5.2 El promedio</h3>

{_t3()}

<h3>5.3 Quién paga</h3>

{_t5()}

{fig("e4-phi-mejor.png", 3, "Φ según cuál es el modo mejor de cada persona, contra σ. Escala vieja. Las curvas se separan por grupo: el daño no es de la ciudad, es de quienes tienen el ruido encima.")}

{fig("e4-phi-mejor-guevara.png", 4, "Lo mismo con los β de la literatura.")}

<h3>5.4 La historia y la percepción</h3>

{_t6()}
"""


# --- 6. Análisis ----------------------------------------------------------------


def s6() -> str:
    smax = SIGMAS[-1]
    b_tp = f4(BASE, "tp", smax, D_REF)
    b_auto = f4(BASE, "auto", smax, D_REF)
    cb = base0(BASE, D_REF)
    pm_tp, pm_auto = b_tp["phi"]["por_mejor"], b_auto["phi"]["por_mejor"]
    i_bici = MODOS.index("Bici")
    return f"""
<h2 id="analisis">6. Análisis</h2>

<h3>6.1 La variabilidad es un impuesto sobre el modo que la tiene</h3>

<p>La tabla 4 dice algo simple y poco intuitivo: el ruido no sólo empeora las
decisiones, <strong>mueve demanda</strong>. Y la mueve hacia donde no hay nada que
aprender. La bici no mejoró en absoluto —su tiempo es el mismo— pero gana
{num(100 * abs(dsplit(BASE, "auto", smax, D_REF)[i_bici]), 2)} pp cuando el ruido está
en el auto y {num(100 * abs(dsplit(BASE, "tp", smax, D_REF)[i_bici]), 2)} pp cuando está
en el metro.</p>

<p>El mecanismo es la ec. (1) otra vez. Un modo con ruido genera creencias dispersas y,
por la concavidad del logit arriba del punto de indiferencia, la dispersión empuja la
elección hacia el reparto uniforme; un modo sin ruido mantiene su creencia clavada en el
valor correcto. Con el tiempo, lo predecible le gana a lo bueno-pero-incierto.</p>

<p>Para política pública la lectura es directa: <strong>la confiabilidad es un atributo
del modo, no un detalle operativo</strong>. Un metro que mejora su tiempo medio pero
sigue siendo irregular puede perder viajes frente a una alternativa peor en promedio y
predecible.</p>

<h3>6.2 El promedio esconde signos opuestos</h3>

<p>Con el ruido sólo en el metro, el {tex(r"\Phi")} agregado de la ciudad pasa de
{num(cb["phi"]["todos"]["largo"], 2)} sin ruido a
{num(b_tp["phi"]["todos"]["largo"], 2)}: <strong>sube</strong>. Leído solo, ese número
dice que la ciudad elige su modo mejor más seguido que con información perfecta. Debajo
conviven {miles(pm_tp["Metro"]["n"])} personas cuyo modo mejor es el metro, en
{tex(r"\Phi")} = {num(pm_tp["Metro"]["largo"], 2)}, y {miles(pm_tp["Bici"]["n"])} cuyo
modo mejor es la bici, en {num(pm_tp["Bici"]["largo"], 2)}.</p>

<p>Los segundos «mejoran» por una razón que no tiene nada de buena: el ruido degradó a su
competidor, así que eligen más seguido lo que de todos modos les convenía. El promedio
suma esa ganancia espuria con la pérdida real de los primeros y da un número no sólo
tranquilizador sino <strong>de signo equivocado</strong>. Un indicador agregado que
sube mientras un grupo identificable cae a {num(pm_tp["Metro"]["largo"], 2)} no sirve
para evaluar nada.</p>

<p>Esto es la contracara del hallazgo de E3. Allá el agregado escondía rotación
individual con signos que se cancelaban; acá esconde una <strong>redistribución entre
grupos</strong>. En los dos casos la conclusión es la misma: la partición modal y los
promedios de ciudad son las variables que peor informan sobre este fenómeno.</p>

<h3>6.3 La asimetría de E2 no hubo que imponerla</h3>

<p>En E2 «ruido sólo en el mejor» y «ruido sólo en el peor» eran dos condiciones
construidas a mano para aislar el mecanismo. Acá hay una sola condición física —el ruido
está en tal modo— y la población se parte sola: quien tiene ese modo como mejor queda en
el lado malo de la asimetría, quien lo tiene como peor, en el bueno.</p>

<p>Ésa es la razón por la que E4 vale la pena aunque el mecanismo ya se conociera: en una
ciudad, «a quién le toca» no es una condición experimental, es la distribución de
orígenes, destinos y tenencia de auto. Con el ruido en el auto, los
{miles(pm_auto["Auto"]["n"])} agentes cuyo modo mejor es el auto quedan en
{num(pm_auto["Auto"]["largo"], 2)}; los otros, en 1 o por encima.</p>

<h3>6.4 Lo que este informe no muestra</h3>

<ul>
  <li><strong>La bici y la caminata nunca llevan ruido.</strong> Es el supuesto que hace
      visible la sustitución, y también su límite: una ciclovía congestionada o una
      vereda insegura tienen su propia variabilidad, y el experimento no la tiene.</li>
  <li><strong>σ es el mismo para el auto y el metro.</strong> En la realidad no lo es, y
      cuál de los dos es más irregular decide buena parte del resultado.</li>
  <li><strong>σ no está calibrado</strong> y el ruido es i.i.d. y sin truncar, igual que
      en E3.</li>
  <li><strong>Sin inercia ni heterogeneidad de {tex(r"\beta")}.</strong> El CWA de
      Guevara (5,71) agravaría el atrapamiento; no está.</li>
  <li><strong>La caminata no se aprende.</strong> Su tiempo es geométrico y vive entero
      en {tex(r"\bar V")}, así que su cuota se mueve sólo por lo que hacen los demás.</li>
</ul>
"""


# --- 7. Conclusiones ------------------------------------------------------------


def s7() -> str:
    smax = SIGMAS[-1]
    b_tp = f4(BASE, "tp", smax, D_REF)
    b_auto = f4(BASE, "auto", smax, D_REF)
    g_tp = f4(GUEV, "tp", smax, D_REF)
    cb = base0(BASE, D_REF)
    i_bici = MODOS.index("Bici")
    return f"""
<h2 id="conclusiones">7. Conclusiones</h2>

<p>Con los {tex(r"\beta")} del simulador; el punto 5 dice qué cambia si fueran los de la
literatura.</p>

<ol>
  <li><strong>La variabilidad redistribuye viajes hacia el modo que no la tiene.</strong>
      Con {tex(r"\sigma")} = {num(smax, 0)} min la bici gana
      {num(100 * abs(dsplit(BASE, "auto", smax, D_REF)[i_bici]), 2)} pp con el ruido en
      el auto y {num(100 * abs(dsplit(BASE, "tp", smax, D_REF)[i_bici]), 2)} pp con el
      ruido en el metro, sin haber mejorado en nada.</li>
  <li><strong>El daño cae sobre quien tiene el ruido en su modo mejor.</strong> Con el
      ruido en el metro, quienes deberían usarlo quedan en
      {tex(r"\Phi")} = {num(b_tp["phi"]["por_mejor"]["Metro"]["largo"], 2)}; con el ruido
      en el auto, quienes deberían usar el auto quedan en
      {num(b_auto["phi"]["por_mejor"]["Auto"]["largo"], 2)}.</li>
  <li><strong>El promedio agregado miente de signo.</strong> El {tex(r"\Phi")} de toda la
      ciudad con ruido en el metro <em>sube</em> de {num(cb["phi"]["todos"]["largo"], 2)}
      a {num(b_tp["phi"]["todos"]["largo"], 2)} mientras ese grupo se hunde.</li>
  <li><strong>La asimetría de E2 aparece sola.</strong> No hay que construir «ruido en el
      mejor» y «ruido en el peor»: la ciudad las genera según quién es cada persona.</li>
  <li><strong>La calibración mueve el tamaño, no el signo.</strong> Con los
      {tex(r"\beta")} de la literatura el grupo del metro pasa de
      {num(b_tp["phi"]["por_mejor"]["Metro"]["largo"], 2)} a
      {num(g_tp["phi"]["por_mejor"]["Metro"]["largo"], 2)} y la redistribución se
      multiplica — pero ahí la comparación arrastra además el reequilibrio de la §4.4, y
      hay que leerla contra el control de su propia columna.</li>
</ol>

<h3>7.1 Lo que queda</h3>

<ul>
  <li>Ruido en la bici: hoy es un refugio sin variabilidad por construcción, y eso acota
      cuánto se puede concluir sobre el tamaño de la sustitución.</li>
  <li>σ distinto por modo, y calibrado contra variabilidad observada.</li>
  <li>Ruido correlacionado entre días y entre personas, en vez de i.i.d.</li>
  <li>Conseguir y leer Denrell y March (2001) y Erev y Barron (2005); hoy se citan de
      memoria.</li>
</ul>

<h3>7.2 Referencias</h3>
<ul class="refs">
  <li>Guevara, C. A., Tang, Y. y Gao, S. (2018). The initial condition problem with
      complete history dependency in learning models for travel choices.
      <em>Transportation Research Part B</em> 117, 850–861. — Verificado contra
      <code>papers/2018 Guevara Tang Gao TRB.pdf</code>: la tabla 2 es su tabla 4,
      dataset completo.</li>
  <li>Tang, Y. y Gao, S., 2017. An exploratory study of instance-based learning for
      route choice with random travel times. <em>J. Choice Modell.</em> 24, 22–33. —
      Referencia tomada de la bibliografía de Guevara et al. (2018); no revisada
      directamente.</li>
  <li>Ben-Elia, E. y Shiftan, Y., 2010. Which road do I take? A learning-based model of
      route-choice behavior with real-time information. <em>Transport. Res. Part A</em>
      44. — Referencia tomada de la bibliografía de Guevara et al. (2018), no revisada
      directamente.</li>
  <li>Gonzalez, C., Lerch, J. F. y Lebiere, C., 2003. Instance-based learning in dynamic
      decision making. <em>Cogn. Sci.</em> 27, 591–635. — Origen del IBL; referencia
      tomada de la bibliografía de Guevara et al. (2018), no revisada directamente.</li>
  <li>Denrell, J. y March, J. G. (2001), sobre el <em>hot stove effect</em>:
      <strong>citado de memoria, sin verificar contra el texto.</strong></li>
</ul>

<h2 id="reproducir">Reproducir</h2>

<pre><code>cd sandbox/ibl-dia-a-dia
uv sync --extra dev --reinstall-package titirilquen-core   # el núcleo del repo, no uno cacheado
uv run python poblacion.py ciudad                          # → salida/ciudad4.json
uv run python poblacion.py ciudad --guevara                # → salida/ciudad4-guevara.json
uv run python figuras_experimentos.py
uv run python figuras_experimentos.py --guevara
uv run python informe_e4.py
node ../../tools/renderiza_ecuaciones.js</code></pre>
"""


# --- Armado ---------------------------------------------------------------------

SECCIONES = (
    ("preguntas", "Preguntas de investigación"),
    ("experimento", "El experimento"),
    ("modelo", "El modelo"),
    ("escala", "La escala del logit"),
    ("resultados", "Resultados"),
    ("analisis", "Análisis"),
    ("conclusiones", "Conclusiones"),
    ("reproducir", "Reproducir"),
)


def main() -> None:
    cuerpo = "\n".join(f() for f in (s1, s2, s3, s4, s5, s6, s7))
    indice = "\n".join(f'    <li><a href="#{i}">{t}</a></li>' for i, t in SECCIONES)
    html = pagina(
        titulo="E4 · La ciudad de cuatro modos",
        h1="La ciudad de cuatro modos",
        bajada=(
            "Qué pasa cuando la variabilidad está en unos modos y no en otros — a dónde "
            "van los viajes, y quién paga."
        ),
        meta=(
            f"Experimento E4 · {miles(BASE['N'])} agentes · {BASE['dias']} días · "
            f"d = {num(D_REF, 2)} · escalas μ = 1 y μ = {num(K, 3)}"
        ),
        indice=indice,
        cuerpo=cuerpo,
    )
    destino = AQUI / "informe-e4.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  {destino}  ({miles(len(html))} bytes)")


if __name__ == "__main__":
    main()
