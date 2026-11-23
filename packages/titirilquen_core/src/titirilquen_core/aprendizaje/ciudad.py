"""La ciudad entera aprende día a día, con la congestión respondiendo.

Es el motor de los experimentos E3 (dos modos, todos con auto) y E4 (los cuatro
modos de la app, con el ruido en unos y no en otros). La diferencia con
`aprendizaje.persona` cabe en una frase: **acá la red responde**. Cada día todos
eligen con sus tiempos percibidos, los flujos cargan la oferta, y cada uno
experimenta el tiempo real de su modo en su celda. Al día siguiente decide con
el IBL sobre lo que vivió.

Eso agrega dos cosas que con una persona no existen:

* **Congestión endógena.** Si muchos abandonan el metro el auto se llena y los
  devuelve: el agregado se estabiliza aunque abajo las personas roten.
* **Personas comparables.** Con decenas de miles de agentes hay muchos grupos
  idénticos por construcción, y se puede medir cuánto los separó la historia.

**La escala.** `escala` multiplica la utilidad antes del softmax. Es el mismo
objeto que multiplicar los β, y acá **no es inocua**: el día 0 es el equilibrio
que calcula el MSA con escala 1, y con otra deja de ser punto fijo — la ciudad
se corre sola sin ningún ruido. Por eso la línea base es siempre el control sin
ruido de la misma escala, nunca el día 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from titirilquen_core.aprendizaje.ibl import tiempo_percibido
from titirilquen_core.city import CiudadLineal
from titirilquen_core.config import SimulationConfig
from titirilquen_core.demand.utility import TiemposObservados, calcular_utilidades
from titirilquen_core.equilibrium.msa import run_msa
from titirilquen_core.land_use.config import LandUseConfig
from titirilquen_core.supply.oferta import resolver_oferta

#: Los cuatro modos, en el orden en que viven las columnas de utilidad.
MODOS_CIUDAD = ("Auto", "Metro", "Bici", "Caminata")

#: Bandas de la ventaja del mejor sobre el segundo (útiles del núcleo) para leer
#: el efecto por tamaño de ventaja: con ventajas grandes no hay recorrido. Se
#: calculan sobre `V_ref`, que NO lleva la escala, así que parten a la misma
#: gente en cualquier corrida y las columnas son comparables.
BANDAS = ((0.0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, np.inf))


def softmax_filas(V: NDArray[np.float64], escala: float) -> NDArray[np.float64]:
    """Logit sobre los modos factibles, fila por fila.

    `escala` multiplica toda la utilidad: es el μ del logit. El núcleo normaliza
    μ = 1 y son los β los que la absorben, así que el default reproduce el
    simulador; otro valor es una sensibilidad de calibración, no una corrección.
    """
    z = escala * (V - V.max(axis=1, keepdims=True))
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _sortear(P: NDArray[np.float64], rng: np.random.Generator) -> NDArray[np.int_]:
    """Una elección por persona, según su fila de probabilidades."""
    cum = P.cumsum(axis=1)
    u = rng.random(P.shape[0])[:, None]
    return np.minimum((u > cum).sum(axis=1), P.shape[1] - 1)


@dataclass
class EscenarioCiudad:
    """La ciudad, la población y la referencia del día 0, listas para vectorizar.

    Se arma UNA vez con `preparar_escenario` —que resuelve el equilibrio— y se
    reusa en todos los experimentos: el MSA es el paso caro.

    Se aprenden los `K` primeros modos de `MODOS_CIUDAD`: auto y metro (E3), más
    la bici (E4). La caminata nunca, porque su tiempo es geométrico y no tiene
    ni congestión ni ruido: vive entero en `V_ref`.
    """

    sim: SimulationConfig
    ciudad: CiudadLineal
    K: int
    celda: NDArray[np.int_]
    estrato: NDArray[np.int_]
    tiene_auto: NDArray[np.bool_]
    t_ref: NDArray[np.float64]
    """(L, K) tiempo de equilibrio por celda de los modos que se aprenden."""
    V_ref: NDArray[np.float64]
    """(N, 4) utilidad con los tiempos del día 0."""
    feas: NDArray[np.bool_]
    btv: NDArray[np.float64]
    """(N,) coeficiente del tiempo de viaje de cada persona."""
    split_equilibrio: list[float]
    n_grupos: int
    J: NDArray[np.int_] = field(init=False)
    elige: NDArray[np.bool_] = field(init=False)
    mejor: NDArray[np.int_] = field(init=False)
    dv: NDArray[np.float64] = field(init=False)

    def __post_init__(self) -> None:
        Vf = np.where(self.feas, self.V_ref, -np.inf)
        self.J = self.feas.sum(axis=1)
        # Sólo cuentan quienes PUEDEN elegir: con un único modo factible no hay
        # aprendizaje que medir, y promediarlos ensucia todos los indicadores.
        self.elige = self.J >= 2
        self.mejor = Vf.argmax(axis=1)
        orden = np.sort(Vf, axis=1)
        self.dv = orden[:, -1] - orden[:, -2]

    @property
    def N(self) -> int:
        return int(self.celda.shape[0])


def preparar_escenario(
    sim: SimulationConfig, lu: LandUseConfig, *, k_modos: int = 2
) -> EscenarioCiudad:
    """El paso caro: resuelve el equilibrio y arma la población.

    `k_modos` = 2 es E3 (auto y metro); 3 es E4, que agrega la bici. El
    resultado se reusa en todos los experimentos de esa ciudad.
    """
    if k_modos not in (2, 3):
        raise ValueError("k_modos debe ser 2 (auto y metro) o 3 (más la bici)")
    trace = run_msa(sim, lu, localizacion="equilibrio")
    s = trace.iteraciones[-1]
    ciudad = CiudadLineal(n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km)
    L = ciudad.n_celdas
    # Los teletrabajadores no eligen modo: quedan fuera.
    agentes = [a for a in trace.agentes if not a.teletrabaja]
    if not agentes:
        raise ValueError("la ciudad no tiene agentes que elijan modo")
    celda = np.array([a.celda_origen for a in agentes])
    estrato = np.array([a.estrato for a in agentes])
    tiene_auto = np.array([a.tiene_auto for a in agentes])

    t_ref = np.stack([s.t_auto, s.t_tren_viaje, s.t_bici][:k_modos], axis=1).astype(float)
    ref = [
        TiemposObservados(
            auto_total=float(s.t_auto[i]),
            bici_total=float(s.t_bici[i]),
            tren_acceso=float(s.t_tren_acceso[i]),
            tren_espera=float(s.t_tren_espera[i]),
            tren_viaje=float(s.t_tren_viaje[i]),
            bici_libre=float(s.t_bici_libre[i]),
        )
        for i in range(L)
    ]

    # La utilidad se calcula UNA vez por grupo (estrato, celda, tenencia de
    # auto): son decenas de miles de agentes y unos pocos miles de grupos.
    cache: dict[tuple[int, int, bool], tuple[NDArray, NDArray]] = {}
    n = len(agentes)
    V_ref = np.zeros((n, 4))
    feas = np.zeros((n, 4), dtype=bool)
    for i in range(n):
        key = (int(estrato[i]), int(celda[i]), bool(tiene_auto[i]))
        if key not in cache:
            u = calcular_utilidades(
                estrato=key[0],  # type: ignore[arg-type]
                celda_origen=key[1],
                tiene_auto=key[2],
                ciudad=ciudad,
                config=sim.demand,
                tiempos_observados=ref[key[1]],
                modos_habilitados=sim.modos_habilitados,
            )
            cache[key] = (
                np.array([u[m].valor for m in MODOS_CIUDAD]),
                np.array([u[m].feasible for m in MODOS_CIUDAD]),
            )
        V_ref[i], feas[i] = cache[key]

    split = s.modal_split
    tot = sum(v for m, v in split.items() if m != "Teletrabajo")
    return EscenarioCiudad(
        sim=sim,
        ciudad=ciudad,
        K=k_modos,
        celda=celda,
        estrato=estrato,
        tiene_auto=tiene_auto,
        t_ref=t_ref,
        V_ref=V_ref,
        feas=feas,
        btv=np.array([sim.demand.estratos[int(h)].betas.b_tiempo_viaje for h in estrato]),
        split_equilibrio=[split[m] / tot for m in MODOS_CIUDAD],
        n_grupos=len(cache),
    )


# --- Indicadores ----------------------------------------------------------------


def suerte_del_estreno(
    primera_eps: NDArray[np.float64], share_final: NDArray[np.float64]
) -> tuple[float, float]:
    """Cuota final de quienes estrenaron el modo con mala y con buena suerte.

    Compara el decil peor de la primera experiencia contra el decil mejor. Si el
    azar del primer día no deja huella, los dos números coinciden. Devuelve
    (mala, buena); NaN si hay muy pocos casos para decir algo.
    """
    ok = ~np.isnan(primera_eps)
    if ok.sum() < 20:
        return float("nan"), float("nan")
    q10, q90 = np.nanpercentile(primera_eps, [10, 90])
    mala = share_final[ok & (primera_eps >= q90)]
    buena = share_final[ok & (primera_eps <= q10)]
    return float(mala.mean()), float(buena.mean())


def cuota_del_mejor(
    esc: EscenarioCiudad, ult: NDArray[np.int_], v_ult: NDArray[np.float64]
) -> dict:
    """Fracción de viajes hecha en el modo que de verdad es mejor, por banda.

    «De verdad mejor» se define con la utilidad verdadera media de los últimos
    días, no con la percibida: es lo que la persona habría elegido sabiendo. El
    efecto de variabilidad dice que con más ruido esa cuota se acerca a 1/J.
    """
    Vf = np.where(esc.feas, v_ult, -np.inf)
    mejor = Vf.argmax(axis=1)
    orden = np.sort(Vf, axis=1)
    ventaja = orden[:, -1] - orden[:, -2]
    ok = esc.elige
    cuota = (ult == mejor[:, None]).mean(axis=1)
    out: dict = {"todos": float(cuota[ok].mean()), "n": int(ok.sum()), "bandas": []}
    for lo, hi in BANDAS:
        sel = ok & (ventaja >= lo) & (ventaja < hi)
        out["bandas"].append(
            {
                "desde": lo,
                "hasta": None if np.isinf(hi) else hi,
                "cuota": float(cuota[sel].mean()) if sel.any() else float("nan"),
                "n": int(sel.sum()),
            }
        )
    return out


def dispersion_entre_iguales(esc: EscenarioCiudad, ult: NDArray[np.int_]) -> float:
    """Cuánto diferenció la historia a personas idénticas, sobre la binomial.

    Personas iguales = mismo estrato, misma celda y misma tenencia de auto, con
    J ≥ 2: tienen el mismo modo mejor y la misma probabilidad de equilibrio. Si
    todas eligieran con esa misma P, la varianza de su cuota en la ventana sería
    la binomial. La razón vale ≈ 1 si la historia no diferenció a nadie, y crece
    cuando sí. Es el indicador de dependencia de trayectoria, y no tiene análogo
    con una sola persona.
    """
    el = esc.elige
    share = (ult[el] == esc.mejor[el][:, None]).mean(axis=1)
    clave = (esc.estrato[el] * esc.ciudad.n_celdas + esc.celda[el]) * 2 + esc.tiene_auto[el]
    _, g = np.unique(clave, return_inverse=True)
    n = np.bincount(g).astype(float)
    p = np.bincount(g, weights=share) / n
    var_obs = np.bincount(g, weights=(share - p[g]) ** 2) / n
    var_bin = p * (1.0 - p) / ult.shape[1]
    ok = (n >= 2) & (var_bin > 0)
    if not ok.any():
        return float("nan")
    return float((n[ok] * var_obs[ok]).sum() / (n[ok] * var_bin[ok]).sum())


def phi_poblacion(
    esc: EscenarioCiudad,
    p_ventana: dict[str, NDArray[np.float64]],
    escala: float,
) -> dict:
    """Φ = (S − 1/J)/(P* − 1/J) por horizonte, en total y por grupo.

    Con dos modos 1/J = ½ y es el Φ de una persona tal cual; con más, el punto
    de indiferencia es el reparto uniforme entre los modos factibles de cada
    persona. Se abre por banda de ventaja y por cuál es el modo mejor — esto
    último es lo que separa a quien tiene el ruido encima de quien no.

    Ojo donde P* − 1/J es chico: ahí Φ amplifica cualquier diferencia. Por eso
    se devuelven también P*, 1/J y S crudos.
    """
    el = esc.elige
    p_est = np.full(esc.N, np.nan)
    P_ref = softmax_filas(np.where(esc.feas[el], esc.V_ref[el], -np.inf), escala)
    p_est[el] = P_ref[np.arange(el.sum()), esc.mejor[el]]
    u = 1.0 / np.maximum(esc.J, 1)

    def phi(sel: NDArray[np.bool_], w: str) -> float:
        U = u[sel].mean()
        den = p_est[sel].mean() - U
        return float((p_ventana[w][sel].mean() - U) / den) if den != 0 else float("nan")

    ventanas = list(p_ventana)
    out: dict = {"todos": {w: phi(el, w) for w in ventanas}, "bandas": []}
    for lo, hi in BANDAS:
        sel = el & (esc.dv >= lo) & (esc.dv < hi)
        fila = {"desde": lo, "hasta": None if np.isinf(hi) else hi, "n": int(sel.sum())}
        if sel.any():
            fila["p_estrella"] = float(p_est[sel].mean())
            fila.update({w: phi(sel, w) for w in ventanas})
        out["bandas"].append(fila)

    # Por modo mejor del equilibrio: separa a quienes viven el ruido en SU modo
    # mejor de quienes lo viven en uno peor. Es la asimetría de E2, pero acá no
    # se impone por diseño: sale de quién es cada persona.
    out["por_mejor"] = {}
    for k, m in enumerate(MODOS_CIUDAD):
        sel = el & (esc.mejor == k)
        if not sel.any():
            continue
        fila = {
            "n": int(sel.sum()),
            "p_estrella": float(p_est[sel].mean()),
            "uniforme": float(u[sel].mean()),
            "s": {w: float(p_ventana[w][sel].mean()) for w in ventanas},
        }
        fila.update({w: phi(sel, w) for w in ventanas})
        out["por_mejor"][m] = fila
    return out


# --- Simulación -----------------------------------------------------------------


def simular_ciudad(
    esc: EscenarioCiudad,
    *,
    d: float,
    sigma: float = 0.0,
    ruido: tuple[bool, ...] | None = None,
    escala: float = 1.0,
    dias: int = 250,
    ultimos: int = 20,
    ventanas: dict[str, tuple[int, int]] | None = None,
    semilla: int = 42,
    truncar: bool = False,
) -> dict:
    """Un experimento sobre la ciudad ya preparada.

    `ruido[k]` dice si el modo aprendido `k` lleva ε; por defecto, todos (E3).
    Dejarlo en False para alguno es la pregunta de E4: a dónde van los viajes
    que el ruido expulsa.

    El costo crece con el CUADRADO del horizonte —el IBL pondera toda la
    historia— así que `dias` es la palanca que hace esto usable en vivo.
    """
    if dias < 3:
        raise ValueError("hacen falta al menos 3 días")
    if ultimos > dias:
        raise ValueError("`ultimos` no puede pasar del horizonte")
    from titirilquen_core.aprendizaje.ejecutar import ventanas as ventanas_de

    vs = ventanas or ventanas_de(dias)
    rng = np.random.default_rng(semilla)
    N, L, K = esc.N, esc.ciudad.n_celdas, esc.K
    ruido = (True,) * K if ruido is None else ruido
    if len(ruido) != K:
        raise ValueError(f"`ruido` debe tener {K} elementos, uno por modo aprendido")

    x = np.zeros((N, dias + 1, K))
    a = np.zeros((N, dias + 1, K), dtype=bool)
    x[:, 0, :] = esc.t_ref[esc.celda]  # el prior: los tiempos del equilibrio
    a[:, 0, :] = True
    t_ref = x[:, 0, :].copy()

    modo_hist = np.zeros((N, dias), dtype=np.int8)
    p_ventana = {w: np.zeros(N) for w in vs}
    primera_eps = np.full((N, K), np.nan)
    split_dia = np.zeros((dias, 4))
    bienestar = np.zeros(dias)
    bienestar_decision = np.zeros(dias)
    v_ult = np.zeros((N, len(MODOS_CIUDAD)))

    for t in range(1, dias + 1):
        b = tiempo_percibido(x, a, t, d)
        V = esc.V_ref.copy()
        V[:, :K] += esc.btv[:, None] * (b - t_ref)
        V[~esc.feas] = -np.inf
        P = softmax_filas(V, escala)
        modo = _sortear(P, rng)
        p_mejor = P[np.arange(N), esc.mejor]
        for w, (ini, fin) in vs.items():
            if ini <= t <= fin:
                p_ventana[w] += p_mejor / (fin - ini + 1)
        modo_hist[:, t - 1] = modo
        bienestar_decision[t - 1] = V[np.arange(N), modo].mean()

        # La red responde: los flujos del día cargan la oferta.
        d_auto = np.bincount(esc.celda[modo == 0], minlength=L).astype(float)
        d_metro = np.bincount(esc.celda[modo == 1], minlength=L).astype(float)
        d_bici = np.bincount(esc.celda[modo == 2], minlength=L).astype(float)
        oferta = resolver_oferta(esc.sim, esc.ciudad, d_auto, d_bici, d_metro)
        red = (
            oferta.auto.t_usuarios_min,
            oferta.tren.t_viaje_min,
            oferta.bici.t_usuarios_min,
        )

        # Siempre se consume del generador, aun con sigma = 0: saltarlo
        # correría el flujo y los resultados dejarían de ser comparables
        # con los publicados.
        eps = rng.normal(0.0, sigma, size=N)
        real = np.stack([np.asarray(r, dtype=float)[esc.celda] for r in red[:K]], axis=1)
        for k in range(K):
            usa = modo == k
            vivido = real[usa, k] + eps[usa] if ruido[k] else real[usa, k]
            x[usa, t, k] = np.maximum(vivido, 0.0) if truncar else vivido
            a[usa, t, k] = True
            if ruido[k]:
                nuevo = usa & np.isnan(primera_eps[:, k])
                primera_eps[nuevo, k] = eps[nuevo]

        split_dia[t - 1] = np.bincount(modo, minlength=4) / N
        V_true = esc.V_ref.copy()
        V_true[:, :K] += esc.btv[:, None] * (real - t_ref)
        bienestar[t - 1] = V_true[np.arange(N), modo].mean()
        if t > dias - ultimos:
            v_ult += V_true / ultimos

    ult = modo_hist[:, -ultimos:]
    fila: dict = {
        "sigma": sigma,
        "escala": escala,
        "d": d,
        "dias": dias,
        "ultimos": ultimos,
        "split_por_dia": split_dia.round(5).tolist(),
        "split_ultimos": split_dia[-ultimos:].mean(axis=0).tolist(),
        "bienestar_por_dia": bienestar.round(5).tolist(),
        "bienestar_decision_por_dia": bienestar_decision.round(5).tolist(),
        "cuota_mejor": cuota_del_mejor(esc, ult, v_ult),
        "dispersion_iguales": dispersion_entre_iguales(esc, ult),
        "phi": phi_poblacion(esc, p_ventana, escala),
    }
    for k, nombre in ((0, "auto"), (1, "metro")):
        puede = esc.feas[:, k]
        share_ult = (ult == k).mean(axis=1)
        fila[f"abandono_{nombre}"] = float(np.mean(share_ult[puede] == 0.0))
        mala, buena = suerte_del_estreno(primera_eps[puede, k], share_ult[puede])
        fila[f"share_fin_mala_suerte_{nombre}"] = mala
        fila[f"share_fin_buena_suerte_{nombre}"] = buena
    return fila
