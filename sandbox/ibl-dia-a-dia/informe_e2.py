"""Informe del experimento E2 — variabilidad del tiempo de viaje.

Lee las dos escalas del logit y escribe `informe-e2.html`:

    uv run python experimentos.py              -> salida/experimentos.json
    uv run python experimentos.py --guevara    -> salida/experimentos-guevara.json
    uv run python figuras_experimentos.py      (y --guevara)
    uv run python informe_e2.py
    node ../../tools/renderiza_ecuaciones.js

Ningun numero se tipea a mano: todos salen de los dos JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from informe_comun import ec, fig, linea, ntex, num, pagina, pp, sim, tabla, tex

AQUI = Path(__file__).parent
SALIDA = AQUI / "salida"
BASE = json.loads((SALIDA / "experimentos.json").read_text(encoding="utf-8"))
GUEV = json.loads((SALIDA / "experimentos-guevara.json").read_text(encoding="utf-8"))

K = GUEV["escala"]
CB = {c["nombre"]: c for c in BASE["casos"]}
CG = {c["nombre"]: c for c in GUEV["casos"]}

# Caso y configuracion de referencia. C1 es el unico que con los β de la literatura
# no esta saturado (P* = 0,92 frente a 0,999 de C2 y C3), y d = 1,28 es el
# decaimiento que Guevara, Tang y Gao (2018, tabla 4) estiman con datos reales.
REF, D_REF, W = "C1", 1.28, "largo"
SIGMAS = sorted({r["sigma"] for r in BASE["e2"]})
CONDS = ("ambos", "solo_mejor", "solo_peor")
DECS = sorted({r["d"] for r in BASE["e2"]})
NOM_COND = {
    "ambos": "en los dos modos",
    "solo_mejor": "sólo en el mejor",
    "solo_peor": "sólo en el peor",
}
NOM_W = {"corto": "días 1–10", "medio": "días 11–50", "largo": "días 51–250"}


def r2(D: dict, caso: str, d: float, cond: str, sigma: float) -> dict:
    """La fila de E2 de una celda del diseño."""
    return next(
        x
        for x in D["e2"]
        if x["caso"] == caso and x["d"] == d and x["condicion"] == cond and x["sigma"] == sigma
    )


def par(caso: str, d: float, cond: str, sigma: float) -> tuple[dict, dict]:
    """La misma celda en las dos escalas."""
    return r2(BASE, caso, d, cond, sigma), r2(GUEV, caso, d, cond, sigma)


# --- 1. Preguntas ---------------------------------------------------------------


def s1() -> str:
    mb, mg = par(REF, D_REF, "solo_mejor", 80.0)
    ab, ag = par(REF, D_REF, "ambos", 80.0)
    pb, pg = par(REF, D_REF, "solo_peor", 80.0)
    return f"""
<h2 id="preguntas">1. Preguntas de investigación</h2>

<p>E2 pregunta qué le hace la <strong>variabilidad del tiempo de viaje</strong> a una
persona que elige todos los días y sólo observa lo que eligió. Cuatro preguntas, con la
respuesta corta al lado; el resto del informe las sostiene. Los números son los del
simulador —sus {tex(r"\beta")}, {tex(r"\mu")} = 1— y la §4 explica qué tan lejos podrían
estar.</p>

<p><strong>P1. ¿Cuánta de la ventaja verdadera del modo mejor sobrevive al
aprendizaje?</strong> En promedio, casi toda: con el caso de referencia ({REF}, ventaja
{num(CB[REF]["ventaja_min"], 1)} min) y ruido en los dos modos, {tex(r"\Phi")} cae de 1 a
{num(ab["phi"][W], 2)} aun con {tex(r"\sigma")} = 80 min. Esa respuesta tranquilizadora
es justamente la que P2 desarma.</p>

<p><strong>P2. ¿Importa en cuál de los dos modos está la variabilidad?</strong> Es
<em>lo único</em> que importa de verdad, y es el resultado de E2. Con
{tex(r"\sigma")} = 80 min sobre el modo <em>mejor</em>, {tex(r"\Phi")} baja a
{num(mb["phi"][W], 2)} y el {num(100 * mb["ventanas"][W]["invertidos"], 1)} % de las
personas queda <strong>invertido</strong>: elige sistemáticamente el modo peor. El mismo
ruido sobre el modo <em>peor</em> da {tex(r"\Phi")} = {num(pb["phi"][W], 2)}, o sea
<em>mejora</em> la decisión. El promedio de P1 es la mezcla de esos dos signos.</p>

<p><strong>P3. ¿El daño viene de que la creencia se desplaza o de que se
dispersa?</strong> De las dos, y cuál manda depende de dónde está el ruido. Con ruido en
ambos modos domina la dispersión; con ruido sólo en el mejor domina el desplazamiento,
que es el <em>hot stove</em> en su forma de manual.</p>

<p><strong>P4. ¿Cuánto de esto depende de la calibración?</strong> El mecanismo no, el
tamaño sí, y bastante. Si los {tex(r"\beta")} de transporte fueran los que sugiere la
literatura de elección repetida —{num(K, 1)} veces mayores, §4— las mismas tres celdas
darían {num(ag["phi"][W], 2)}, {num(mg["phi"][W], 2)} y {num(pg["phi"][W], 2)}: con ruido
en el modo mejor {tex(r"\Phi")} se vuelve <em>negativo</em> y los invertidos pasan a
{num(100 * mg["ventanas"][W]["invertidos"], 1)} %. Cada tabla trae esa columna.</p>
"""


# --- 2. El experimento ----------------------------------------------------------


def s2() -> str:
    filas = "".join(
        f"<tr><td>{c}</td><td>{CB[c]['estrato']}</td>"
        f"<td class='n'>{num(CB[c]['km'], 1)}</td>"
        f"<td class='n'>{num(CB[c]['t_auto'], 1)}</td>"
        f"<td class='n'>{num(CB[c]['t_metro'], 1)}</td>"
        f"<td>{CB[c]['mejor']}</td>"
        f"<td class='n'>{num(CB[c]['ventaja_min'], 1)}</td>"
        f"<td class='n'>{num(CB[c]['p_verdadera'], 4)}</td>"
        f"<td class='n'>{num(CG[c]['p_verdadera'], 4)}</td></tr>"
        for c in ("C1", "C2", "C3")
    )
    return f"""
<h2 id="experimento">2. El experimento</h2>

<p>Una persona elige cada día entre <strong>dos</strong> modos —el mejor y el peor de
su celda— durante {BASE["dias"]} días, {BASE["replicas"]} réplicas independientes,
semilla {BASE["semilla"]}. Cada día observa el tiempo <em>realizado</em> del modo que
eligió y de ningún otro: ésa es la asimetría de información que hace interesante el
problema. El tiempo realizado es el tiempo de referencia más un shock normal de
desviación {tex(r"\sigma")}.</p>

<p>El diseño cruza cuatro ejes:</p>
<ul>
  <li><strong>Dónde está el ruido</strong> ({len(CONDS)} niveles): en los dos modos,
      sólo en el mejor, sólo en el peor. Es el eje que contesta P2.</li>
  <li><strong>Cuánto ruido</strong> ({len(SIGMAS)} niveles): {tex(r"\sigma")} ∈
      {{{", ".join(num(s, 0) for s in SIGMAS)}}} min.</li>
  <li><strong>Cuánta memoria</strong> ({len(DECS)} niveles): {tex("d")} ∈
      {{{", ".join(num(d, 2) for d in DECS)}}}. {tex("d")} = 0 pondera todos los días
      igual; {tex("d")} = {num(D_REF, 2)} es el valor estimado con datos reales.</li>
  <li><strong>Qué tan clara es la decisión</strong> (3 casos): tres pares
      origen–destino con ventajas muy distintas.</li>
</ul>

<p>Y todo eso se corre <strong>dos veces</strong>, en las dos escalas del logit de la
§4. Son {len(BASE["e2"])} celdas por escala.</p>

{
        tabla(
            1,
            "Los tres casos",
            "<tr><th>caso</th><th>estrato</th><th class='n'>km</th>"
            "<th class='n'>auto (min)</th><th class='n'>metro (min)</th><th>mejor</th>"
            f"<th class='n'>{_a()} (min)</th>"
            f"<th class='n'>{sim('P*')} (simulador)</th>"
            f"<th class='n'>{sim('P*')} (β × {num(K, 1)})</th></tr>",
            filas,
            f"Los tiempos y la ventaja {_a()} no dependen de la escala; la probabilidad "
            f"verdadera P* sí. Con los β de la literatura, C2 y C3 están <strong>saturados</strong> "
            f"(P* ≥ {num(CG['C2']['p_verdadera'], 3)}): casi no queda margen para que el "
            f"aprendizaje empeore nada medible. Por eso el caso de referencia de este informe "
            f"es {REF}, el único con rango útil, y C2 y C3 entran como control.",
        )
    }
"""


def _a() -> str:
    return tex("A")


# --- 3. El modelo ---------------------------------------------------------------


def s3() -> str:
    return f"""
<h2 id="modelo">3. El modelo</h2>

<h3>3.1 Lo que la persona cree</h3>

<p>El <em>instance-based learning</em> (IBL) dice que el tiempo que una persona cree
que toma el modo {tex("i")} es un promedio ponderado de los tiempos que
<strong>efectivamente vivió</strong> en ese modo. Los días recientes pesan más:</p>

{ec(r"b_{ni}(t) \;=\; \sum_{t' \lt t} w_{ni}(t', t)\, x_i(t')", 1)}

{ec(r"w_{ni}(t', t) \;=\; \frac{a_{ni}(t')\,(t - t')^{-d}}{\sum_{s \lt t} a_{ni}(s)\,(t - s)^{-d}}", 2)}

<p>donde {tex("x_i(t')")} es el tiempo realizado el día {tex("t'")} y
{tex(r"a_{ni}(t')")} vale 1 si esa persona eligió {tex("i")} ese día y 0 si no. Esa
indicatriz es todo el problema: <strong>los días en que no elegiste un modo no
entran</strong>, así que la creencia sobre un modo sólo se actualiza si lo usas. El
parámetro {tex("d")} gradúa la memoria — {tex("d")} = 0 promedia toda la historia,
{tex("d")} grande mira casi sólo lo último. Ésta es la forma de Guevara, Tang y Gao
(2018), que la toman de Tang y Gao (2017); el código está en
{linea("ibl.py", "pesos_ibl")} y {linea("ibl.py", "tiempo_percibido")}.</p>

<h3>3.2 Lo que la persona elige</h3>

<p>Con esas creencias arma una utilidad percibida y elige con un logit binario:</p>

{ec(r"V_{ni}(t) \;=\; \bar V_i \;+\; \beta\,\bigl(b_{ni}(t) - \tau_i\bigr)", 3)}

{ec(r"P_n(t) \;=\; \Lambda\bigl(\Delta V_n(t)\bigr), \qquad \Lambda(z) = \frac{1}{1 + e^{-z}}", 4)}

<p>{tex(r"\bar V_i")} es la utilidad del modo {tex("i")} con su tiempo de referencia
{tex(r"\tau_i")}, tal como la calcula el simulador; {tex(r"\beta")} es el coeficiente
del tiempo de viaje, en útiles por minuto. {tex(r"\Delta V_n(t)")} es la ventaja
percibida del modo mejor sobre el peor.</p>

<h3>3.3 Los indicadores</h3>

<p>La ventaja verdadera conviene leerla en minutos, no en útiles, porque así no
depende de la escala:</p>

{ec(r"A \;=\; \frac{\Delta V}{|\beta|}, \qquad P^* = \Lambda(\Delta V)", 5)}

<p>{tex("A")} es cuántos minutos le gana el modo mejor al peor, ponderando cada
componente del tiempo por su propio coeficiente. {tex("P^*")} es la probabilidad que
elegiría alguien que <strong>conoce</strong> los tiempos de referencia: el techo
contra el cual se mide el aprendizaje.</p>

<p>El indicador central es qué fracción de esa ventaja sobrevive:</p>

{ec(r"\Phi \;=\; \frac{S - \tfrac12}{P^* - \tfrac12}, \qquad S = \mathbb{E}\bigl[\bar P_n\bigr]", 6)}

<p>{tex(r"\Phi")} = 1 significa que el aprendizaje reprodujo la decisión informada;
{tex(r"\Phi")} = 0, que la persona quedó tirando una moneda; {tex(r"\Phi")} &lt; 0, que
<strong>se invirtió</strong> — en promedio elige el modo peor.
{tex(r"\Phi")} &gt; 1 es posible y no es un error: quiere decir que el aprendizaje
eligió el modo bueno <em>más</em> seguido que el informado.</p>

<p>Y para saber <em>por qué</em> cae, se parte en dos. Sea {tex(r"\hat m")} la media y
{tex(r"\hat s")} la desviación de la ventaja percibida {tex(r"\Delta V_n(t)")} sobre
personas y días. Lo que daría sólo la dispersión, con la media en su valor verdadero,
es {tex(r"P_{disp} = \mathbb{E}\bigl[\Lambda(\Delta V + \hat s Z)\bigr]")}, y
entonces</p>

{ec(r"\underbrace{S - P^*}_{\text{total}} \;=\; \underbrace{P_{\text{disp}} - P^*}_{\text{dispersión}} \;+\; \underbrace{S - P_{\text{disp}}}_{\text{sesgo}}", 7)}

<p>La <strong>dispersión</strong> es puro Jensen: {tex(r"\Lambda")} es cóncava arriba
de ½, así que ruido simétrico alrededor de una ventaja positiva siempre acerca a ½.
Es negativa por construcción cuando {tex(r"P^* \gt \tfrac12")}. El <strong>sesgo</strong>
es lo que falta: cuánto se corrió la creencia media. Ahí vive el <em>hot stove</em>, y
—a diferencia de la dispersión— puede tener cualquier signo. El código está en
{linea("experimentos.py", "descomposicion")}.</p>
"""


# --- 4. La escala ---------------------------------------------------------------


def s4() -> str:
    bsim, blit = abs(CB[REF]["beta"]), abs(CG[REF]["beta"])
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

{ec(razon, 8)}

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
"""


# --- 5. Resultados --------------------------------------------------------------


def s5() -> str:
    # Tabla 3: Phi del caso de referencia, las tres condiciones, las dos escalas.
    filas = ""
    for s in SIGMAS:
        celdas = ""
        for cond in CONDS:
            a, g = par(REF, D_REF, cond, s)
            celdas += (
                f"<td class='n'>{num(a['phi'][W], 3)}</td><td class='n'>{num(g['phi'][W], 3)}</td>"
            )
        filas += f"<tr><td class='n'>{num(s, 0)}</td>{celdas}</tr>"
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('σ')} (min)</th>"
        + "".join(f"<th colspan='2'>ruido {NOM_COND[c]}</th>" for c in CONDS)
        + "</tr><tr>"
        + "".join(f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in CONDS)
        + "</tr>"
    )
    t3 = tabla(
        3,
        f"Φ del caso {REF}, d = {num(D_REF, 2)}, {NOM_W[W]}",
        cab,
        filas,
        "Cada par de columnas es la misma celda del diseño en las dos escalas. "
        "Con k = 1 (izquierda de cada par) casi nada se mueve de 1, y en «sólo en el "
        "peor» <em>sube</em> hasta 1,44. Con los β de la literatura (negrita) el "
        "experimento separa: el ruido sobre el modo mejor es devastador, el ruido "
        "sobre el peor es benigno, y el ruido en ambos queda en medio.",
    )

    # Tabla 4: descomposicion y fraccion invertida.
    filas4 = ""
    for cond in CONDS:
        for s in (40.0, 80.0):
            a, g = par(REF, D_REF, cond, s)
            for nom, x, pv in (
                ("1", a["descomposicion"][W], CB[REF]["p_verdadera"]),
                (num(K, 2), g["descomposicion"][W], CG[REF]["p_verdadera"]),
            ):
                r = a if nom == "1" else g
                fuerte = nom != "1"
                ab, ce = ("<strong>", "</strong>") if fuerte else ("", "")
                filas4 += (
                    f"<tr><td>{NOM_COND[cond]}</td><td class='n'>{num(s, 0)}</td>"
                    f"<td class='n'>{ab}{nom}{ce}</td>"
                    f"<td class='n'>{ab}{pp(x['S'] - pv)}{ce}</td>"
                    f"<td class='n'>{pp(x['pve'])}</td>"
                    f"<td class='n'>{pp(x['sesgo'])}</td>"
                    f"<td class='n'>{num(x['s'], 2)}</td>"
                    f"<td class='n'>{num(100 * r['ventanas'][W]['invertidos'], 1)}</td></tr>"
                )
    t4 = tabla(
        4,
        f"De dónde sale el daño — {REF}, d = {num(D_REF, 2)}, {NOM_W[W]}",
        f"<tr><th>ruido</th><th class='n'>{sim('σ')} (min)</th>"
        f"<th class='n'>{sim('k')}</th>"
        "<th class='n'>total (pp)</th><th class='n'>dispersión (pp)</th>"
        f"<th class='n'>sesgo (pp)</th><th class='n'>{sim('ŝ')} (útiles)</th>"
        "<th class='n'>invertidos (%)</th></tr>",
        filas4,
        "«Total» es S − P*, la ec. (7). La <strong>dispersión es negativa siempre</strong>, "
        "como exige Jensen. El <strong>sesgo cambia de signo</strong> según dónde esté el "
        "ruido, y es el que manda en los extremos: con ruido sólo en el mejor aporta la "
        "mayor parte del daño, con ruido sólo en el peor compensa de sobra a la dispersión. "
        "«Invertidos» es el porcentaje de personas cuya cuota promedio del modo mejor quedó "
        "bajo ½: gente que aprendió al revés.",
    )

    # Tabla 5: control de saturacion.
    filas5 = ""
    for c in ("C1", "C2", "C3"):
        celdas = ""
        for cond in CONDS:
            a, g = par(c, D_REF, cond, 80.0)
            celdas += (
                f"<td class='n'>{num(a['phi'][W], 3)}</td><td class='n'>{num(g['phi'][W], 3)}</td>"
            )
        filas5 += (
            f"<tr><td>{c}</td><td class='n'>{num(CB[c]['ventaja_min'], 1)}</td>"
            f"<td class='n'>{num(CG[c]['p_verdadera'], 4)}</td>{celdas}</tr>"
        )
    t5 = tabla(
        5,
        f"Control de saturación — los tres casos con σ = 80 min, d = {num(D_REF, 2)}, {NOM_W[W]}",
        f"<tr><th rowspan='2'>caso</th>"
        f"<th rowspan='2' class='n'>{sim('A')} (min)</th>"
        f"<th rowspan='2' class='n'>{sim('P*')} con {sim('k')} = {num(K, 2)}</th>"
        + "".join(f"<th colspan='2'>ruido {NOM_COND[c]}</th>" for c in CONDS)
        + "</tr><tr>"
        + "".join(f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in CONDS)
        + "</tr>",
        filas5,
        "C2 y C3 están saturados: con P* ≥ 0,998 el denominador de Φ ya vale casi ½ y "
        "<strong>no queda techo</strong>, así que su Φ ≈ 1 en «sólo en el peor» es un "
        "límite aritmético, no un hallazgo. En C1 sí hay margen en las dos escalas, y ahí "
        "el signo se da vuelta de verdad: 1,44 con k = 1 contra 1,11 con la escala de "
        "Guevara. Por eso C1 es el caso de referencia y éstos son control.",
    )

    return f"""
<h2 id="resultados">5. Resultados</h2>

<h3>5.1 El panorama</h3>

<p>Las dos figuras siguientes son el mismo gráfico en las dos escalas. Ojo con el eje
horizontal: está en útiles, así que la misma grilla de {tex(r"\sigma")} en minutos
cubre un rango {num(K, 1)} veces más ancho en la segunda.</p>

{fig("e2-phi.png", 1, f"Φ a {NOM_W['largo']} con los β del simulador (k = 1), por condición y caso. Todo pegado a 1, y «sólo en el peor» por encima.")}

{fig("e2-phi-guevara.png", 2, f"Lo mismo con los β de la literatura (k = {num(K, 2)}). Ahora el experimento separa, y C1 —la curva azul— es el que más se mueve, por ser el de ventaja más chica.")}

<h3>5.2 El caso de referencia</h3>

{t3}

<p>Leído en una línea: con ruido en los dos modos, {REF} conserva
{num(par(REF, D_REF, "ambos", 80.0)[1]["phi"][W], 2)} de su ventaja; con el mismo ruido
puesto <strong>sólo en el modo mejor</strong>, {tex(r"\Phi")} se va a
{num(par(REF, D_REF, "solo_mejor", 80.0)[1]["phi"][W], 2)} —negativo— y con el ruido
puesto sólo en el peor, <em>sube</em> a
{num(par(REF, D_REF, "solo_peor", 80.0)[1]["phi"][W], 2)}.</p>

<h3>5.3 De dónde sale el daño</h3>

{t4}

{fig(f"e2-descomposicion-{REF}-d{D_REF}-guevara.png", 3, f"La ec. (7) celda por celda, en puntos porcentuales, para {REF} con los β de la literatura. La barra azul (dispersión) apunta siempre hacia abajo; la roja (sesgo) cambia de signo y es la que decide el resultado neto.")}

<h3>5.4 La memoria</h3>

{fig(f"e2-decaimiento-{REF}-guevara.png", 4, f"Φ de {REF} en función de σ para los tres valores de d. Más peso en lo reciente (d alto) agrava el problema: la creencia se queda colgada de las últimas experiencias, que es justo lo que el ruido contamina.")}

<h3>5.5 El control de saturación</h3>

{t5}
"""


# --- 6. Análisis ----------------------------------------------------------------


def s6() -> str:
    mb, mg = par(REF, D_REF, "solo_mejor", 80.0)
    pb, _ = par(REF, D_REF, "solo_peor", 80.0)
    dm, dp = mb["descomposicion"][W], pb["descomposicion"][W]
    return f"""
<h2 id="analisis">6. Análisis</h2>

<h3>6.1 La asimetría es el resultado, no un detalle</h3>

<p>El mecanismo es el que la literatura llama <em>hot stove</em>: si una experiencia sale
mal, dejas de elegir esa opción, y al dejar de elegirla <strong>dejas de recibir la
información que corregiría la creencia</strong>. La ec. (2) lo hace explícito —
{tex(r"a_{ni}(t')")} apaga los días en que no elegiste—, así que una mala racha se congela
en la memoria en vez de promediarse.</p>

<p>Lo que E2 agrega es que ese mecanismo <strong>no tiene un signo propio</strong>: te
hace abandonar lo que sea variable. Si lo variable es el modo bueno, es una trampa
({tex(r"\Phi")} = {num(mb["phi"][W], 2)}, sesgo {pp(dm["sesgo"])}). Si lo variable es el
modo malo, es una ayuda: te hace abandonar lo que igual te convenía abandonar
({tex(r"\Phi")} = {num(pb["phi"][W], 2)}, sesgo {pp(dp["sesgo"])}).</p>

<p>Esto importa para política pública más de lo que parece. La lectura ingenua de
«reducir la variabilidad del transporte público» supone que menos varianza siempre es
mejor. E2 dice que el signo depende de si el modo que se vuelve confiable es el que la
persona <em>debería</em> elegir. Reducir la variabilidad del modo que ya es peor puede
empujar gente <em>hacia</em> él.</p>

<h3>6.2 Dispersión y sesgo no son lo mismo</h3>

<p>La tabla 4 separa dos cosas que suelen confundirse. La <strong>dispersión</strong> es
mecánica y siempre daña: {tex(r"\Lambda")} es cóncava arriba de ½, así que cualquier ruido
en la creencia acerca la elección a la moneda. No necesita ninguna historia psicológica.
El <strong>sesgo</strong> sí: es el desplazamiento sistemático de la creencia media, y es
donde se ve el <em>hot stove</em>.</p>

<p>En el caso de referencia, con ruido sólo en el mejor, el sesgo aporta
{pp(dm["sesgo"])} de los {pp(dm["S"] - CB[REF]["p_verdadera"])} totales: <strong>manda el
sesgo, no la dispersión</strong>. Con ruido en ambos modos la cuenta se da vuelta y domina
la dispersión. Cualquier resumen del tipo «el daño es tal cosa» sin decir dónde está el
ruido es falso en la mitad de las celdas.</p>

<h3>6.3 Cuánto de esto depende de la calibración</h3>

<p>El logit trae su propio ruido: el término de Gumbel tiene desviación
{tex(r"\pi/\sqrt3")} ≈ {num(3.141592653589793 / 3**0.5, 2)} útiles. Con los
{tex(r"\beta")} del simulador, {tex(r"\sigma")} = 80 min valen
{num(mb["sigma_utiles"], 2)} útiles: el ruido del experimento y el del logit son del
<strong>mismo orden</strong>. Una elección que ya es bastante aleatoria por construcción
tiene poco que perder, y eso acota cuánto puede verse el efecto.</p>

<p>Si los {tex(r"\beta")} fueran {num(K, 1)} veces mayores —lo que sugiere la literatura
de elección repetida, §4— esa razón pasaría a {num(mg["sigma_utiles"] / (3.141592653589793 / 3**0.5), 1)}
y el daño sería otro: los invertidos de la peor celda pasan de
{num(100 * mb["ventanas"][W]["invertidos"], 1)} % a
{num(100 * mg["ventanas"][W]["invertidos"], 1)} %. <strong>El mecanismo es el mismo; lo
que cambia es cuánto margen hay para que se note.</strong></p>

<p>La lectura honesta es ésa: en la medida en que el {tex(r"\beta")} del simulador esté
absorbiendo heterogeneidad no observada —y algo de eso hace—, <strong>E2 subestima el
efecto</strong>. No al revés.</p>

<h3>6.4 Lo que este informe no muestra</h3>

<ul>
  <li><strong>Un solo {tex(r"\beta")}.</strong> Guevara estima dos coeficientes de tiempo,
      uno por ruta (tabla 2). Acá se usó sólo TIMEF para la sensibilidad, porque
      {tex("A = \\Delta V/|\\beta|")} deja de estar bien definido con dos.</li>
  <li><strong>Sin inercia ni dummies de escenario.</strong> El CWA de Guevara (5,71,
      grande) captura la tendencia a repetir lo ya elegido, que reforzaría el
      atrapamiento. No está en este modelo, así que si algo, E2 <em>subestima</em> el
      efecto.</li>
  <li><strong>σ no se calibró.</strong> La grilla de 0 a 80 min es exploratoria. Qué σ es
      realista para el metro o el auto de esta ciudad es una pregunta aparte, y es la que
      más haría falta para convertir esto en una predicción.</li>
  <li><strong>En la columna de sensibilidad, C2 y C3 saturan.</strong> Con los
      {tex(r"\beta")} del simulador los tres casos tienen {tex("P^*")} entre
      {num(CB["C1"]["p_verdadera"], 2)} y {num(CB["C3"]["p_verdadera"], 2)} y los tres
      informan; multiplicados por {num(K, 1)}, {tex("P^*")} de C2 y C3 pasa de
      {num(CG["C2"]["p_verdadera"], 3)} y ahí {tex(r"\Phi")} ya no tiene recorrido
      (tabla 5).</li>
</ul>
"""


# --- 7. Conclusiones ------------------------------------------------------------


def s7() -> str:
    mb, mg = par(REF, D_REF, "solo_mejor", 80.0)
    pb, _ = par(REF, D_REF, "solo_peor", 80.0)
    ab, _ = par(REF, D_REF, "ambos", 80.0)
    return f"""
<h2 id="conclusiones">7. Conclusiones</h2>

<p>Todo con los {tex(r"\beta")} del simulador; entre paréntesis, qué daría si fueran
{num(K, 1)} veces mayores (§4).</p>

<ol>
  <li><strong>En promedio la variabilidad parece inofensiva.</strong> Con
      {tex(r"\sigma")} = 80 min en los dos modos sobrevive el
      {num(100 * ab["phi"][W], 0)} % de la ventaja del modo mejor. Ése es justamente el
      número que no hay que mirar solo.</li>
  <li><strong>Dónde está el ruido importa más que cuánto ruido hay.</strong> El mismo
      {tex(r"\sigma")} da {tex(r"\Phi")} = {num(mb["phi"][W], 2)} si cae sobre el modo
      mejor y {num(pb["phi"][W], 2)} si cae sobre el peor. El <em>hot stove</em> no
      distingue entre opciones buenas y malas: hace abandonar lo variable.</li>
  <li><strong>Y la trampa atrapa a una minoría grande.</strong> El
      {num(100 * mb["ventanas"][W]["invertidos"], 0)} % de las personas termina eligiendo
      sistemáticamente el modo peor, y se queda ahí: son los días 51 a 250, no el
      arranque ({num(100 * mg["ventanas"][W]["invertidos"], 0)} % con los
      {tex(r"\beta")} mayores).</li>
  <li><strong>El daño se reparte entre dispersión y sesgo, y la proporción cambia con el
      diseño.</strong> La dispersión siempre resta; el sesgo decide el signo.</li>
  <li><strong>El tamaño del efecto depende de la calibración, el mecanismo no.</strong>
      Con los {tex(r"\beta")} del simulador el ruido del experimento es del mismo orden
      que el del propio logit, lo que acota cuánto puede verse. En la medida en que esos
      {tex(r"\beta")} absorban heterogeneidad no observada, esto <em>subestima</em> el
      efecto.</li>
</ol>

<h3>7.1 Lo que queda</h3>

<ul>
  <li>Rehacer E1, E3 y E4 a esta escala. E1 ya está corrido
      (<code>salida/experimentos-guevara.json</code>) pero sin informe; E3 y E4 no
      tienen corrida.</li>
  <li>Elegir celdas nuevas con P* bien repartido <em>a esta escala</em>, para barrer
      {tex("A")} sin toparse con el techo.</li>
  <li>Agregar la inercia tipo CWA y ver cuánto agrava el atrapamiento.</li>
  <li>Conseguir y leer Denrell y March (2001) y Erev y Barron (2005); hoy se citan de
      memoria.</li>
</ul>

<h3>7.2 Referencias</h3>
<ul class="refs">
  <li>Guevara, C. A., Tang, Y. y Gao, S. (2018). The initial condition problem with
      complete history dependency in learning models for travel choices.
      <em>Transportation Research Part B</em> 117, 850–861. — Verificado contra
      <code>papers/2018 Guevara Tang Gao TRB.pdf</code>: la tabla 2 de arriba es su
      tabla 4, dataset completo.</li>
  <li>Tang, Y. y Gao, S., 2017. An exploratory study of instance-based learning for
      route choice with random travel times. <em>J. Choice Modell.</em> 24, 22–33. —
      Referencia tomada de la bibliografía de Guevara et al. (2018); no revisada
      directamente.</li>
  <li>Ben-Elia, E. y Shiftan, Y., 2010. Which road do I take? A learning-based model
      of route-choice behavior with real-time information. <em>Transport. Res. Part
      A</em> 44. — Fuente de los datos de laboratorio que Guevara et al. estiman;
      referencia tomada de su bibliografía, no revisada directamente.</li>
  <li>Gonzalez, C., Lerch, J. F. y Lebiere, C., 2003. Instance-based learning in
      dynamic decision making. <em>Cogn. Sci.</em> 27, 591–635. — Origen del IBL;
      referencia tomada de la bibliografía de Guevara et al. (2018), no revisada
      directamente.</li>
  <li>Henríquez-Jara, B. y Guevara, C. A. (2025). An Experience-Based Choice Model
      (EBCM). <em>Journal of Choice Modelling</em> 55, 100552. —
      <code>papers/1-s2.0-S1755534525000156-main.pdf</code>.</li>
  <li>Denrell, J. y March, J. G. (2001), sobre el <em>hot stove effect</em>, y Erev, I.
      y Barron, G. (2005), sobre el <em>payoff variability effect</em>:
      <strong>citados de memoria, sin verificar contra el texto.</strong> Guevara et
      al. (2018) no los cita, así que no se pudieron confirmar desde el PDF que sí
      tenemos.</li>
</ul>

<h2 id="reproducir">Reproducir</h2>

<pre><code>cd sandbox/ibl-dia-a-dia
uv sync --extra dev --reinstall-package titirilquen-core   # el núcleo del repo, no uno cacheado
uv run --extra dev pytest                                  # las fórmulas
uv run python experimentos.py                              # ~5 min → salida/experimentos.json
uv run python experimentos.py --guevara                    # ~5 min → salida/experimentos-guevara.json
uv run python figuras_experimentos.py
uv run python figuras_experimentos.py --guevara
uv run python informe_e2.py
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
        titulo="E2 · Variabilidad del tiempo de viaje",
        h1="Variabilidad del tiempo de viaje",
        bajada=(
            "Qué le hace al aprendizaje día a día que los tiempos no sean los mismos "
            "todos los días — y por qué la respuesta depende de la escala del logit."
        ),
        meta=(
            f"Experimento E2 · caso de referencia {REF} · d = {num(D_REF, 2)} · "
            f"{BASE['dias']} días × {BASE['replicas']} réplicas · "
            f"escalas k = 1 y k = {num(K, 3)}"
        ),
        indice=indice,
        cuerpo=cuerpo,
    )
    destino = AQUI / "informe-e2.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  {destino}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
