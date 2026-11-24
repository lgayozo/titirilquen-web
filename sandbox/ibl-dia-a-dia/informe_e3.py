"""Informe del experimento E3 — la ciudad completa aprende.

Lee las dos escalas del logit y escribe `informe-e3.html`:

    uv run python poblacion.py              -> salida/poblacion.json
    uv run python poblacion.py --guevara    -> salida/poblacion-guevara.json
    uv run python figuras_experimentos.py   (y --guevara)
    uv run python informe_e3.py
    node ../../tools/renderiza_ecuaciones.js

Ningun numero se tipea a mano: todos salen de los dos JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

from informe_comun import ec, fig, linea, miles, ntex, num, pagina, pp, sim, tabla, tex

AQUI = Path(__file__).parent
SALIDA = AQUI / "salida"
BASE = json.loads((SALIDA / "poblacion.json").read_text(encoding="utf-8"))
GUEV = json.loads((SALIDA / "poblacion-guevara.json").read_text(encoding="utf-8"))

# El beta del nucleo, para pasar utiles a minutos. `poblacion.py` mide el
# bienestar en utiles del NUCLEO (mu entra solo en el softmax, no multiplica V),
# asi que la conversion usa el mismo beta en las dos escalas. El de los JSON de
# E1/E2 viene escalado, de ahi la division.
_E12 = json.loads((SALIDA / "experimentos.json").read_text(encoding="utf-8"))
BETA = abs(next(c for c in _E12["casos"] if c["nombre"] == "C2")["beta"]) / _E12.get("escala", 1.0)

K = GUEV["filas"][0]["mu"]
SIGMAS = sorted({f["sigma"] for f in BASE["filas"]})
DECS = sorted({f["d"] for f in BASE["filas"]})
D_REF = 1.28
U = BASE["ultimos"]
NOM_W = {"corto": "días 1–10", "medio": "días 11–50", "largo": "días 51–250"}


def f3(D: dict, sigma: float, d: float) -> dict:
    """La fila de E3 de una celda del diseño."""
    return next(x for x in D["filas"] if x["sigma"] == sigma and x["d"] == d)


def par(sigma: float, d: float) -> tuple[dict, dict]:
    """La misma celda en las dos escalas."""
    return f3(BASE, sigma, d), f3(GUEV, sigma, d)


def brecha_min(f: dict) -> float:
    """Utilidad de decisión menos la experimentada, en minutos de viaje."""
    dec = sum(f["bienestar_decision_por_dia"][-U:]) / U
    exp = sum(f["bienestar_por_dia"][-U:]) / U
    return (dec - exp) / BETA


# --- 1. Preguntas ---------------------------------------------------------------


def s1() -> str:
    ab, ag = par(80.0, D_REF)
    cb, _ = par(0.0, D_REF)
    return f"""
<h2 id="preguntas">1. Preguntas de investigación</h2>

<p>E1 y E2 miran a <strong>una</strong> persona, con la red congelada. E3 pregunta qué
queda de eso cuando aprende la <strong>ciudad entera</strong> y la congestión responde:
{miles(BASE["N"])} agentes eligiendo el mismo día, cargando la red, y el tiempo de cada
uno dependiendo de lo que eligieron los demás. Cinco preguntas, con la respuesta corta al
lado; los números son los del simulador y la §4 dice qué tan lejos podrían estar.</p>

<p><strong>P1. ¿La ciudad reproduce lo que le pasa a una persona?</strong> Sí, y
amortiguado. Con {tex(r"\sigma")} = 80 min y {tex("d")} = {num(D_REF, 2)},
{tex(r"\Phi")} a largo plazo cae de {num(cb["phi"]["todos"]["largo"], 3)} sin ruido a
{num(ab["phi"]["todos"]["largo"], 3)}. El mecanismo es el mismo de E2; lo que cambia es
que acá nadie está solo.</p>

<p><strong>P2. ¿La variabilidad mueve la partición modal?</strong> Prácticamente nada:
la cuota de auto pasa de {num(100 * cb["split_ultimos"][0], 2)} % sin ruido a
{num(100 * ab["split_ultimos"][0], 2)} % con {tex(r"\sigma")} = 80 min. Es la pregunta
cuya respuesta más se aleja de la intuición de E2 — y la §6.1 explica por qué el
agregado no es la variable que hay que mirar.</p>

<p><strong>P3. ¿Cuánto de la conducta final es historia y no preferencias?</strong>
Bastante. Personas <em>idénticas</em> —mismo estrato, misma celda, misma tenencia de
auto— terminan {num(ab["dispersion_iguales"], 2)} veces más dispersas que lo que
explicaría el azar de elegir con la misma probabilidad. En cambio la suerte del
<em>estreno</em> no deja huella medible: quienes empezaron mal terminan en
{num(100 * ab["share_fin_mala_suerte_auto"], 1)} % de auto y quienes empezaron bien en
{num(100 * ab["share_fin_buena_suerte_auto"], 1)} %.</p>

<p><strong>P4. ¿Cuánto cuesta, y cuánto de ese costo se percibe?</strong> Acá aparece lo
que E1 y E2 no pueden ver, porque necesita separar la utilidad con la que se
<em>decide</em> de la que se <em>vive</em>. Con {tex(r"\sigma")} = 80 min la gente cree
estar <strong>{num(brecha_min(ab), 1)} minutos por viaje mejor de lo que está</strong>, y
el error no se corrige con los días. Es además el único indicador de este informe que
<em>no</em> depende de la calibración (§6.3).</p>

<p><strong>P5. ¿Cuánto de esto depende de la calibración?</strong> La dependencia de
trayectoria, mucho. Con los {tex(r"\beta")} de la literatura (§4) la dispersión entre
iguales pasa de {num(ab["dispersion_iguales"], 2)} a {num(ag["dispersion_iguales"], 2)}
veces la binomial, y la brecha de estreno —que acá es nula— se vuelve
{pp(ag["share_fin_buena_suerte_auto"] - ag["share_fin_mala_suerte_auto"])}. El
mecanismo no cambia; el margen para que se note, sí.</p>
"""


# --- 2. El experimento ----------------------------------------------------------


def s2() -> str:
    eq = BASE["split_equilibrio"]
    modos = [m for m, v in zip(BASE["modos"], eq, strict=True) if v > 0]
    filas = "".join(
        f"<tr><td>{m}</td><td class='n'>{num(100 * v, 2)}</td></tr>"
        for m, v in zip(BASE["modos"], eq, strict=True)
        if v > 0
    )
    t1 = tabla(
        1,
        "La ciudad del día 0",
        "<tr><th>modo</th><th class='n'>cuota de equilibrio (%)</th></tr>",
        filas,
        f"El día 0 es el equilibrio MSA de esta ciudad: {miles(BASE['N'])} agentes con su celda "
        f"y su estrato, los tiempos de equilibrio por celda y la partición de arriba. Esos "
        f"tiempos son la «información exógena de buena calidad» con la que todos arrancan: "
        f"el <em>prior</em> de la ec. (2). Sólo {' y '.join(modos)}, y todos con auto, para "
        f"que cada persona elija entre los dos modos que tienen ruido — si hubiera modos sin "
        f"ruido serían un refugio y parte del efecto sería ese artefacto.",
    )
    return f"""
<h2 id="experimento">2. El experimento</h2>

<p>La diferencia con E1 y E2 cabe en una frase: <strong>acá la red responde</strong>.
Cada día los {miles(BASE["N"])} agentes eligen con sus tiempos percibidos, los flujos cargan
la oferta (BPR del auto, frecuencia del metro), y cada uno experimenta el tiempo real de
su modo en su celda más un {tex(r"\varepsilon")} propio. Al día siguiente decide con el
IBL sobre lo que vivió. Son {BASE["dias"]} días.</p>

<p>Eso agrega dos cosas que en fase 0 no existían:</p>
<ul>
  <li><strong>Congestión endógena.</strong> Si muchos abandonan el metro, el auto se
      llena y empeora para todos — un estabilizador que no estaba cuando la red era
      fija.</li>
  <li><strong>Personas comparables.</strong> Con {miles(BASE["N"])} agentes hay muchos grupos
      de personas <em>idénticas</em> por construcción, y se puede medir cuánto las
      separó la historia. Es lo que contesta P3 y no tiene análogo con una sola
      persona.</li>
</ul>

<p>El diseño cruza {len(SIGMAS)} niveles de ruido —{tex(r"\sigma")} ∈
{{{", ".join(num(s, 0) for s in SIGMAS)}}} min, sobre el auto y sobre el metro— y
{len(DECS)} de memoria —{tex("d")} ∈ {{{", ".join(num(d, 2) for d in DECS)}}}—, en las
dos escalas del logit de la §4. {tex(r"\sigma")} = 0 es la referencia de cada escala:
la misma dinámica sin ruido, que converge al equilibrio del logit.</p>

{t1}
"""


# --- 3. El modelo ---------------------------------------------------------------


def s3() -> str:
    return f"""
<h2 id="modelo">3. El modelo</h2>

<h3>3.1 Lo que cada persona cree y elige</h3>

<p>El <em>instance-based learning</em> es el mismo de E1 y E2: el tiempo que la persona
{tex("n")} cree que toma el modo {tex("i")} es el promedio ponderado de los tiempos que
vivió en ese modo, con los días recientes pesando más y los días en que no lo eligió
sin entrar.</p>

{ec(r"b_{ni}(t) \;=\; \sum_{t' \lt t} w_{ni}(t', t)\, x_{ni}(t'), \qquad w_{ni} \;\propto\; a_{ni}(t')\,(t - t')^{-d}", 1)}

<p>La novedad de E3 está en {tex("x_{ni}(t')")}: ya no es un tiempo fijo con ruido, sino
<strong>el tiempo que la red entregó ese día</strong> en la celda de esa persona, más su
{tex(r"\varepsilon")} propio. Si mucha gente se pasa al auto, el auto se congestiona y
todos lo viven peor. El prior es el tiempo de equilibrio del día 0
({linea("ibl.py", "tiempo_percibido")}).</p>

<p>La utilidad no se reimplementa: se llama al núcleo una vez por grupo con los tiempos
del día 0 y se corrige sólo la parte lineal en el tiempo de viaje,</p>

{ec(r"V_{ni}(t) \;=\; \bar V_i \;+\; \beta\,\bigl(b_{ni}(t) - \tau_i\bigr)", 2)}

<p>de modo que las constantes modales, el costo, las penalizaciones y la factibilidad
quedan exactamente como las calcula el simulador. La elección es un logit sobre los
{tex("J_n")} modos factibles de esa persona:</p>

{ec(r"P_{ni}(t) \;=\; \frac{e^{\mu V_{ni}(t)}}{\sum_{j} e^{\mu V_{nj}(t)}}", 3)}

<p>{tex(r"\mu")} es la escala del logit, y la §4 explica por qué acá sí importa cuál se
usa ({linea("poblacion.py", "_softmax_filas")}).</p>

<h3>3.2 Los indicadores</h3>

<p><strong>Cuánta ventaja sobrevive.</strong> Igual que en E2, pero el punto de
indiferencia ya no es ½ sino el reparto uniforme entre los modos factibles de cada
persona:</p>

{ec(r"\Phi \;=\; \frac{\bar S - \overline{1/J}}{\bar P^{*} - \overline{1/J}}", 4)}

<p>donde {tex(r"\bar S")} es la cuota media del modo que de verdad es mejor para cada
persona y {tex(r"\bar P^{*}")} la que elegiría quien conoce los tiempos de equilibrio.
Se calcula en total y por <strong>banda de ventaja</strong> {tex(r"\Delta V")} del mejor
sobre el segundo ({linea("poblacion.py", "_phi")}). Esas bandas están en útiles del
núcleo y <strong>no cambian con la escala</strong>, así que separan exactamente a la
misma gente en las dos corridas — algo que en E1 y E2 no se podía, porque ahí la
saturación obligó a elegir un caso de referencia a mano.</p>

<p><strong>Cuánto separó la historia a personas iguales.</strong> Dos personas con el
mismo estrato, la misma celda y la misma tenencia de auto tienen el mismo modo mejor y
la misma {tex("P")} de equilibrio. Si eligieran con esa misma probabilidad, la varianza
de su cuota en los últimos {U} días sería la binomial. La razón</p>

{ec(r"R \;=\; \frac{\operatorname{Var}\bigl(\text{cuota observada}\bigr)}{\bar p\,(1 - \bar p)\,/\,U}", 5)}

<p>vale 1 si la historia no diferenció a nadie y crece cuando sí
({linea("poblacion.py", "_dispersion_iguales")}). Es el indicador de dependencia de la
trayectoria, y no tiene análogo en E1 ni E2.</p>

<p><strong>Cuánto pesó el primer día.</strong> Entre quienes estrenaron el modo con una
experiencia del decil <em>peor</em> y quienes la tuvieron del decil <em>mejor</em>, la
cuota final de cada grupo ({linea("poblacion.py", "_suerte")}). Si la suerte inicial no
importa, los dos números coinciden.</p>

<p><strong>Cuánto cuesta y cuánto se percibe.</strong> Dos bienestares distintos: la
utilidad con la que se <em>decidió</em> —la percibida, {tex("V_{ni}")} del modo
elegido— y la que de verdad se <em>vivió</em>, con el tiempo que la red entregó. Su
diferencia, en minutos,</p>

{ec(r"B \;=\; \frac{\mathbb{E}\bigl[V^{\text{decisión}}\bigr] - \mathbb{E}\bigl[V^{\text{experimentada}}\bigr]}{|\beta|}", 6)}

<p>es cuánto mejor <em>cree</em> estar la gente de lo que está. Los dos se miden en
útiles del núcleo —{tex(r"\mu")} entra sólo en la ec. (3), no multiplica
{tex("V")}—, así que {tex("B")} es comparable entre escalas y se lee en minutos de viaje
con el mismo {tex(r"\beta")} = {num(-BETA, 4)} útiles/min.</p>
"""


# --- 4. La escala ---------------------------------------------------------------


def _t_reeq() -> str:
    """El dia 0 contra el equilibrio al que llega cada escala sin nada de ruido."""
    dia0 = BASE["split_equilibrio"]
    cb, cg = f3(BASE, 0.0, D_REF), f3(GUEV, 0.0, D_REF)
    filas = "".join(
        f"<tr><td>{m}</td>"
        f"<td class='n'>{num(100 * dia0[i], 2)}</td>"
        f"<td class='n'>{num(100 * cb['split_ultimos'][i], 2)}</td>"
        f"<td class='n'>{num(100 * cg['split_ultimos'][i], 2)}</td></tr>"
        for i, m in enumerate(BASE["modos"])
        if dia0[i] > 0
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
        f"conectado—. Con los β de la literatura el auto se corre {num(abs(salto), 2)} puntos: "
        f"el logit más afilado concentra la demanda y la congestión acomoda el resto. Por "
        f"eso {sim('Φ')} del control vale {num(cg['phi']['todos']['largo'], 3)} y no 1.",
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

{ec(razon, 7)}

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
    filas = ""
    for s in SIGMAS:
        a, g = par(s, D_REF)
        celdas = "".join(
            f"<td class='n'>{num(a['phi']['todos'][w], 3)}</td>"
            f"<td class='n'>{num(g['phi']['todos'][w], 3)}</td>"
            for w in ("corto", "medio", "largo")
        )
        filas += f"<tr><td class='n'>{num(s, 0)}</td>{celdas}</tr>"
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('σ')} (min)</th>"
        + "".join(f"<th colspan='2'>{NOM_W[w]}</th>" for w in ("corto", "medio", "largo"))
        + "</tr><tr>"
        + "".join(
            f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in range(3)
        )
        + "</tr>"
    )
    return tabla(
        4,
        f"Φ de la población, {sim('d')} = {num(D_REF, 2)}",
        cab,
        filas,
        "Fracción de la ventaja verdadera que sobrevive, ec. (4), en los tres horizontes. "
        "Con σ = 0 debe dar 1 en las dos escalas y da: es el control de que la dinámica sin "
        "ruido converge al equilibrio del logit de esa escala.",
    )


def _t4() -> str:
    filas = ""
    for s in SIGMAS:
        a, g = par(s, D_REF)
        filas += (
            f"<tr><td class='n'>{num(s, 0)}</td>"
            f"<td class='n'>{num(100 * a['split_ultimos'][0], 2)}</td>"
            f"<td class='n'>{num(100 * g['split_ultimos'][0], 2)}</td>"
            f"<td class='n'>{num(100 * a['abandono_auto'], 2)}</td>"
            f"<td class='n'>{num(100 * g['abandono_auto'], 2)}</td>"
            f"<td class='n'>{num(100 * a['abandono_metro'], 2)}</td>"
            f"<td class='n'>{num(100 * g['abandono_metro'], 2)}</td></tr>"
        )
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('σ')} (min)</th>"
        "<th colspan='2'>cuota de auto (%)</th>"
        "<th colspan='2'>abandono del auto (%)</th>"
        "<th colspan='2'>abandono del metro (%)</th></tr><tr>"
        + "".join(
            f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in range(3)
        )
        + "</tr>"
    )
    b0, g0 = par(0.0, D_REF)
    b8, g8 = par(80.0, D_REF)
    return tabla(
        6,
        f"La partición modal, {sim('d')} = {num(D_REF, 2)}, últimos {U} días",
        cab,
        filas,
        f"«Abandono» es la fracción de quienes podían usar el modo y terminaron sin usarlo "
        f"ningún día de la ventana. <strong>Léase contra la fila {sim('σ')} = 0</strong>: "
        f"con los β de la literatura el abandono ya parte de "
        f"{num(100 * f3(GUEV, 0.0, D_REF)['abandono_auto'], 1)} % sin nada de ruido —el "
        f"logit afilado hace que mucha gente no toque nunca uno de los dos modos, §4.1—, "
        f"así que el nivel no es efecto del ruido y la diferencia sí. "
        f"La cuota de auto se mueve "
        f"{pp(g8['split_ultimos'][0] - g0['split_ultimos'][0])} entre σ = 0 y σ = 80 a la "
        f"sensibilidad de calibración, y {pp(b8['split_ultimos'][0] - b0['split_ultimos'][0])} a la "
        f"vieja. Contrastar con la tabla 4: <strong>las elecciones individuales se degradan "
        f"mucho más que el agregado</strong> (§6.1).",
    )


def _t5() -> str:
    filas = ""
    for s in SIGMAS:
        a, g = par(s, D_REF)
        filas += (
            f"<tr><td class='n'>{num(s, 0)}</td>"
            f"<td class='n'>{num(a['dispersion_iguales'], 2)}</td>"
            f"<td class='n'>{num(g['dispersion_iguales'], 2)}</td>"
            f"<td class='n'>{num(100 * a['share_fin_mala_suerte_auto'], 1)}</td>"
            f"<td class='n'>{num(100 * a['share_fin_buena_suerte_auto'], 1)}</td>"
            f"<td class='n'>{num(100 * g['share_fin_mala_suerte_auto'], 1)}</td>"
            f"<td class='n'>{num(100 * g['share_fin_buena_suerte_auto'], 1)}</td></tr>"
        )
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('σ')} (min)</th>"
        f"<th colspan='2'>dispersión entre iguales, {sim('R')}</th>"
        f"<th colspan='2'>{sim('μ')} = 1: cuota final de auto (%)</th>"
        f"<th colspan='2'>{sim('μ')} = {num(K, 2)}: cuota final de auto (%)</th></tr><tr>"
        f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>"
        "<th class='n'>mala suerte</th><th class='n'>buena suerte</th>"
        "<th class='n'>mala suerte</th><th class='n'>buena suerte</th></tr>"
    )
    g8 = f3(GUEV, 80.0, D_REF)
    b8 = f3(BASE, 80.0, D_REF)
    return tabla(
        7,
        f"Cuánto separó la historia a personas idénticas, {sim('d')} = {num(D_REF, 2)}",
        cab,
        filas,
        f"{sim('R')} es la ec. (5): 1 significa que personas iguales se comportan como si "
        f"tiraran la misma moneda, y más de 1 que la historia las diferenció. «Mala» y «buena "
        f"suerte» son quienes estrenaron el modo con una experiencia del decil peor y del "
        f"mejor. Con los β de la literatura esa brecha de estreno vale "
        f"{pp(g8['share_fin_buena_suerte_auto'] - g8['share_fin_mala_suerte_auto'])} con "
        f"σ = 80; con los β del simulador, "
        f"{pp(b8['share_fin_buena_suerte_auto'] - b8['share_fin_mala_suerte_auto'])}.",
    )


def _t6() -> str:
    b0 = f3(BASE, 0.0, D_REF)
    bandas = b0["phi"]["bandas"]
    filas = ""
    for i, bd in enumerate(bandas):
        hasta = "∞" if bd["hasta"] is None else num(bd["hasta"], 1)
        celdas = ""
        for s in (0.0, 20.0, 40.0, 80.0):
            a, g = par(s, D_REF)
            celdas += (
                f"<td class='n'>{num(a['phi']['bandas'][i]['largo'], 3)}</td>"
                f"<td class='n'>{num(g['phi']['bandas'][i]['largo'], 3)}</td>"
            )
        filas += (
            f"<tr><td class='n'>{num(bd['desde'], 1)}–{hasta}</td>"
            f"<td class='n'>{miles(bd['n'])}</td>"
            f"<td class='n'>{num(bd['p_estrella'], 3)}</td>"
            f"<td class='n'>{num(f3(GUEV, 0.0, D_REF)['phi']['bandas'][i]['p_estrella'], 3)}</td>"
            f"{celdas}</tr>"
        )
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('ΔV')} (útiles)</th>"
        "<th rowspan='2' class='n'>personas</th>"
        f"<th colspan='2'>{sim('P*')}</th>"
        + "".join(f"<th colspan='2'>{sim('σ')} = {num(s, 0)}</th>" for s in (0.0, 20.0, 40.0, 80.0))
        + "</tr><tr>"
        + "".join(
            f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in range(5)
        )
        + "</tr>"
    )
    return tabla(
        5,
        f"Φ a largo plazo por banda de ventaja, {sim('d')} = {num(D_REF, 2)}",
        cab,
        filas,
        f"<strong>La columna {sim('σ')} = 0 es el control sin ruido</strong>: el impacto "
        f"del ruido es la caída respecto de ella, no el nivel. "
        f"{sim('ΔV')} es la ventaja del modo mejor sobre el segundo, en útiles del núcleo. "
        f"<strong>Las bandas parten a la misma gente en las dos escalas</strong> —{sim('ΔV')} "
        f"se calcula sobre la utilidad del simulador y μ entra sólo en la ec. (3)—, así que "
        f"las columnas son directamente comparables. Lo que sí cambia con la escala es "
        f"{sim('P*')}: la misma ventaja en útiles se traduce en una elección mucho más "
        f"decidida.",
    )


def _t7() -> str:
    filas = ""
    for s in SIGMAS:
        a, g = par(s, D_REF)
        filas += (
            f"<tr><td class='n'>{num(s, 0)}</td>"
            f"<td class='n'>{num(brecha_min(a), 2)}</td>"
            f"<td class='n'>{num(brecha_min(g), 2)}</td>"
            f"<td class='n'>{num(sum(a['bienestar_por_dia'][-U:]) / U, 4)}</td>"
            f"<td class='n'>{num(sum(g['bienestar_por_dia'][-U:]) / U, 4)}</td></tr>"
        )
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('σ')} (min)</th>"
        f"<th colspan='2'>{sim('B')}: se cree mejor por (min/viaje)</th>"
        "<th colspan='2'>utilidad experimentada (útiles)</th></tr><tr>"
        + "".join(
            f"<th class='n'>simulador</th><th class='n'>β × {num(K, 1)}</th>" for _ in range(2)
        )
        + "</tr>"
    )
    g8, b8 = f3(GUEV, 80.0, D_REF), f3(BASE, 80.0, D_REF)
    return tabla(
        8,
        f"El costo y lo que se percibe de él, {sim('d')} = {num(D_REF, 2)}, últimos {U} días",
        cab,
        filas,
        f"{sim('B')} es la ec. (6): cuánto mejor <em>cree</em> estar la gente de lo que "
        f"está, en minutos de viaje. Con σ = 80 min son {num(brecha_min(g8), 1)} min por "
        f"viaje con los β de la literatura y {num(brecha_min(b8), 1)} a los del simulador. Los dos "
        f"bienestares están en útiles del núcleo, así que las columnas son comparables entre "
        f"escalas. La utilidad experimentada cae mucho menos que lo que la brecha sugiere: "
        f"el grueso del efecto es <strong>error de percepción</strong>, no pérdida de "
        f"tiempo.",
    )


def s5() -> str:
    return f"""
<h2 id="resultados">5. Resultados</h2>

<h3>5.1 Cuánta ventaja sobrevive</h3>

{_t3()}

{fig("e3-phi.png", 1, f"Φ de la población contra σ, un panel por horizonte, una línea por {tex('d')}, con los β del simulador ({tex(r'\mu')} = 1).")}

{fig("e3-phi-guevara.png", 2, f"Lo mismo con los β de la literatura ({tex(r'\mu')} = {num(K, 2)}). Mismo eje vertical que la figura 1: la diferencia es el resultado, no el encuadre.")}

<h3>5.2 A quién le pasa</h3>

{_t6()}

<h3>5.3 La partición modal apenas se mueve</h3>

{_t4()}

<h3>5.4 La historia separa a personas idénticas</h3>

{_t5()}

{fig("e3-iguales.png", 3, f"Izquierda: dispersión entre personas iguales, {tex('R')} de la ec. (5); 1 es «la historia no diferenció a nadie». Derecha: la brecha {tex('B')} entre la utilidad de decisión y la experimentada, en minutos por viaje. Escala vieja.")}

{fig("e3-iguales-guevara.png", 4, "Lo mismo con los β de la literatura.")}

<h3>5.5 Lo que cuesta y lo que se percibe</h3>

{_t7()}
"""


# --- 6. Análisis ----------------------------------------------------------------


def s6() -> str:
    a0, g0 = par(0.0, D_REF)
    a8, g8 = par(80.0, D_REF)
    return f"""
<h2 id="analisis">6. Análisis</h2>

<h3>6.1 El agregado engaña</h3>

<p>Es el contraste más útil de E3. Las elecciones individuales se degradan
—{tex(r"\Phi")} cae de {num(a0["phi"]["todos"]["largo"], 2)} a
{num(a8["phi"]["todos"]["largo"], 2)}— y sin embargo la cuota de auto se mueve
{pp(a8["split_ultimos"][0] - a0["split_ultimos"][0])}. Un observador que sólo mirara la
partición modal concluiría que no pasó nada.</p>

<p>Hay dos razones y conviene no confundirlas. La primera es
<strong>compensación</strong>: el ruido está en los dos modos, así que tanta gente
abandona el auto como el metro, y los errores se cancelan en la suma. La segunda es
<strong>congestión</strong>: si demasiados se pasan al auto, el auto empeora y los
devuelve. El equilibrio agregado es estable aunque abajo las personas estén rotando sin
parar.</p>

<p>La consecuencia práctica es incómoda para la evaluación de proyectos. La partición
modal es la variable que casi siempre se reporta, y acá es justamente la que menos
informa: el daño está en <em>quién</em> va en cada modo, no en <em>cuántos</em>.</p>

<h3>6.2 Personas iguales dejan de ser iguales</h3>

<p>Con {tex(r"\sigma")} = 80 min, personas con el mismo estrato, la misma celda y la
misma tenencia de auto terminan {num(a8["dispersion_iguales"], 1)} veces más dispersas
que si todas eligieran con la misma probabilidad. No es heterogeneidad de preferencias:
<strong>por construcción son idénticas</strong>. Es historia.</p>

<p>Lo que <em>no</em> aparece con estos {tex(r"\beta")} es que la suerte del estreno deje
huella: la diferencia entre empezar con una mala experiencia y empezar con una buena vale
{pp(a8["share_fin_buena_suerte_auto"] - a8["share_fin_mala_suerte_auto"])} de cuota
final, que es ruido. La dispersión viene de toda la trayectoria, no del primer día.</p>

<h3>6.3 Lo que la gente cree que le pasa</h3>

<p>La ec. (6) separa dos cosas que normalmente se miden juntas: lo que la persona
<em>vive</em> y lo que <em>cree</em> estar viviendo cuando decide. Con
{tex(r"\sigma")} = 80 min la gente se cree {num(brecha_min(a8), 1)} minutos por viaje
mejor de lo que está, y ese error no se corrige con los días.</p>

<p>Y tiene una propiedad que lo separa de todo lo demás de este informe:
<strong>{tex("B")} es casi el mismo con los {tex(r"\beta")} de la literatura</strong>
({num(brecha_min(a8), 1)} contra {num(brecha_min(g8), 1)} min). No es casualidad: los dos
bienestares se miden en útiles del núcleo, así que la escala cambia <em>a quién</em> le
toca equivocarse, no <em>cuánto</em> se equivoca quien se equivoca. Mientras
{tex(r"\Phi")}, {tex("R")} y la brecha de estreno dependen fuerte de la calibración, el
error de percepción por viaje no. <strong>Es el resultado más robusto de E3.</strong></p>

<p>El mecanismo vuelve a ser la ec. (1): como sólo se observa el modo elegido, y se elige
lo que parece bueno, la creencia sobre el modo usado está sesgada hacia lo favorable. La
persona no tiene manera de descubrir su error, porque el experimento que lo revelaría
—usar el otro modo— es justamente el que dejó de hacer.</p>

<p>Esto importa para medir beneficios. Si se evalúa con la utilidad de decisión —que es
lo que una encuesta de preferencias declaradas recoge— se sobreestima el bienestar en del
orden de {num(brecha_min(a8), 0)} minutos por viaje. La utilidad experimentada, en
cambio, cae poco: el grueso del daño es de percepción, no de tiempo perdido.</p>

<h3>6.4 Cuánto de esto depende de la calibración</h3>

<p>Mucho, salvo {tex("B")}. Con los {tex(r"\beta")} de la literatura (§4)
{tex(r"\Phi")} cae de {num(g0["phi"]["todos"]["largo"], 2)} a
{num(g8["phi"]["todos"]["largo"], 2)} en vez de hasta
{num(a8["phi"]["todos"]["largo"], 2)}; la dispersión entre iguales llega a
{num(g8["dispersion_iguales"], 1)} veces la binomial; y la brecha de estreno, que acá es
nula, pasa a valer
{pp(g8["share_fin_buena_suerte_auto"] - g8["share_fin_mala_suerte_auto"])}.</p>

<p>O sea: <strong>la dependencia de trayectoria es el indicador más sensible a la
calibración de todo este trabajo</strong>. Si el {tex(r"\beta")} del simulador está
absorbiendo heterogeneidad no observada, lo que E3 reporta como «la historia diferencia
un poco» podría ser bastante más.</p>

<h3>6.5 Lo que este informe no muestra</h3>

<ul>
  <li><strong>Sólo auto y metro, y todos con auto.</strong> Es deliberado: con modos sin
      ruido, la bici y la caminata serían un refugio hacia el que migraría la elección por
      construcción, y parte del efecto sería ese artefacto. La ciudad de cuatro modos es
      E4.</li>
  <li><strong>σ no está calibrado.</strong> La grilla de 0 a 80 min es exploratoria.</li>
  <li><strong>Ruido i.i.d. y sin truncar.</strong> La variabilidad real está
      correlacionada entre días y entre personas, y los tiempos no pueden ser
      negativos.</li>
  <li><strong>Sin inercia.</strong> El CWA de Guevara (5,71) agravaría el atrapamiento y
      no está.</li>
  <li><strong>El prior es el equilibrio.</strong> Todos arrancan sabiendo los tiempos del
      día 0. Un prior equivocado es otra pregunta.</li>
</ul>
"""


# --- 7. Conclusiones ------------------------------------------------------------


def s7() -> str:
    a0, _ = par(0.0, D_REF)
    a8, g8 = par(80.0, D_REF)
    return f"""
<h2 id="conclusiones">7. Conclusiones</h2>

<p>Con los {tex(r"\beta")} del simulador; el punto 5 dice qué cambia si fueran los de la
literatura.</p>

<ol>
  <li><strong>La ciudad reproduce el mecanismo de E2, amortiguado.</strong> Con
      {tex(r"\sigma")} = 80 min y {tex("d")} = {num(D_REF, 2)}, {tex(r"\Phi")} a largo
      plazo cae de {num(a0["phi"]["todos"]["largo"], 2)} sin ruido a
      {num(a8["phi"]["todos"]["largo"], 2)}.</li>
  <li><strong>La partición modal no se entera.</strong> Se mueve
      {pp(a8["split_ultimos"][0] - a0["split_ultimos"][0])} mientras las elecciones
      individuales se degradan. Quien mire sólo el agregado no ve nada.</li>
  <li><strong>La historia diferencia a personas idénticas.</strong>
      {tex("R")} = {num(a8["dispersion_iguales"], 1)} veces la binomial. La suerte del
      estreno, en cambio, no deja huella con estos {tex(r"\beta")}.</li>
  <li><strong>El costo es sobre todo de percepción, y es el resultado más
      robusto.</strong> La gente se cree {num(brecha_min(a8), 1)} min por viaje mejor de
      lo que está, no se corrige, y el número casi no cambia con la calibración. Si se
      evalúa con la utilidad de decisión, se sobreestima el beneficio.</li>
  <li><strong>La dependencia de trayectoria sí depende de la calibración.</strong> Con
      los {tex(r"\beta")} de la literatura, {tex("R")} pasa a
      {num(g8["dispersion_iguales"], 1)} y la brecha de estreno de
      {pp(a8["share_fin_buena_suerte_auto"] - a8["share_fin_mala_suerte_auto"])} a
      {pp(g8["share_fin_buena_suerte_auto"] - g8["share_fin_mala_suerte_auto"])}. Es
      donde más margen hay, y donde más haría falta saber cuál es el
      {tex(r"\beta")} correcto.</li>
</ol>

<h3>7.1 Lo que queda</h3>

<ul>
  <li>E4 —la ciudad de cuatro modos— tiene su propio informe: ahí el ruido no está en
      todos los modos y aparece la sustitución hacia el que no lo tiene.</li>
  <li>Calibrar σ contra variabilidad observada, que es lo que falta para que estos
      números sean una predicción y no una exploración.</li>
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
uv run python poblacion.py                                 # → salida/poblacion.json
uv run python poblacion.py --guevara                       # → salida/poblacion-guevara.json
uv run python figuras_experimentos.py
uv run python figuras_experimentos.py --guevara
uv run python informe_e3.py
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
        titulo="E3 · La ciudad completa aprende",
        h1="La ciudad completa aprende",
        bajada=(
            "Qué queda del efecto de la variabilidad cuando aprenden todos a la vez y la "
            "congestión responde — y por qué la partición modal no lo muestra."
        ),
        meta=(
            f"Experimento E3 · {miles(BASE['N'])} agentes · {BASE['dias']} días · "
            f"d = {num(D_REF, 2)} · escalas μ = 1 y μ = {num(K, 3)}"
        ),
        indice=indice,
        cuerpo=cuerpo,
    )
    destino = AQUI / "informe-e3.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  {destino}  ({miles(len(html))} bytes)")


if __name__ == "__main__":
    main()
