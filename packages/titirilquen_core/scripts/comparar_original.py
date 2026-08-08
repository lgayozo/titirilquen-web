"""Comparacion contra el simulador ORIGINAL (github.com/lehyt2163/Titirilquen).

Regenera todas las cifras de `docs/COMPARACION_ORIGINAL.md`. Responde tres
preguntas, en este orden:

1. EQUIVALENCIA ESTRUCTURAL — ¿las ecuaciones son las mismas? Se verifica
   EJECUTANDO ambas implementaciones sobre las mismas entradas, no leyendo.
2. PARAMETROS — ¿que implican los betas? Se comparan las cantidades
   interpretables (VST, ponderadores, ASC en minutos), no los betas crudos.
3. IMPACTO — ¿cuanto mueven los resultados? Se corre el MOTOR ACTUAL con los
   PARAMETROS DEL ORIGINAL, aislando el efecto de la calibracion del efecto de
   los cambios de codigo.

El codigo original NO esta versionado (es un repo aparte, GPL-3.0). Clonalo a
`reference/` — que esta en .gitignore — antes de correr:

    git clone https://github.com/lehyt2163/Titirilquen.git reference/titirilquen-original

Correr desde packages/titirilquen_core (~1 min):

    uv run python scripts/comparar_original.py
"""

from __future__ import annotations

import ast
import contextlib
import sys
import types
from pathlib import Path

import numpy as np
from scipy.special import logsumexp

sys.path.insert(0, str(Path(__file__).parent))

from auditoria_transporte import base_lu, base_sim

from titirilquen_core.config import SupplyConfig
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    iter_msa_desde_suelo,
)
from titirilquen_core.land_use.ciudad import V_REF_KMH, LandUseCity
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig
from titirilquen_core.land_use.equilibrium import solve_logit
from titirilquen_core.supply.car import demora_auto_tramo as car_actual

RAIZ = Path(__file__).parent.parent.parent.parent
ORIGINAL = RAIZ / "reference" / "titirilquen-original" / "app.py"

# Funciones puras del original que se extraen para ejecutarlas. NO se importa
# `app.py`: es una app Streamlit y el import ejecutaria la UI.
FUNCIONES_PURAS = {"demora_auto_tramo", "demora_bici_tramo", "oferta_tren"}


def _cargar_original() -> tuple[dict, dict]:
    """Devuelve (constantes, funciones puras) de `app.py` sin ejecutar Streamlit."""
    if not ORIGINAL.exists():
        sys.exit(
            f"No se encontro {ORIGINAL}.\n"
            "Clonalo primero (no esta versionado):\n"
            "  git clone https://github.com/lehyt2163/Titirilquen.git "
            "reference/titirilquen-original"
        )
    arbol = ast.parse(ORIGINAL.read_text(encoding="utf-8"))

    constantes: dict = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and isinstance(nodo.targets[0], ast.Name):
            # ValueError = no es un literal (llamadas, f-strings, etc.)
            with contextlib.suppress(ValueError):
                constantes[nodo.targets[0].id] = ast.literal_eval(nodo.value)

    modulo = ast.Module(
        body=[
            n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name in FUNCIONES_PURAS
        ],
        type_ignores=[],
    )
    ns: dict = {"np": np}
    exec(compile(ast.fix_missing_locations(modulo), "<original>", "exec"), ns)
    return constantes, {k: ns[k] for k in FUNCIONES_PURAS if k in ns}


def seccion(titulo: str) -> None:
    print(f"\n\n{'=' * 74}\n{titulo}\n{'=' * 74}")


# ---------------------------------------------------------------- 1. EQUIVALENCIA


def equivalencia_auto(funcs: dict) -> None:
    """La oferta vial es un port linea a linea: se verifica numericamente."""
    seccion("1a. OFERTA AUTO — equivalencia numerica original vs core")
    print("Misma demanda aleatoria, mismos parametros. Diferencia esperada: 0.\n")
    rng = np.random.default_rng(0)
    n_celdas, largo_km = 201, 20.0
    casos = {
        "2 pistas, 3.5 m, BPR(0.8, 2)": (2, 3.5, 0.8, 2.0),
        "1 pista,  3.5 m, BPR(0.8, 2)": (1, 3.5, 0.8, 2.0),
        "4 pistas, 3.2 m, BPR(0.15, 4)": (4, 3.2, 0.15, 4.0),
        "2 pistas, 2.8 m, BPR(0.8, 2)": (2, 2.8, 0.8, 2.0),
        "2 pistas, 3.0 m (borde!)": (2, 3.0, 0.8, 2.0),
    }
    print(f"{'caso':<34}{'max |dif| (min)':>18}{'veredicto':>14}")
    print("-" * 66)
    for caso, (pistas, ancho, alpha, beta) in casos.items():
        dem = rng.uniform(0, 400, n_celdas)
        orig = funcs["demora_auto_tramo"](
            largo_km / 2, dem, 31, ancho, 5, 2, largo_km, pistas, alpha, beta
        )
        act = car_actual(
            ubicacion_centro_km=largo_km / 2,
            demanda=dem,
            v_max_kmh=31,
            ancho_pista_m=ancho,
            largo_vehiculo_m=5,
            gap_m=2,
            L_ciudad_km=largo_km,
            num_pistas=pistas,
            alpha_bpr=alpha,
            beta_bpr=beta,
        )
        d = float(np.max(np.abs(orig[0] - act.t_usuarios_min)))
        print(f"{caso:<34}{d:>18.2e}{'IGUAL' if d < 1e-9 else 'DISTINTO':>14}")
    print(
        "\n>>> El unico caso distinto es ancho=3.0 m exacto: el original cae al\n"
        "    factor 0.75 (`3 < a`) y el actual aplica 0.9 (`a >= 3.0`), que es lo\n"
        "    que dice el Overleaf. Correccion deliberada."
    )


def anden(sup: SupplyConfig) -> None:
    """El factor de saturacion de anden tenia el signo invertido."""
    seccion("1b. METRO — factor de saturacion de anden")
    a = sup.train.anden_alpha
    print("original:  factor = 1 si rho<=1, else 0.5 * rho^4   (discontinuo)")
    print(f"actual:    factor = 1 + {a} * rho^4                   (BPR continua)\n")
    print(f"{'rho = carga/cap':>16}{'orig':>10}{'actual':>10}")
    print("-" * 36)
    for rho in (0.5, 0.9, 1.0, 1.0001, 1.05, 1.2, 1.5, 2.0):
        fo = 1.0 if rho <= 1 else 0.5 * rho**4
        print(f"{rho:>16.4f}{fo:>10.3f}{1.0 + a * rho**4:>10.3f}")
    print(
        "\n>>> En el original, al cruzar rho=1 el factor CAE de 1.000 a 0.500: la\n"
        "    espera se parte a la mitad justo al saturarse. Recien en\n"
        f"    rho={(1 / 0.5) ** 0.25:.3f} vuelve a superar 1. Salto discontinuo, "
        "y con el signo invertido."
    )


def detencion(sup: SupplyConfig) -> None:
    """El original no cobraba por detenerse: mas estaciones era gratis."""
    seccion("1c. METRO — tiempo de detencion en estaciones intermedias")
    dt = sup.train.tiempo_detencion_min
    v_t, largo_km, d_cbd = sup.train.v_tren_kmh, 20.0, 5.0
    print("original: t_viaje = distancia / v_tren            (sin costo por parar)")
    print(f"actual:   t_viaje = distancia / v_tren + paradas * {dt} min\n")
    print(f"Viajero a {d_cbd:.0f} km del CBD, ciudad de {largo_km:.0f} km:\n")
    print(f"{'n_estaciones':>13}{'t acceso':>10}{'t marcha':>10}{'t detencion':>13}{'TOTAL':>9}")
    print("-" * 55)
    for n_s in (4, 10, 20, 40, 80):
        d_est = largo_km / n_s
        acceso = (d_est / 4) / 4.8 * 60  # media de la distancia a la estacion
        marcha = d_cbd / v_t * 60
        det = max(int(d_cbd / d_est) - 1, 0) * dt
        print(f"{n_s:>13}{acceso:>10.2f}{marcha:>10.2f}{det:>13.2f}{acceso + marcha + det:>9.2f}")
    print(
        "\n>>> En el original la columna 'detencion' es 0 siempre: agregar estaciones\n"
        "    acortaba el acceso sin ningun costo. Optimo degenerado en n_s -> inf."
    )


# ------------------------------------------------------------------ 2. PARAMETROS

VST_SNI_2026 = 3338.0  # $/h, viaje urbano en vehiculo


def parametros(cfg_orig: dict) -> None:
    sim = base_sim()
    orig = cfg_orig["CONFIG_DEMANDA"]["estratos"]

    seccion("2a. VALOR SUBJETIVO DEL TIEMPO IMPLICITO  (b_tiempo / b_costo) x 60")
    print(f"Referencia: VST social SNI 2026 = ${VST_SNI_2026:,.0f}/h\n")
    print(f"{'estrato':<10}{'original $/h':>16}{'actual $/h':>14}{'orig / SNI':>13}")
    print("-" * 53)
    for h in (1, 2, 3):
        ob, nb = orig[h]["betas"], sim.demand.estratos[h].betas
        vo = ob["b_tiempo_viaje"] / ob["b_costo"] * 60
        vn = nb.b_tiempo_viaje / nb.b_costo * 60
        print(f"{h:<10}{vo:>16,.0f}{vn:>14,.0f}{vo / VST_SNI_2026:>12.1f}x")
    print(
        "\n>>> b_tiempo_viaje NO se movio en ningun estrato: toda la correccion se\n"
        "    hizo via b_costo, que reescala el VST sin tocar las razones de tiempo."
    )

    seccion("2b. PONDERADORES DE TIEMPO (relativos a b_tiempo_viaje)")
    print("Rango empirico habitual para la espera: 1.5 - 2.5\n")
    print(
        f"{'estrato':<10}{'espera orig':>13}{'espera act':>12}{'camin orig':>13}{'camin act':>12}"
    )
    print("-" * 60)
    for h in (1, 2, 3):
        ob, nb = orig[h]["betas"], sim.demand.estratos[h].betas
        bt_o, bt_n = ob["b_tiempo_viaje"], nb.b_tiempo_viaje
        print(
            f"{h:<10}{ob['b_tiempo_espera'] / bt_o:>13.2f}"
            f"{nb.b_tiempo_espera / bt_n:>12.2f}"
            f"{ob['b_tiempo_caminata'] / bt_o:>13.2f}"
            f"{nb.b_tiempo_caminata / bt_n:>12.2f}"
        )
    print(
        "\n>>> El original ponderaba la espera POR DEBAJO del tiempo en vehiculo\n"
        "    (0.73 en el estrato medio): un minuto en el anden molestaba menos que\n"
        "    un minuto viajando sentado. Contradice la literatura empirica."
    )

    seccion("2c. ASC EN MINUTOS DE VIAJE EQUIVALENTES  (asc / |b_tiempo_viaje|)")
    print(f"{'estrato':<9}{'modo':<14}{'original':>11}{'actual':>10}")
    print("-" * 44)
    for h in (1, 2, 3):
        ob = orig[h]["betas"]
        nb = sim.demand.estratos[h].betas.model_dump()
        bt = abs(ob["b_tiempo_viaje"])
        for m in ("asc_auto", "asc_metro", "asc_bici", "asc_caminata"):
            print(f"{h:<9}{m:<14}{ob[m] / bt:>11.1f}{nb[m] / bt:>10.1f}")


def defaults(cfg_orig: dict) -> None:
    seccion("2d. DEFAULTS DE OFERTA Y CIUDAD")
    sup = SupplyConfig()
    d_orig = cfg_orig["defaults"]
    # frec_min y tasa_carga van hardcodeados en la llamada a oferta_tren del
    # original (app.py:~499), no en el dict de defaults.
    filas = [
        ("capacidad_tren (pax)", d_orig["cap_tren"], sup.train.capacidad_tren),
        ("frec_min (tr/h)", 10, sup.train.frec_min),
        ("frec_max (tr/h)", d_orig["frec_max"], sup.train.frec_max),
        ("num_estaciones", d_orig["num_estaciones"], sup.train.num_estaciones),
        ("capacidad ciclovia", d_orig["cap_bici"], sup.bike.capacidad_pista),
        ("num_pistas", d_orig["num_pistas"], sup.car.num_pistas),
        ("costo_parking ($)", d_orig["parking"], base_sim().demand.globales.costo_parking),
        ("tarifa_metro ($)", d_orig["tarifa"], base_sim().demand.globales.costo_tarifa_metro),
        ("bencina ($/km)", d_orig["bencina"], base_sim().demand.globales.costo_combustible_km),
    ]
    print(f"{'parametro':<24}{'original':>12}{'actual':>12}")
    print("-" * 48)
    for nombre, o, n in filas:
        marca = "" if o == n else "   <--"
        print(f"{nombre:<24}{o:>12}{n:>12}{marca}")
    print(
        "\n>>> frec_min NO era configurable en el original: iba hardcodeado en la\n"
        "    llamada a oferta_tren(). Es el parametro que mas importa (ver 3b)."
    )


# --------------------------------------------------------------------- 3. IMPACTO


def _corre(sim) -> tuple[dict, float, float]:
    sim = sim.model_copy(update={"max_iter": 120, "tolerance": 0.02})
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, base_lu(), tr, localizacion="equilibrio"):
        pass
    ult = tr.iteraciones[-1]
    total = sum(ult.modal_split.values()) or 1
    reparto = {m: 100 * v / total for m, v in ult.modal_split.items()}
    return reparto, ult.frecuencia_metro, ult.frecuencia_teorica_metro


def _con_betas_del_original(cfg_orig: dict):
    """base_sim() con los betas del original. El original no separaba el acceso
    al metro, asi que b_tiempo_acceso toma el valor de b_tiempo_caminata."""
    sim = base_sim()
    orig = cfg_orig["CONFIG_DEMANDA"]["estratos"]
    est = dict(sim.demand.estratos)
    for h in (1, 2, 3):
        ob = orig[h]["betas"]
        est[h] = est[h].model_copy(
            update={
                "betas": est[h].betas.model_copy(
                    update={
                        "asc_auto": ob["asc_auto"],
                        "asc_metro": ob["asc_metro"],
                        "asc_bici": ob["asc_bici"],
                        "asc_caminata": ob["asc_caminata"],
                        "b_tiempo_viaje": ob["b_tiempo_viaje"],
                        "b_costo": ob["b_costo"],
                        "b_tiempo_espera": ob["b_tiempo_espera"],
                        "b_tiempo_acceso": ob["b_tiempo_caminata"],
                        "b_tiempo_caminata": ob["b_tiempo_caminata"],
                    }
                )
            }
        )
    return sim.model_copy(update={"demand": sim.demand.model_copy(update={"estratos": est})})


def _con_metro_del_original():
    sim = base_sim()
    return sim.model_copy(
        update={
            "supply": sim.supply.model_copy(
                update={
                    "train": sim.supply.train.model_copy(
                        update={"capacidad_tren": 1200, "frec_min": 10, "frec_max": 20}
                    )
                }
            )
        }
    )


def _con_parking_del_original():
    sim = base_sim()
    return sim.model_copy(
        update={
            "demand": sim.demand.model_copy(
                update={"globales": sim.demand.globales.model_copy(update={"costo_parking": 6000})}
            )
        }
    )


def impacto(cfg_orig: dict) -> None:
    seccion("3a. IMPACTO EN EL REPARTO MODAL")
    print("Motor ACTUAL con los parametros indicados del original, todo lo demas")
    print("fijo. Aisla el efecto de la calibracion del efecto del codigo.\n")
    escenarios = {
        "actual (calibracion 2026)": base_sim(),
        "betas del original": _con_betas_del_original(cfg_orig),
        "metro original (K=1200, fmin=10)": _con_metro_del_original(),
        "parking $6.000 (original)": _con_parking_del_original(),
    }
    print(f"{'escenario':<36}{'%auto':>8}{'%metro':>8}{'%bici':>8}{'%camin':>8}{'f_op':>7}")
    print("-" * 75)
    for etq, sim in escenarios.items():
        r, f_op, _ = _corre(sim)
        print(
            f"{etq:<36}{r.get('Auto', 0):>8.1f}{r.get('Metro', 0):>8.1f}"
            f"{r.get('Bici', 0):>8.1f}{r.get('Caminata', 0):>8.1f}{f_op:>7.1f}"
        )
    print(
        "\n>>> OJO con la fila del parking: el original tenia parking $6.000 PERO\n"
        "    tambien un b_costo ~6.6x mas chico en magnitud. Los dos cambios se\n"
        "    compensan en parte; esta fila NO representa al original."
    )

    seccion("3b. EL PISO DE FRECUENCIA MATA EL MECANISMO DE DOWNS-THOMSON")
    print("Si f_op != f_teorica, el piso esta mordiendo y la frecuencia DEJA de")
    print("responder a la demanda: sin ese canal no hay efecto Mohring.\n")
    print(f"{'escenario':<36}{'f_op':>8}{'f_teorica':>11}{'muerde?':>10}")
    print("-" * 65)
    for etq, sim in {
        "actual (frec_min=2)": base_sim(),
        "metro original (frec_min=10)": _con_metro_del_original(),
    }.items():
        _, f_op, f_teo = _corre(sim)
        print(
            f"{etq:<36}{f_op:>8.1f}{f_teo:>11.1f}{('SI' if abs(f_op - f_teo) > 0.05 else 'no'):>10}"
        )


# ------------------------------------------------------- 4. MODULO CIUDAD (SUELO)

# Parametros del bid-rent del original: los del default de la clase `Ciudad`,
# salvo `y`, que `app.py` sobreescribe al instanciarla (linea 458).
ALPHA_ORIG = np.array([1.3, 1.2, 1.1])
RHO_ORIG = np.array([1.0, 1.0, 1.0])
Y_ORIG = np.array([120.0, 50.0, 10.0])
L_ORIG = 1001  # n_celdas hardcodeado en app.py
LARGO_CIUDAD_KM = 20.0


def _solver_del_original():
    """Extrae `Ciudad.resolver_equilibrio_logit` y lo devuelve como funcion suelta.

    Se ata a un stub en vez de instanciar `Ciudad`, porque el `__init__` resuelve
    el equilibrio y asigna ~100.000 hogares de a uno."""
    ruta = ORIGINAL.parent / "Ciudad2.py"
    if not ruta.exists():
        sys.exit(f"Falta {ruta} (viene en el mismo clon que app.py).")
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == "Ciudad")
    metodo = next(
        n
        for n in clase.body
        if isinstance(n, ast.FunctionDef) and n.name == "resolver_equilibrio_logit"
    )
    mod = ast.Module(body=[metodo], type_ignores=[])
    ns: dict = {"np": np, "logsumexp": logsumexp}
    exec(compile(ast.fix_missing_locations(mod), "<original>", "exec"), ns)
    return ns["resolver_equilibrio_logit"]


def bidrent(resolver_orig) -> None:
    seccion("4a. BID-RENT — equivalencia del punto fijo")
    print("Umbral 1e-7: la tolerancia del propio solver es 1e-8, asi que las")
    print("diferencias de ese orden son ruido de convergencia.\n")

    rng = np.random.default_rng(7)
    n = 101
    cbd = n // 2
    H = np.array([2000.0, 5000.0, 3000.0])  # noqa: N806
    lam = np.ones(3)
    # sum(S) DEBE igualar sum(H): las columnas de Q suman 1 (toda parcela se
    # llena), asi que con capacidad != demanda la conservacion es imposible
    # por construccion, para cualquier solver.
    S = rng.integers(50, 200, n).astype(float)  # noqa: N806
    S *= H.sum() / S.sum()  # noqa: N806
    T = np.tile(np.abs(np.arange(n) - cbd).astype(float), (3, 1))  # noqa: N806

    stub = types.SimpleNamespace(T=T, S=S.copy(), H=H, y=Y_ORIG, L=n, u=None, p=None, Q=None)
    resolver_orig(stub, lam, ALPHA_ORIG, RHO_ORIG)
    res = solve_logit(
        H=H, S=S, y=Y_ORIG, T=T, alpha=ALPHA_ORIG, rho=RHO_ORIG, lambda_h=lam,
        beta=1.0, tol=1e-8, max_iter=10000, ancho_celda_km=1.0,
    )  # fmt: skip

    print(f"{'salida':<18}{'max |dif|':>14}{'veredicto':>12}")
    print("-" * 44)
    for nombre, a, b in [
        ("u (utilidad)", stub.u, res.u),
        ("p (precios)", stub.p, res.p),
        ("Q (composicion)", stub.Q, res.Q),
    ]:
        d = float(np.max(np.abs(np.asarray(a) - np.asarray(b))))
        print(f"{nombre:<18}{d:>14.3e}{'IGUAL' if d < 1e-7 else 'DISTINTO':>12}")
    print(
        "\n>>> El punto fijo es LA MISMA ecuacion. Lo que difiere es la Q final:\n"
        "    el original la arma con log(S_i) —constante por columna, se cancela\n"
        "    en la normalizacion— y omite log(H_h), que NO es constante. Ver D-25."
    )

    seccion("4b. BID-RENT — conservacion de hogares por estrato")
    print("sum_i S_i * Q[h,i] debe dar H_h: cada estrato coloca los suyos.\n")
    print(f"{'estrato':<9}{'H objetivo':>12}{'original':>13}{'core':>13}{'error orig':>13}")
    print("-" * 60)
    for h in range(3):
        co = float(np.sum(S * np.asarray(stub.Q)[h]))
        cc = float(np.sum(S * res.Q[h]))
        print(f"{h + 1:<9}{H[h]:>12,.0f}{co:>13,.1f}{cc:>13,.1f}{100 * (co - H[h]) / H[h]:>12.1f}%")
    print(
        "\n>>> El core conserva exacto. El original coloca un 52% mas de hogares\n"
        "    de estrato alto de los que le pediste, y un 31% menos de medios."
    )

    seccion("4c. BID-RENT — invarianza a la resolucion de la grilla")
    print(f"Misma ciudad fisica ({LARGO_CIUDAD_KM:.0f} km), distinto n_celdas. La composicion")
    print("no deberia depender de como discretizo.\n")
    # La sonda va a una distancia FISICA fija (2 km), no a un indice fijo: la
    # celda CBD+1 esta a dx km del centro, o sea a distinta distancia real
    # segun n_celdas, y comparar ahi seria comparar puntos distintos.
    d_sonda_km = 2.0
    print(f"Sonda: composicion del estrato alto a {d_sonda_km:.0f} km del CBD.\n")
    print(f"{'n_celdas':>10}{'Q[alto] orig':>16}{'Q[alto] core':>16}")
    print("-" * 42)
    for n_c in (51, 101, 201, 401):
        cbd_c = n_c // 2
        dx = LARGO_CIUDAD_KM / n_c
        S_c = np.full(n_c, H.sum() / n_c)  # noqa: N806
        T_celdas = np.tile(np.abs(np.arange(n_c) - cbd_c).astype(float), (3, 1))  # noqa: N806
        st = types.SimpleNamespace(
            T=T_celdas, S=S_c.copy(), H=H, y=Y_ORIG, L=n_c, u=None, p=None, Q=None
        )
        resolver_orig(st, lam, ALPHA_ORIG, RHO_ORIG)
        T_min = np.tile(np.abs(np.arange(n_c) - cbd_c) * dx / V_REF_KMH * 60.0, (3, 1))  # noqa: N806
        r = solve_logit(
            H=H, S=S_c, y=Y_ORIG, T=T_min, alpha=ALPHA_ORIG, rho=RHO_ORIG, lambda_h=lam,
            beta=1.0, tol=1e-8, max_iter=10000, ancho_celda_km=dx,
        )  # fmt: skip
        i_sonda = cbd_c + max(1, round(d_sonda_km / dx))
        print(f"{n_c:>10}{np.asarray(st.Q)[0, i_sonda]:>16.4f}{r.Q[0, i_sonda]:>16.4f}")
    print(
        "\n>>> Al refinar 8x la grilla el original DERIVA un +32% y el core se mueve\n"
        "    un -0.5% (invariante salvo discretizacion). Causa: en el original T va\n"
        "    en INDICES DE CELDA y S en hogares/CELDA, ambas dependientes de dx, asi\n"
        "    que n_celdas reescala en silencio alpha y rho. El core usa minutos y\n"
        "    hogares/km (D-26). Consecuencia practica: en el original, comparar dos\n"
        "    corridas con distinta discretizacion es comparar dos calibraciones."
    )


def suelo_parametros() -> None:
    seccion("4d. PARAMETROS DEL BID-RENT — el problema de unidades")
    dx_orig = LARGO_CIUDAD_KM / L_ORIG
    k_alpha = V_REF_KMH / (60 * dx_orig)  # T[celdas] = T[min] * k_alpha
    k_rho = dx_orig  # S[hogares/celda] = dens[hogares/km] * k_rho
    print("Los numeros crudos NO son comparables: cambiaron las unidades.")
    print(f"  original: alpha x T[celdas], rho x S[hogares/celda]  (dx={dx_orig:.5f} km)")
    print("  core:     alpha x T[min],    rho x dens[hogares/km]")
    print(f"  factores: alpha x{k_alpha:.2f},  rho x{k_rho:.5f}\n")
    cfg_actual = LandUseConfig().estratos
    print(f"{'':<11}{'orig crudo':>12}{'orig convertido':>18}{'actual':>10}{'razon':>9}")
    print("-" * 62)
    for h in range(3):
        a_eq = ALPHA_ORIG[h] * k_alpha
        print(
            f"{'alpha h' + str(h + 1):<11}{ALPHA_ORIG[h]:>12.2f}{a_eq:>18.2f}"
            f"{cfg_actual[h].alpha:>10.2f}{cfg_actual[h].alpha / a_eq:>8.2f}x"
        )
    print()
    for h in range(3):
        r_eq = RHO_ORIG[h] * k_rho
        print(
            f"{'rho h' + str(h + 1):<11}{RHO_ORIG[h]:>12.2f}{r_eq:>18.4f}"
            f"{cfg_actual[h].rho:>10.2f}{cfg_actual[h].rho / r_eq:>8.2f}x"
        )
    print(
        "\n>>> Leer 'alpha 1.3 -> 6.5' como un aumento INVIERTE el signo del cambio:\n"
        "    en unidades comparables el original pesaba el tiempo 5x MAS (32.5\n"
        "    utiles/min vs 6.5). El castigo a la densidad se movio al reves (5x mas\n"
        "    hoy). Ojo: como alpha_efectivo dependia de dx, cambiar n_celdas movia\n"
        "    la calibracion sin que nadie lo escribiera."
    )


def suelo_impacto() -> None:
    seccion("4e. IMPACTO — donde vive cada estrato")
    print("Motor ACTUAL, unidades fijas; solo cambian alpha/rho/y (los del")
    print("original, convertidos). Aisla la calibracion del codigo.\n")
    n, cbd = 201, 100
    dx = LARGO_CIUDAD_KM / n
    H = (7200, 18000, 10800)  # noqa: N806
    dx_orig = LARGO_CIUDAD_KM / L_ORIG
    k_alpha, k_rho = V_REF_KMH / (60 * dx_orig), dx_orig

    cfgs = {
        "actual": LandUseConfig(H_por_estrato=H),
        "original (convertido)": LandUseConfig(
            H_por_estrato=H,
            estratos=tuple(
                LandUseStratumConfig(
                    y=Y_ORIG[h], alpha=ALPHA_ORIG[h] * k_alpha, rho=RHO_ORIG[h] * k_rho
                )
                for h in range(3)
            ),
        ),
    }
    print(f"{'calibracion':<24}{'estrato':<8}{'d media (km)':>14}{'% a <2 km':>12}")
    print("-" * 58)
    for etq, cfg in cfgs.items():
        ciudad = LandUseCity.build(L=n, CBD=cbd, cfg=cfg, ancho_celda_km=dx)
        q_mat = ciudad.result.Q
        cap = np.asarray(ciudad.S, dtype=float)
        d = np.abs(np.arange(n) - cbd) * dx
        for h, nombre in enumerate(("alto", "medio", "bajo")):
            hog = cap * q_mat[h]
            tot = max(float(hog.sum()), 1e-9)
            d_media = float((hog * d).sum()) / tot
            cerca = 100 * float(hog[d <= 2.0].sum()) / tot
            print(f"{etq if h == 0 else '':<24}{nombre:<8}{d_media:>14.2f}{cerca:>11.1f}%")
    print(
        "\n>>> El ordenamiento cualitativo es el MISMO (ricos al centro, pobres a la\n"
        "    periferia): eso lo da la estructura, no la calibracion. Lo que cambia\n"
        "    es la intensidad — el original concentra al estrato alto casi por\n"
        "    completo dentro de 2 km."
    )


def main() -> None:
    constantes, funcs = _cargar_original()
    print(f"Original leido desde: {ORIGINAL}")
    equivalencia_auto(funcs)
    anden(SupplyConfig())
    detencion(SupplyConfig())
    parametros(constantes)
    defaults(constantes)
    impacto(constantes)
    bidrent(_solver_del_original())
    suelo_parametros()
    suelo_impacto()


if __name__ == "__main__":
    main()
