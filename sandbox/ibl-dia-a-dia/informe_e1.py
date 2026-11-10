"""Informe del experimento E1 — experiencias malas tempranas.

Lee las dos escalas del logit y escribe `informe-e1.html`:

    uv run python experimentos.py              -> salida/experimentos.json
    uv run python experimentos.py --guevara    -> salida/experimentos-guevara.json
    uv run python figuras_experimentos.py      (y --guevara)
    uv run python informe_e1.py
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

# Mismo caso y configuracion de referencia que el informe de E2: C1 es el unico
# sin saturar a la escala de Guevara, y d = 1,28 es el decaimiento que Guevara,
# Tang y Gao (2018, tabla 4) estiman con datos reales.
REF, D_REF = "C1", 1.28
KS = sorted({r["k"] for r in BASE["e1"] if r.get("k")})
RS = sorted({r["r"] for r in BASE["e1"] if r.get("k")})
DECS = sorted({r["d"] for r in BASE["e1"]})
NOM_W = {"corto": "días 1–10", "medio": "días 11–50", "largo": "días 51–250"}


def r1(D: dict, caso: str, d: float, k: int, r: float) -> dict:
    """La fila de E1 de una celda del diseño."""
    return next(
        x
        for x in D["e1"]
        if x["caso"] == caso and x["d"] == d and x.get("k") == k and x.get("r") == r
    )


def par(caso: str, d: float, k: int, r: float) -> tuple[dict, dict]:
    """La misma celda en las dos escalas."""
    return r1(BASE, caso, d, k, r), r1(GUEV, caso, d, k, r)


def vm(x: dict) -> str:
    """Vida media, con «—» cuando no recupera la mitad dentro del horizonte."""
    v = x["vida_media"]
    return "—" if v is None else num(v, 0)


# --- 1. Preguntas ---------------------------------------------------------------


def s1() -> str:
    dc = CB[REF]["delta_critico"][str(D_REF)]
    peor_base = min(x["efecto"]["largo"] for x in BASE["e1"] if x.get("k") and x["caso"] == REF)
    peor_guev = min(x["efecto"]["largo"] for x in GUEV["e1"] if x.get("k") and x["caso"] == REF)
    _, g = par(REF, D_REF, 5, 6.0)
    return f"""
<h2 id="preguntas">1. Preguntas de investigación</h2>

<p>E1 pregunta qué le hace a una persona una <strong>mala racha temprana</strong>: unas
pocas experiencias muy malas en el modo que le conviene, justo al principio, cuando
todavía no tiene historia que las promedie. Cuatro preguntas, con la respuesta corta al
lado.</p>

<p><strong>P1. ¿Qué tan mala, o cuántas veces, tiene que ser la experiencia para
cambiar la conducta?</strong> Hay un umbral exacto y se puede escribir: el shock
crítico {tex(r"\Delta^*")} que deja la ventaja percibida en cero. Para el caso de
referencia ({REF}) va de {num(dc[str(max(KS))], 1)} a {num(dc[str(min(KS))], 1)}
minutos según cuántas veces ocurra. Y es <strong>el mismo en las dos escalas</strong>:
el umbral es una propiedad de la memoria, no del logit.</p>

<p><strong>P2. ¿El efecto se borra o se queda?</strong> Depende de si cruza una
segunda frontera, y ahí las dos escalas no se parecen en nada. Con la escala vieja
<em>todo</em> se recupera: el peor efecto de largo plazo de las {len(KS) * len(RS) * len(DECS)}
combinaciones es {pp(peor_base)}. A la escala de Guevara hay una región donde <strong>no se recupera
nunca</strong>: el peor llega a {pp(peor_guev)} y la persona sigue ahí el día 250.</p>

<p><strong>P3. ¿La fórmula predice lo que hace la simulación?</strong> Sí, y es la
verificación que sostiene todo lo demás: la probabilidad analítica justo después del
{tex("k")}-ésimo shock reproduce la simulada en las dos escalas (§5.4).</p>

<p><strong>P4. ¿Cambia la escala la respuesta?</strong> No cambia el umbral, cambia la
<em>consecuencia</em> de cruzarlo — y eso basta para que aparezca un fenómeno que con
{tex(r"\mu")} = 1 no existía. Con {tex("k")} = 5 y
{tex(r"\Delta")} = 6{tex("A")}, la cuota del modo mejor queda en
{num(100 * (CG[REF]["p_verdadera"] + g["efecto"]["largo"]), 1)} % y no se mueve más.</p>
"""


# --- 2. El experimento ----------------------------------------------------------


def s2() -> str:
    filas = "".join(
        f"<tr><td>{c}</td><td>{CB[c]['estrato']}</td>"
        f"<td class='n'>{num(CB[c]['km'], 1)}</td>"
        f"<td>{CB[c]['mejor']}</td>"
        f"<td class='n'>{num(CB[c]['ventaja_min'], 1)}</td>"
        f"<td class='n'>{num(CB[c]['p_verdadera'], 4)}</td>"
        f"<td class='n'>{num(CG[c]['p_verdadera'], 4)}</td></tr>"
        for c in ("C1", "C2", "C3")
    )
    t1 = tabla(
        1,
        "Los tres casos",
        f"<tr><th>caso</th><th>estrato</th><th class='n'>km</th><th>mejor</th>"
        f"<th class='n'>{sim('A')} (min)</th>"
        f"<th class='n'>{sim('P*')} con {sim('k')} = 1</th>"
        f"<th class='n'>{sim('P*')} con {sim('k')} = {num(K, 2)}</th></tr>",
        filas,
        f"La ventaja {sim('A')} no depende de la escala; la probabilidad verdadera "
        f"{sim('P*')} sí. El caso de referencia es {REF}, el mismo del informe de E2. "
        f"Ojo: el tamaño del shock se define como {sim('Δ')} = {sim('r')}·{sim('A')}, "
        f"así que un caso con más ventaja recibe un shock absoluto más grande — por eso "
        f"acá el patrón entre casos es el <em>contrario</em> al de E2 (§5.6).",
    )
    return f"""
<h2 id="experimento">2. El experimento</h2>

<p>Una persona elige cada día entre <strong>dos</strong> modos —el mejor y el peor de
su celda— durante {BASE["dias"]} días, {BASE["replicas"]} réplicas independientes,
semilla {BASE["semilla"]}. Sin variabilidad: los tiempos son los de referencia, salvo
por el tratamiento. <strong>Las primeras {tex("k")} veces que elige el modo mejor</strong>,
su experiencia sale {tex(r"\Delta")} minutos peor de lo que realmente es. Después, todo
vuelve a la normalidad.</p>

<p>Esa definición tiene una consecuencia que importa: los shocks se entregan
<em>cuando la persona elige el modo</em>, no en días fijos. Si abandona antes de
acumular las {tex("k")} experiencias, nunca las recibe. Volvemos a esto en §5.5, porque
deja de ser un detalle de implementación y pasa a ser parte del resultado.</p>

<p>El diseño cruza cuatro ejes:</p>
<ul>
  <li><strong>Cuántas experiencias malas</strong> ({len(KS)} niveles): {tex("k")} ∈
      {{{", ".join(str(k) for k in KS)}}}.</li>
  <li><strong>Qué tan malas</strong> ({len(RS)} niveles): {tex("r = \\Delta/A")} ∈
      {{{", ".join(num(r, 1) for r in RS)}}}, es decir el shock medido en múltiplos de
      la propia ventaja del caso.</li>
  <li><strong>Cuánta memoria</strong> ({len(DECS)} niveles): {tex("d")} ∈
      {{{", ".join(num(d, 2) for d in DECS)}}}. {tex("d")} = 0 pondera todos los días
      igual; {tex("d")} = {num(D_REF, 2)} es el valor estimado con datos reales.</li>
  <li><strong>Qué tan clara es la decisión</strong> (3 casos).</li>
</ul>

<p>Cada combinación se compara contra un <strong>control</strong> sin shocks, idéntico
en todo lo demás. Y todo se corre <strong>dos veces</strong>, en las dos escalas del
logit de la §4.</p>

{t1}
"""


# --- 3. El modelo ---------------------------------------------------------------


def s3() -> str:
    return f"""
<h2 id="modelo">3. El modelo</h2>

<h3>3.1 Lo que la persona cree</h3>

<p>El <em>instance-based learning</em> (IBL) dice que el tiempo que una persona cree
que toma el modo {tex("i")} es un promedio ponderado de los tiempos que
<strong>efectivamente vivió</strong> en ese modo, con los días recientes pesando
más:</p>

{ec(r"b_{ni}(t) \;=\; \sum_{t' \lt t} w_{ni}(t', t)\, x_i(t')", 1)}

{ec(r"w_{ni}(t', t) \;=\; \frac{a_{ni}(t')\,(t - t')^{-d}}{\sum_{s \lt t} a_{ni}(s)\,(t - s)^{-d}}", 2)}

<p>{tex(r"a_{ni}(t')")} vale 1 si esa persona eligió {tex("i")} el día {tex("t'")} y 0
si no. Esa indicatriz es todo el problema de E1: <strong>los días en que no elegiste un
modo no entran en la creencia sobre ese modo</strong>, así que una mala racha no se
promedia si dejas de usarlo. El código está en {linea("ibl.py", "pesos_ibl")} y
{linea("ibl.py", "tiempo_percibido")}.</p>

<p>La persona arranca con un <em>prior</em>: una instancia en {tex("t' = 0")} con el
tiempo de referencia {tex(r"\tau_i")}. Sabe cuánto tardan los modos, pero esa creencia
inicial pesa como una sola experiencia y es lo que las malas rachas van a desplazar.</p>

<h3>3.2 Lo que la persona elige</h3>

{ec(r"V_{ni}(t) \;=\; \bar V_i \;+\; \beta\,\bigl(b_{ni}(t) - \tau_i\bigr)", 3)}

{ec(r"P_n(t) \;=\; \Lambda\bigl(\Delta V_n(t)\bigr), \qquad \Lambda(z) = \frac{1}{1 + e^{-z}}", 4)}

{ec(r"A \;=\; \frac{\Delta V}{|\beta|}, \qquad P^* = \Lambda(\Delta V)", 5)}

<p>{tex("A")} es la ventaja verdadera del modo mejor en minutos, y {tex("P^*")} la
probabilidad de alguien que <strong>conoce</strong> los tiempos: el control contra el
cual se mide el daño.</p>

<h3>3.3 El umbral</h3>

<p>Si la persona usa el modo mejor los días 1…{tex("k")} y recibe el shock cada vez,
al decidir el día {tex("k+1")} esas {tex("k")} experiencias tienen antigüedad 1…{tex("k")}
y el prior tiene antigüedad {tex("k+1")}. El peso conjunto de la mala racha frente al
prior es</p>

{ec(r"W_k \;=\; \frac{\sum_{j=1}^{k} j^{-d}}{\sum_{j=1}^{k} j^{-d} + (k+1)^{-d}}", 6)}

<p>que con {tex("d = 0")} da {tex("k/(k+1)")} sin importar cuándo ocurrieron. La
ventaja percibida queda entonces {tex(r"\Delta V - |\beta|\,W_k\,\Delta")}, y el shock
que la deja exactamente en cero es</p>

{ec(r"\Delta^* \;=\; \frac{A}{W_k}", 7)}

<p>Éste es el número que contesta P1. Nótese que {tex(r"\Delta^*")} está escrito sólo
con {tex("A")} —minutos— y {tex("W_k")} —memoria—: <strong>no aparece la escala del
logit</strong>. La probabilidad justo después del {tex("k")}-ésimo shock sí la
lleva:</p>

{ec(r"P_{\text{post}} \;=\; \Lambda\bigl(\Delta V - |\beta|\,W_k\,\Delta\bigr)", 8)}

<p>Multiplicar toda la utilidad por {tex("k_e")} (la reescala de la §4) multiplica
{tex(r"\Delta V")} y {tex(r"|\beta|")} por igual, así que el argumento del logit se
multiplica por {tex("k_e")}: el <strong>cruce por ½ no se mueve</strong> —es
{tex(r"\Delta = \Delta^*")}— pero la curva se vuelve mucho más abrupta. El código está
en {linea("experimentos.py", "peso_shocks")}, {linea("experimentos.py", "delta_critico")}
y {linea("experimentos.py", "p_post_analitica")}.</p>

<h3>3.4 Los indicadores del daño</h3>

<p>El efecto en una ventana de días es la diferencia de cuota contra el control:</p>

{ec(r"E \;=\; S_{\text{shock}} - S_{\text{control}}", 9)}

<p>y la <strong>vida media</strong> es cuántos días pasan desde el punto más bajo hasta
recuperar la mitad de la brecha ({linea("experimentos.py", "vida_media")}). Si no se
recupera dentro de los {BASE["dias"]} días, se anota «—», y eso es el resultado, no un
dato faltante.</p>
"""


# --- 4. La escala ---------------------------------------------------------------


def s4() -> str:
    bb, bg = abs(CB[REF]["beta"]), abs(CG[REF]["beta"])
    k_tex = r"k_e \;=\; \frac{" + ntex(bg, 3) + "}{" + ntex(bb, 4) + r"} \;=\; " + ntex(K, 3)
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
        "TIMEF y TIMES son los coeficientes del tiempo percibido de la ruta rápida y la "
        "lenta: no son un rango, son dos coeficientes específicos de alternativa dentro "
        "de un mismo modelo (su ec. 15). Tomamos TIMEF = −0,198. De acá sale también el "
        "d = 1,28 que usamos como decaimiento de referencia.",
    )
    return f"""
<h2 id="escala">4. La escala del logit</h2>

<p>El simulador venía con {tex(r"\beta")} = {num(-bb, 4)} útiles/min y
{tex(r"\mu")} = 1, un número que viene de la calibración del modelo de ciudad, no de
elecciones repetidas de una misma persona. Guevara, Tang y Gao (2018) estiman un IBL
con los datos de laboratorio de ruta de Ben-Elia y Shiftan (2010) —que es casi
exactamente el experimento que E1 simula— y obtienen:</p>

{t2}

<p>Adoptar ese {tex(r"\beta")} <strong>no</strong> es cambiar
{tex(r"\beta_t")} y dejar el resto: eso multiplicaría el valor del tiempo por
{num(K, 2)} y descalibraría las constantes modales — sería otro modelo. Lo correcto es
multiplicar <em>toda</em> la utilidad por</p>

{ec(k_tex, 10)}

<p>que es formalmente idéntico a fijar {tex(r"\mu = k_e")} dejando los coeficientes como
estaban. Preserva el valor del tiempo, los <em>trade-offs</em> y las constantes; lo
único que cambia es cuán determinista es la elección. Se puede verificar: {tex("A")},
{tex("W_k")} y {tex(r"\Delta^*")} quedan idénticos hasta el último decimal (§5.2).</p>

<p>Para E1 la consecuencia es precisa. El umbral {tex(r"\Delta^*")} no se mueve, pero
{tex("P_{\\text{post}}")} de la ec. (8) pasa a ser {tex(r"\Lambda(k_e z)")} donde antes
era {tex(r"\Lambda(z)")}. <strong>La misma pregunta, una respuesta mucho más
abrupta</strong>: apenas pasado el umbral, la probabilidad de volver a usar el modo se
desploma, y de eso depende si la persona recupera o no.</p>
"""


# --- 5. Resultados --------------------------------------------------------------


def _t3() -> str:
    """W_k y Delta* por k y d. Identicos en las dos escalas."""
    filas = ""
    for k in KS:
        celdas = ""
        for d in DECS:
            w = CB[REF]["w_k"][str(d)][str(k)]
            dc = CB[REF]["delta_critico"][str(d)][str(k)]
            celdas += f"<td class='n'>{num(w, 4)}</td><td class='n'>{num(dc, 1)}</td>"
        filas += f"<tr><td class='n'>{k}</td>{celdas}</tr>"
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('k')}</th>"
        + "".join(f"<th colspan='2'>{sim('d')} = {num(d, 2)}</th>" for d in DECS)
        + "</tr><tr>"
        + "".join(
            f"<th class='n'>{sim('W_k')}</th><th class='n'>{sim('Δ*')} (min)</th>" for _ in DECS
        )
        + "</tr>"
    )
    iguales = all(
        CB[REF]["delta_critico"][str(d)][str(k)] == CG[REF]["delta_critico"][str(d)][str(k)]
        for d in DECS
        for k in KS
    )
    return tabla(
        3,
        f"El umbral crítico — caso {REF}",
        cab,
        filas,
        f"{sim('W_k')} es el peso de la mala racha frente al prior, ec. (6); "
        f"{sim('Δ*')} = {sim('A')}/{sim('W_k')} el shock que deja la ventaja percibida "
        f"en cero, ec. (7). Más experiencias malas bajan el umbral, pero con rendimientos "
        f"decrecientes: de {num(CB[REF]['delta_critico'][str(D_REF)][str(min(KS))], 1)} a "
        f"{num(CB[REF]['delta_critico'][str(D_REF)][str(max(KS))], 1)} min al pasar de "
        f"{min(KS)} a {max(KS)}. Más memoria de lo reciente ({sim('d')} alto) también lo "
        f"baja. <strong>Estos números son idénticos en las dos escalas</strong> "
        f"({'verificado celda a celda' if iguales else 'OJO: difieren'}): el umbral es una "
        f"propiedad de la memoria, no del logit.",
    )


def _t4() -> str:
    """Respuesta alrededor del umbral, caso y d de referencia, k intermedio."""
    kk = 3
    filas = ""
    for r in RS:
        a, g = par(REF, D_REF, kk, r)
        filas += (
            f"<tr><td class='n'>{num(r, 1)}</td><td class='n'>{num(a['delta_min'], 1)}</td>"
            f"<td class='n'>{num(a['p_post_analitica'], 3)}</td>"
            f"<td class='n'><strong>{num(g['p_post_analitica'], 3)}</strong></td>"
            f"<td class='n'>{pp(a['efecto']['corto'])}</td>"
            f"<td class='n'><strong>{pp(g['efecto']['corto'])}</strong></td>"
            f"<td class='n'>{pp(a['efecto']['largo'])}</td>"
            f"<td class='n'><strong>{pp(g['efecto']['largo'])}</strong></td>"
            f"<td class='n'>{vm(a)}</td><td class='n'><strong>{vm(g)}</strong></td></tr>"
        )
    dc = CB[REF]["delta_critico"][str(D_REF)][str(kk)]
    cab = (
        f"<tr><th rowspan='2' class='n'>{sim('r')}</th>"
        f"<th rowspan='2' class='n'>{sim('Δ')} (min)</th>"
        f"<th colspan='2'>{sim('P')} tras el shock</th>"
        "<th colspan='2'>efecto corto plazo (pp)</th>"
        "<th colspan='2'>efecto largo plazo (pp)</th>"
        "<th colspan='2'>vida media (días)</th></tr><tr>"
        + "".join(
            f"<th class='n'>{sim('k_e')} = 1</th><th class='n'>{sim('k_e')} = {num(K, 2)}</th>"
            for _ in range(4)
        )
        + "</tr>"
    )
    return tabla(
        4,
        f"Alrededor del umbral — {REF}, {sim('k')} = {kk}, {sim('d')} = {num(D_REF, 2)}",
        cab,
        filas,
        f"El umbral de este caso es {sim('Δ*')} = {num(dc, 1)} min, entre "
        f"{sim('r')} = 1,0 y 1,5. Con la escala vieja cruzarlo casi no se nota: el efecto "
        f"de largo plazo nunca pasa de {pp(min(a['efecto']['largo'] for a in [r1(BASE, REF, D_REF, kk, x) for x in RS]))} "
        f"y todo se recupera en días. A la escala de Guevara (negrita) la misma fila cambia "
        f"de naturaleza: a partir de {sim('r')} = 3 el efecto se queda, y desde "
        f"{sim('r')} = 4 ya no hay recuperación dentro del horizonte («—»).",
    )


def _t5() -> str:
    """Mapa de largo plazo a la escala de Guevara."""
    filas = ""
    for k in KS:
        celdas = "".join(
            f"<td class='n'>{pp(r1(GUEV, REF, D_REF, k, r)['efecto']['largo'])}</td>" for r in RS
        )
        filas += f"<tr><td class='n'>{k}</td>{celdas}</tr>"
    peor_base_d = min(r1(BASE, REF, D_REF, k, r)["efecto"]["largo"] for k in KS for r in RS)
    return tabla(
        5,
        f"Mapa de la trampa — efecto de largo plazo (pp), {REF}, "
        f"{sim('d')} = {num(D_REF, 2)}, escala de Guevara",
        f"<tr><th class='n'>{sim('k')} \\ {sim('r')}</th>"
        + "".join(f"<th class='n'>{num(r, 1)}</th>" for r in RS)
        + "</tr>",
        filas,
        f"Días 51–250 contra el control. Hay una frontera nítida: arriba y a la derecha "
        f"de ella el daño es permanente y se estabiliza cerca de "
        f"{pp(min(r1(GUEV, REF, D_REF, k, r)['efecto']['largo'] for k in KS for r in RS))}, "
        f"que es el abandono casi total del modo mejor. Abajo y a la izquierda, la "
        f"recuperación es completa. <strong>La misma tabla con la escala vieja no tiene "
        f"ninguna celda bajo {pp(peor_base_d)}</strong>: ahí el daño permanente, "
        f"sencillamente, no existe.",
    )


def _t6() -> str:
    """Validacion: analitica vs simulada."""
    filas = ""
    muestra = [(1, 1.0), (1, 3.0), (3, 1.0), (3, 3.0), (10, 1.0)]
    for k, r in muestra:
        a, g = par(REF, D_REF, k, r)
        filas += (
            f"<tr><td class='n'>{k}</td><td class='n'>{num(r, 1)}</td>"
            f"<td class='n'>{num(a['p_post_analitica'], 4)}</td>"
            f"<td class='n'>{num(a['p_post_sim'], 4)}</td>"
            f"<td class='n'>{num(g['p_post_analitica'], 4)}</td>"
            f"<td class='n'>{num(g['p_post_sim'], 4)}</td></tr>"
        )
    # Desviacion maxima sobre todas las celdas donde hay muestra suficiente.
    peor = 0.0
    for D in (BASE, GUEV):
        for x in D["e1"]:
            if x.get("k") and x["llegan_a_k"] >= 0.5:
                peor = max(peor, abs(x["p_post_analitica"] - x["p_post_sim"]))
    return tabla(
        6,
        f"Verificación de la ec. (8) — {REF}, {sim('d')} = {num(D_REF, 2)}",
        f"<tr><th class='n'>{sim('k')}</th><th class='n'>{sim('r')}</th>"
        f"<th colspan='2'>{sim('k_e')} = 1</th>"
        f"<th colspan='2'>{sim('k_e')} = {num(K, 2)}</th></tr>"
        "<tr><th></th><th></th><th class='n'>analítica</th><th class='n'>simulada</th>"
        "<th class='n'>analítica</th><th class='n'>simulada</th></tr>",
        filas,
        f"La fórmula predice la simulación en las dos escalas. Sobre <em>todas</em> las "
        f"celdas de los tres casos y los tres {sim('d')} en que al menos la mitad de las "
        f"réplicas llega a las {sim('k')} experiencias, la desviación máxima es "
        f"{num(peor, 4)}. Las celdas donde no llega —ver tabla 7— quedan fuera porque ahí "
        f"la cantidad simulada se promedia sobre muy pocas réplicas o sobre ninguna.",
    )


def _t7() -> str:
    """Truncamiento: que fraccion llega a recibir los k shocks."""
    filas = ""
    for k in KS:
        celdas = "".join(
            f"<td class='n'>{num(100 * r1(GUEV, REF, D_REF, k, r)['llegan_a_k'], 1)}</td>"
            for r in RS
        )
        filas += f"<tr><td class='n'>{k}</td>{celdas}</tr>"
    cero_g = sum(1 for x in GUEV["e1"] if x.get("k") and x["llegan_a_k"] == 0.0)
    cero_b = sum(1 for x in BASE["e1"] if x.get("k") and x["llegan_a_k"] == 0.0)
    tot = sum(1 for x in GUEV["e1"] if x.get("k"))
    return tabla(
        7,
        f"Autotruncamiento — % de réplicas que llega a recibir las {sim('k')} experiencias "
        f"({REF}, {sim('d')} = {num(D_REF, 2)}, escala de Guevara)",
        f"<tr><th class='n'>{sim('k')} \\ {sim('r')}</th>"
        + "".join(f"<th class='n'>{num(r, 1)}</th>" for r in RS)
        + "</tr>",
        filas,
        f"Los shocks se entregan cuando la persona <em>elige</em> el modo, así que "
        f"abandonar antes de tiempo la protege de recibir el resto. Con "
        f"{sim('k')} = {max(KS)} y {sim('r')} = 3 sólo el "
        f"{num(100 * r1(GUEV, REF, D_REF, max(KS), 3.0)['llegan_a_k'], 1)} % llega. En "
        f"toda la grilla hay {cero_g} celdas de {tot} donde <strong>ninguna</strong> "
        f"réplica llega, contra {cero_b} con la escala vieja. No es un defecto del "
        f"diseño: es el mecanismo. Pero sí obliga a leer las celdas extremas como "
        f"«{sim('k')} intentos de shock», no «{sim('k')} shocks recibidos».",
    )


def _t8() -> str:
    """Contraste entre casos: aca el patron es el inverso al de E2."""
    kk, rr = 3, 2.0
    filas = ""
    for c in ("C1", "C2", "C3"):
        a, g = r1(BASE, c, D_REF, kk, rr), r1(GUEV, c, D_REF, kk, rr)
        filas += (
            f"<tr><td>{c}</td><td class='n'>{num(CB[c]['ventaja_min'], 1)}</td>"
            f"<td class='n'>{num(a['delta_min'], 1)}</td>"
            f"<td class='n'>{num(CG[c]['p_verdadera'], 4)}</td>"
            f"<td class='n'>{num(g['p_post_analitica'], 4)}</td>"
            f"<td class='n'>{pp(a['efecto']['largo'])}</td>"
            f"<td class='n'><strong>{pp(g['efecto']['largo'])}</strong></td></tr>"
        )
    return tabla(
        8,
        f"Los tres casos — {sim('k')} = {kk}, {sim('r')} = {num(rr, 1)}, "
        f"{sim('d')} = {num(D_REF, 2)}",
        f"<tr><th>caso</th><th class='n'>{sim('A')} (min)</th>"
        f"<th class='n'>{sim('Δ')} (min)</th>"
        f"<th class='n'>{sim('P*')} (Guevara)</th>"
        f"<th class='n'>{sim('P_post')} (Guevara)</th>"
        f"<th class='n'>largo plazo, {sim('k_e')} = 1</th>"
        f"<th class='n'>largo plazo, {sim('k_e')} = {num(K, 2)}</th></tr>",
        filas,
        f"Acá el caso más dominante es el <strong>más</strong> dañado, al revés que en E2. "
        f"La razón está en la columna {sim('Δ')}: como el shock se define en múltiplos de "
        f"la ventaja, C3 recibe {num(r1(BASE, 'C3', D_REF, kk, rr)['delta_min'], 0)} min "
        f"de penalización contra {num(r1(BASE, 'C1', D_REF, kk, rr)['delta_min'], 0)} de C1. "
        f"Eso hunde su {sim('P_post')} a {num(r1(GUEV, 'C3', D_REF, kk, rr)['p_post_analitica'], 5)}: "
        f"deja de muestrear el modo y no tiene cómo enterarse de que ya no es malo.",
    )


def s5() -> str:
    return f"""
<h2 id="resultados">5. Resultados</h2>

<h3>5.1 Qué tan mala tiene que ser la experiencia</h3>

{_t3()}

{fig(f"e1-critico-{REF}-guevara.png", 1, f"Probabilidad de elegir el modo mejor justo después del {tex('k')}-ésimo shock, contra el tamaño del shock en múltiplos de la ventaja. Línea: la fórmula (8); puntos: la simulación. Un panel por valor de {tex('d')}. El cruce por ½ ocurre en {tex(r'\Delta/A = 1/W_k')} y no depende de la escala; lo que la escala cambia es cuán vertical es la caída.")}

<h3>5.2 La respuesta alrededor del umbral</h3>

{_t4()}

<h3>5.3 Recuperación o trampa</h3>

<p>Las dos figuras siguientes son el mismo gráfico en las dos escalas, y son el
resultado central de E1.</p>

{fig(f"e1-trayectorias-{REF}-d{D_REF}.png", 2, f"Trayectoria día a día con la escala vieja ({tex('k_e')} = 1), caso {REF}, {tex('d')} = {num(D_REF, 2)}. Izquierda: una experiencia mala; derecha: cinco. Todas las curvas vuelven al control — el daño es transitorio en toda la grilla.")}

{fig(f"e1-trayectorias-{REF}-d{D_REF}-guevara.png", 3, f"Lo mismo a la escala de Guevara. Con {tex('k')} = 5 y {tex(r'\Delta')} = 6{tex('A')} la curva cae a cero y <strong>se queda plana los 250 días</strong>. Con {tex('k')} = 1 el mismo shock todavía se recupera, aunque lento.")}

{_t5()}

{fig(f"e1-horizontes-{REF}-d{D_REF}-guevara.png", 4, "Efecto por horizonte a la escala de Guevara. Se lee comparando paneles: lo que en el corto plazo le pasa a todas las combinaciones, en el largo plazo sólo les queda a las que cruzaron la frontera de la tabla 5.")}

<h3>5.4 ¿Predice la fórmula?</h3>

{_t6()}

<h3>5.5 La persona se protege sola</h3>

{_t7()}

{fig(f"e1-distribuciones-{REF}-d{D_REF}-guevara.png", 5, "Distribución entre réplicas, no sólo el promedio. En el largo plazo la distribución se parte en dos: réplicas que volvieron al control y réplicas que se quedaron abajo. El promedio de la tabla 5 es la mezcla de esas dos poblaciones, no el estado típico de nadie.")}

<h3>5.6 Los tres casos</h3>

{_t8()}
"""


# --- 6. Análisis ----------------------------------------------------------------


def s6() -> str:
    minp = min(r1(BASE, REF, D_REF, k, r)["p_post_analitica"] for k in KS for r in RS)
    return f"""
<h2 id="analisis">6. Análisis</h2>

<h3>6.1 Dos umbrales, no uno</h3>

<p>E1 tiene <strong>dos</strong> fronteras y conviene no confundirlas. La primera es
{tex(r"\Delta^*")}: el shock que vuelca la decisión <em>hoy</em>. Es exacta, se escribe
con la ec. (7) y no depende de la escala del logit. La segunda no tiene fórmula cerrada
acá y es la que decide si el daño <em>persiste</em>: hace falta que
{tex("P_{\\text{post}}")} quede tan bajo que la persona prácticamente deje de muestrear
el modo, porque sólo muestreándolo puede enterarse de que ya volvió a ser bueno.</p>

<p>La ec. (2) es la que conecta ambas: si {tex(r"a_{ni}(t')")} queda en cero día tras
día, la creencia se congela en el peor momento. El aprendizaje no es simétrico —
castiga rápido y perdona sólo si le das la oportunidad.</p>

<h3>6.2 Por qué con μ = 1 no había trampa</h3>

<p>Con la escala vieja, el {tex("P_{\\text{post}}")} más bajo de toda la grilla del
caso de referencia es {num(minp, 3)}. Eso es un {num(100 * minp, 0)} % de probabilidad
de volver a probar el modo <em>cada día</em>: en una semana la persona vuelve casi
seguro, recibe información nueva y se recupera. Por eso todas las curvas de la figura 2
vuelven al control.</p>

<p>A la escala de Guevara ese mismo {tex("P_{\\text{post}}")} se va a órdenes de
{num(r1(GUEV, REF, D_REF, 5, 6.0)["p_post_analitica"], 5)}. Ahí la persona no vuelve a
probar nunca, y lo que era una caída transitoria se vuelve permanente. <strong>No es
que la escala amplifique el efecto: es que crea el fenómeno</strong>, porque la
persistencia depende de un umbral de muestreo que con {tex(r"\mu")} = 1 nunca se
cruzaba.</p>

<p>Dicho de otro modo: la conclusión del informe publicado —«el efecto de una mala
racha se borra»— no era un resultado del modelo IBL, sino del valor de {tex(r"\mu")}.</p>

<h3>6.3 El autotruncamiento es el mecanismo, no ruido</h3>

<p>La tabla 7 parece un problema de diseño y es justamente lo contrario. Que sólo el
{num(100 * r1(GUEV, REF, D_REF, max(KS), 3.0)["llegan_a_k"], 1)} % de las réplicas
llegue a recibir {max(KS)} experiencias malas significa que la mayoría <strong>ya se
había ido</strong>. Es el mismo fenómeno que E2 llama <em>hot stove</em>, visto desde
el otro lado: la persona se protege de más información mala, y al hacerlo se protege
también de la información buena que la haría volver.</p>

<p>La consecuencia práctica es de lectura: en las celdas extremas, {tex("k")} es
«intentos de shock», no «shocks recibidos». Un diseño que quisiera entregar
{tex("k")} shocks de verdad tendría que forzar la exposición, y eso ya sería otra
pregunta de investigación.</p>

<h3>6.4 Lo que este informe no muestra</h3>

<ul>
  <li><strong>El shock es un sesgo determinista, no variabilidad.</strong> Acá los
      {tex("k")} primeros usos salen exactamente {tex(r"\Delta")} peores. La
      variabilidad aleatoria es el experimento E2, y los dos mecanismos interactúan de
      maneras que ninguno de los dos informes mide.</li>
  <li><strong>Un solo {tex(r"\beta")}.</strong> Guevara estima dos coeficientes de
      tiempo, uno por ruta (tabla 2). Acá se usó sólo TIMEF, porque
      {tex(r"A = \Delta V/|\beta|")} deja de estar bien definido con dos.</li>
  <li><strong>Sin inercia.</strong> El CWA de Guevara (5,71) captura la tendencia a
      repetir lo elegido, que agravaría el atrapamiento. No está en este modelo.</li>
  <li><strong>El prior es exacto.</strong> La persona arranca creyendo los tiempos de
      referencia. Un prior equivocado movería el umbral y no se exploró.</li>
  <li><strong>{tex("k")} y {tex(r"\Delta")} no están calibrados.</strong> La grilla es
      exploratoria; cuántas malas experiencias seguidas son realistas en esta ciudad es
      una pregunta aparte.</li>
</ul>
"""


# --- 7. Conclusiones ------------------------------------------------------------


def s7() -> str:
    dc = CB[REF]["delta_critico"][str(D_REF)]
    peor_base = min(x["efecto"]["largo"] for x in BASE["e1"] if x.get("k") and x["caso"] == REF)
    peor_guev = min(x["efecto"]["largo"] for x in GUEV["e1"] if x.get("k") and x["caso"] == REF)
    return f"""
<h2 id="conclusiones">7. Conclusiones</h2>

<ol>
  <li><strong>El umbral tiene fórmula y no depende de la escala.</strong>
      {tex(r"\Delta^* = A/W_k")}: para el caso de referencia, entre
      {num(dc[str(max(KS))], 1)} y {num(dc[str(min(KS))], 1)} minutos según cuántas
      veces ocurra. Verificado idéntico en las dos escalas.</li>
  <li><strong>La fórmula (8) reproduce la simulación</strong> en las dos escalas, con
      desviación máxima pequeña donde hay muestra suficiente (tabla 6). El resto del
      informe se apoya en eso.</li>
  <li><strong>Cruzar el umbral y quedar atrapado son cosas distintas.</strong> Lo
      primero depende de la memoria; lo segundo, de que
      {tex("P_{\\text{post}}")} caiga tan bajo que la persona deje de muestrear.</li>
  <li><strong>La trampa permanente sólo aparece a escala realista.</strong> Con
      {tex(r"\mu")} = 1 el peor efecto de largo plazo de las {len(KS) * len(RS) * len(DECS)}
      combinaciones es {pp(peor_base)} —ruido—; a la escala de Guevara llega a {pp(peor_guev)} y no se
      recupera dentro de los {BASE["dias"]} días.</li>
  <li><strong>La persona se autotrunca.</strong> En buena parte de la grilla abandona
      antes de recibir todos los shocks, lo que protege de más información mala y
      también de la buena.</li>
  <li><strong>Más ventaja no protege; en E1 expone.</strong> Como el shock se mide en
      múltiplos de la ventaja, el caso más dominante recibe el golpe absoluto más
      grande y es el que queda peor (tabla 8). Es el patrón contrario al de E2 y
      conviene no mezclarlos.</li>
</ol>

<h3>7.1 Lo que queda</h3>

<ul>
  <li>Rehacer E3 (ciudad completa) y E4 (cuatro modos) a esta escala; hoy no tienen
      corrida en la escala de Guevara.</li>
  <li>Mapear la frontera de persistencia con una grilla más fina entre
      {tex("r")} = 2 y 4, que es donde cambia de régimen.</li>
  <li>Medir shock y variabilidad juntos, que es lo que pasa en la realidad.</li>
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
  <li>Denrell, J. y March, J. G. (2001), sobre el <em>hot stove effect</em>:
      <strong>citado de memoria, sin verificar contra el texto.</strong> Guevara et al.
      (2018) no lo cita, así que no se pudo confirmar desde el PDF que sí tenemos.</li>
</ul>

<h2 id="reproducir">Reproducir</h2>

<pre><code>cd sandbox/ibl-dia-a-dia
uv sync --extra dev --reinstall-package titirilquen-core   # el núcleo del repo, no uno cacheado
uv run --extra dev pytest                                  # las fórmulas (7)–(9)
uv run python experimentos.py                              # ~5 min → salida/experimentos.json
uv run python experimentos.py --guevara                    # ~5 min → salida/experimentos-guevara.json
uv run python figuras_experimentos.py
uv run python figuras_experimentos.py --guevara
uv run python informe_e1.py
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
        titulo="E1 · Experiencias malas tempranas",
        h1="Experiencias malas tempranas",
        bajada=(
            "Cuánto hace falta para que una mala racha cambie la conducta, y cuándo el "
            "efecto se borra en vez de quedarse para siempre."
        ),
        meta=(
            f"Experimento E1 · caso de referencia {REF} · d = {num(D_REF, 2)} · "
            f"{BASE['dias']} días × {BASE['replicas']} réplicas · "
            f"escalas kₑ = 1 y kₑ = {num(K, 3)}"
        ),
        indice=indice,
        cuerpo=cuerpo,
    )
    destino = AQUI / "informe-e1.html"
    destino.write_text(html, encoding="utf-8")
    print(f"  {destino}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
