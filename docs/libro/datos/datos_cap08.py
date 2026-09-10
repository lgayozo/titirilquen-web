"""Datos del capítulo 8 — Contrato y runtimes.

Produce `cap08.json`. Este capítulo no audita una ecuación sino una promesa:
que el mismo núcleo, corrido en el servidor (FastAPI) y en el navegador
(Pyodide), dé el mismo número, y que lo que el frontend cree del núcleo
—tipos, defaults, presets— sea lo que el núcleo es.

La pieza menos vigilada es el bloque de Python que vive como STRING dentro de
`pyodide.worker.ts`: ni ruff, ni pytest, ni el typecheck lo ven, y el único test
que lo ejecuta (`simulation.spec.ts`, @slow) comprueba que el motor arranca, no
qué calcula. Acá se extrae ese bloque, se ejecuta en CPython contra el núcleo
instalado y se compara, entrada por entrada, con lo que hace la API.

Nueve bloques:

1. `wheel_al_dia` — ¿el wheel commiteado corresponde al núcleo commiteado?
2. `paridad_worker_api` — las cuatro entradas del worker contra la API.
3. `c02` — cuánto difieren los dos motores en el estado por defecto del Sandbox.
4. `defaults` — golden del núcleo + `overrides.ts` contra lo que la línea base
   dice que corre la aplicación.
5. `outer_max_iter` — los cuatro defaults de un mismo parámetro y lo que pasa
   cuando el de la interfaz llega a la API.
6. `payload` — cuántos bytes cruzan la frontera por corrida, y quién los lee.
7. `campos_sin_lector` — campos del contrato que ningún archivo del frontend
   nombra.
8. `determinismo` — el suelo standalone sin semilla y la vuelta 0 del acoplado.
9. `pines` — versiones fijadas a mano en más de un lugar, goldens y contrato.

Correr desde `packages/titirilquen_core` (~30 s):

    uv run python ../../docs/libro/datos/datos_cap08.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import fields as dc_fields
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
NUCLEO = RAIZ / "packages" / "titirilquen_core"
WEB = RAIZ / "apps" / "web"
API = RAIZ / "apps" / "api"
sys.path.insert(0, str(NUCLEO / "tests"))

import test_linea_base as base
from titirilquen_core.bienestar import AgregadosDict
from titirilquen_core.city import CiudadLineal
from titirilquen_core.coupled import iter_coupled
from titirilquen_core.coupled_metrics import StratumMetrics, SystemMetrics
from titirilquen_core.equilibrium.msa import (
    ConvergenceTrace,
    iter_msa_desde_suelo,
    run_msa,
)
from titirilquen_core.land_use.accesibilidad import T_flujo_libre
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.serializacion import (
    AgenteDict,
    CoupledResultDict,
    LandUseResultDict,
    LandUseSolveDict,
    OuterIterationDict,
    SnapshotDict,
    TraceDict,
    land_use_city_to_dict,
    outer_iteration_to_dict,
    trace_to_dict,
)

SALIDA = Path(__file__).parent / "cap08.json"
WORKER = WEB / "src" / "workers" / "pyodide.worker.ts"
WHEEL_DIR = WEB / "public" / "pyodide"
STORE = WEB / "src" / "store" / "landUseStore.ts"


def _commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "desconocido"


def _json_igual(a, b, tol: float = 1e-12) -> bool:
    """Igualdad de dos objetos JSON con tolerancia en los flotantes."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_json_igual(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            _json_igual(x, y, tol) for x, y in zip(a, b, strict=True)
        )
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a is b
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(a)))
    return a == b


def _claves_distintas(a, b, prefijo: str = "") -> list[str]:
    """Rutas donde dos objetos JSON difieren (para diagnosticar, no para pasar)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{prefijo}{k} (sólo en un lado)")
            else:
                out += _claves_distintas(a[k], b[k], f"{prefijo}{k}.")
        return out
    return [] if _json_igual(a, b) else [prefijo.rstrip(".")]


def _fuente_web_sin_strings() -> str:
    """El código TS del frontend (fuera de `lib/gen/`) con las claves i18n
    vaciadas: un nombre de campo que sólo aparezca dentro de
    `t("flowchart.coupled.transport")` no es un lector. Se vacía SÓLO el
    primer argumento de `t(...)`: vaciar todo literal de string rompe con el
    primer apóstrofo de un comentario y se lleva medio archivo."""
    partes = [
        p.read_text(encoding="utf-8")
        for p in (WEB / "src").rglob("*.ts*")
        if "/gen/" not in str(p)
    ]
    texto = "\n".join(partes)
    return re.sub(r'\bt\(\s*(["\'`])(?:(?!\1).)*\1', 't("")', texto)


def _ui_outer_max_iter() -> int:
    m = re.search(r"coupledOuterMaxIter:\s*(\d+),", STORE.read_text(encoding="utf-8"))
    assert m
    return int(m.group(1))


# ---------------------------------------------------------------------------
# 1. El wheel
# ---------------------------------------------------------------------------


def _record(wheel: Path) -> dict[str, str]:
    with zipfile.ZipFile(wheel) as z:
        nombre = next(n for n in z.namelist() if n.endswith(".dist-info/RECORD"))
        lineas = z.read(nombre).decode().splitlines()
    out = {}
    for ln in lineas:
        partes = ln.split(",")
        if len(partes) >= 2 and partes[1]:
            out[partes[0]] = partes[1]
    return out


def wheel_al_dia() -> dict:
    """Se recompila el núcleo a un directorio temporal y se comparan los hashes
    de `RECORD` contra el wheel que sirve el frontend. Es lo que hace el job
    `contrato` del CI, sin depender de que el CI corra."""
    commiteado = next(WHEEL_DIR.glob("*.whl"))
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", tmp],
            cwd=NUCLEO,
            capture_output=True,
            check=True,
        )
        nuevo = next(Path(tmp).glob("*.whl"))
        r_new = _record(nuevo)
    r_old = _record(commiteado)
    difieren = sorted(
        k for k in set(r_old) | set(r_new) if r_old.get(k) != r_new.get(k)
    )
    return {
        "wheel_servido": commiteado.name,
        "archivos_en_el_wheel": len(r_old),
        "archivos_con_hash_distinto": difieren,
        "al_dia": not difieren,
    }


# ---------------------------------------------------------------------------
# 2. La paridad worker ↔ API
# ---------------------------------------------------------------------------


def _pegamento_del_worker() -> dict:
    """Extrae el bloque Python embebido en el worker y lo ejecuta en CPython.

    Se quitan sólo las dos líneas de `micropip` (instalan paquetes en el
    navegador); el resto corre tal cual contra el núcleo instalado en el venv.
    """
    src = WORKER.read_text(encoding="utf-8")
    m = re.search(r"runPythonAsync\(`(.*?)`\)", src, re.DOTALL)
    assert m, "no se encontró el bloque runPythonAsync en el worker"
    bloque = "\n".join(
        ln
        for ln in m.group(1).splitlines()
        if not ln.strip().startswith(("import micropip", "await micropip"))
    )
    ns: dict = {}
    exec(compile(bloque, "<pyodide.worker.ts>", "exec"), ns)  # noqa: S102
    return {"lineas": len(bloque.splitlines()), "ns": ns}


def paridad_worker_api() -> dict:
    sim = base._config_web()
    lu = base._land_use_web()
    peg = _pegamento_del_worker()
    ns = peg["ns"]
    cfg_json = sim.model_dump_json()
    ciudad = CiudadLineal(
        n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km
    )
    dx = ciudad.ancho_celda_km
    L, CBD = sim.city.n_celdas, ciudad.cbd_index
    out: dict = {"lineas_de_python_en_el_worker": peg["lineas"], "entradas": {}}

    # (a) /simulate ≡ iter_from_json_suelo + last_trace_to_py. Desde sep-2026
    # el endpoint recibe el uso de suelo (C-02 cerrado); el worker nunca tuvo
    # otra entrada viva, así que la comparación es entre las dos rutas reales.
    lu_json = json.loads(lu.model_dump_json(by_alias=True))
    for _ in ns["iter_from_json_suelo"](
        json.dumps(
            {
                "config": json.loads(cfg_json),
                "land_use": lu_json,
                "localizacion": "equilibrio",
            }
        )
    ):
        pass
    w = ns["last_trace_to_py"]()
    a = trace_to_dict(run_msa(sim, lu, "equilibrio"), sim)
    out["entradas"]["simulateStream"] = {
        "api": "/simulate",
        "iguales": _json_igual(w, a),
        "claves_distintas": _claves_distintas(w, a)[:10],
    }

    # (b) land_use_solve_from_json ≡ /land-use/solve (salvo `parcelas`: rng)
    req = {
        "L": L,
        "CBD": CBD,
        "largo_km": sim.city.largo_ciudad_km,
        "land_use": lu_json,
        "demand": json.loads(sim.demand.model_dump_json()),
        "supply": json.loads(sim.supply.model_dump_json()),
        "modos_habilitados": None,
    }
    w = ns["land_use_solve_from_json"](json.dumps(req))
    T = T_flujo_libre(sim.demand, L, CBD, dx, None, supply=sim.supply)
    a = land_use_city_to_dict(
        LandUseCity.build(L=L, CBD=CBD, cfg=lu, ancho_celda_km=dx, T=T)
    )
    w_sin, a_sin = dict(w), dict(a)
    w_sin.pop("parcelas")
    a_sin.pop("parcelas")
    out["entradas"]["landUseSolve"] = {
        "api": "/land-use/solve",
        "iguales_salvo_parcelas": _json_igual(w_sin, a_sin),
        "parcelas_iguales": w["parcelas"] == a["parcelas"],
        "claves_distintas": _claves_distintas(w_sin, a_sin)[:10],
    }

    # (c) coupled_iter_from_json ≡ /coupled/stream
    req_c = {
        "sim": json.loads(cfg_json),
        "land_use": lu_json,
        "outer_max_iter": 2,
        "outer_tol": 1.0,
    }
    w_iters = [
        json.loads(json.dumps(x))
        for x in ns["coupled_iter_from_json"](json.dumps(req_c))
    ]
    a_iters = [
        json.loads(json.dumps(outer_iteration_to_dict(o)))
        for o in iter_coupled(
            sim=sim, land_use_config=lu, outer_max_iter=2, outer_tol=1.0
        )
    ]
    out["entradas"]["coupledStream"] = {
        "api": "/coupled/stream",
        "vueltas": len(w_iters),
        "iguales": len(w_iters) == len(a_iters)
        and all(_json_igual(x, y) for x, y in zip(w_iters, a_iters, strict=True)),
        "claves_distintas": (
            _claves_distintas(w_iters[-1], a_iters[-1])[:10]
            if w_iters and a_iters
            else []
        ),
    }

    return out


# ---------------------------------------------------------------------------
# 3. C-02
# ---------------------------------------------------------------------------


def c02() -> dict:
    """C-02, cerrado el 2026-09-10: el Sandbox con motor api corría `/simulate`
    con densidad plana y con motor local `iter_msa_desde_suelo`; medido en el
    cap. 8 original, 9,15 pp de metro entre motores. Hoy `/simulate` recibe el
    uso de suelo y las dos rutas son la misma función: se mide que lo sean."""
    sim = base._config_web()
    lu = base._land_use_web()

    def pct(tr):
        s = tr.iteraciones[-1].modal_split
        t = sum(s.values())
        return {k: round(100.0 * v / t, 3) for k, v in s.items()}

    api = run_msa(sim, lu, "original")
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu, tr, localizacion="original"):
        pass
    p, o = pct(api), pct(tr)
    return {
        "motor_api_run_msa": {"reparto_pct": p, "agentes": len(api.agentes)},
        "motor_local_iter_msa_desde_suelo": {
            "reparto_pct": o,
            "agentes": len(tr.agentes),
        },
        "diferencia_maxima_pp": round(max(abs(o[k] - p[k]) for k in o), 3),
        "diferencia_agentes": len(tr.agentes) - len(api.agentes),
        "historia": "antes del cierre: 9,151 pp de metro y 179 agentes de diferencia",
    }


# ---------------------------------------------------------------------------
# 4. Defaults
# ---------------------------------------------------------------------------


def defaults() -> dict:
    """Golden del núcleo + `overrides.ts` ≟ `test_linea_base._config_web()`.

    El golden lo escribe el núcleo; los overrides se leen del archivo TS con
    expresiones regulares (son cinco números y una palabra). Si la suma no da la
    configuración que la línea base dice que corre la aplicación, uno de los
    tres está mintiendo.
    """
    golden = json.loads(
        (WEB / "e2e" / "fixtures" / "defaults-golden.json").read_text(encoding="utf-8")
    )["defaults"]
    ov = (WEB / "src" / "lib" / "overrides.ts").read_text(encoding="utf-8")

    def cap(pat: str) -> str:
        m = re.search(pat, ov)
        assert m, pat
        return m.group(1)

    n_celdas = int(cap(r"n_celdas:\s*(\d+)"))
    seed = int(cap(r"seed:\s*(\d+)"))
    assignment = cap(r'assignment:\s*"(\w+)"')
    poblacion = int(cap(r"POBLACION_BASE\s*=\s*([\d_]+)").replace("_", ""))
    shares = [float(x) for x in cap(r"SHARES\s*=\s*\[([^\]]+)\]").split(",")]
    lu_max_iter = int(cap(r"max_iter:\s*(\d+)"))

    app = {
        "city": {**golden["city"], "n_celdas": n_celdas},
        "supply": golden["supply"],
        "sim": {**golden["sim"], "seed": seed, "assignment": assignment},
        "land_use": {
            **golden["land_use"],
            "H_por_estrato": [round(poblacion * s) for s in shares],
            "max_iter": lu_max_iter,
        },
    }
    web = base._config_web()
    lu = base._land_use_web()
    campos_sim = ("max_iter", "tolerance", "seed", "assignment", "modos_habilitados")
    linea_base = {
        "city": web.city.model_dump(),
        "supply": web.supply.model_dump(),
        "sim": {k: getattr(web, k) for k in campos_sim},
        "land_use": lu.model_dump(by_alias=True),
    }
    app_n = json.loads(json.dumps(app, default=list))
    lb_n = json.loads(json.dumps(linea_base, default=list))
    return {
        "overrides_encontrados": {
            "n_celdas": n_celdas,
            "seed": seed,
            "assignment": assignment,
            "H_por_estrato": app["land_use"]["H_por_estrato"],
            "land_use.max_iter": lu_max_iter,
        },
        "overrides_que_declara_el_docstring": 5 if "cinco diferencias" in ov else None,
        "overrides_contados": 5,
        "golden_mas_overrides_igual_a_linea_base": _json_igual(app_n, lb_n),
        "claves_distintas": _claves_distintas(app_n, lb_n),
        "nota": (
            "`estratos: ESTRATOS_CALIBRADOS` no es un override: `DemandConfig` no "
            "tiene default para `estratos`, así que el frontend RELLENA un campo "
            "obligatorio, no lo cambia."
        ),
    }


# ---------------------------------------------------------------------------
# 5. outer_max_iter
# ---------------------------------------------------------------------------


def outer_max_iter() -> dict:
    """Un parámetro, cuatro defaults, y una cota en la API que el default de la
    interfaz no cumple."""
    core_src = (NUCLEO / "src" / "titirilquen_core" / "coupled.py").read_text(
        encoding="utf-8"
    )
    core = re.search(r"outer_max_iter:\s*int\s*=\s*(\d+)", core_src)
    api_src = (API / "src" / "api" / "main.py").read_text(encoding="utf-8")
    api = re.search(
        r"outer_max_iter:\s*int\s*=\s*Field\(default=(\d+),\s*ge=(\d+),\s*le=(\d+)\)",
        api_src,
    )
    worker = re.search(
        r'req\.get\("outer_max_iter",\s*(\d+)\)', WORKER.read_text(encoding="utf-8")
    )
    assert core and api and worker
    ui = _ui_outer_max_iter()
    # Lo que responde la API cuando llega el default de la interfaz. Corre en el
    # venv de la API (FastAPI no está en el del núcleo).
    sonda = (
        "from fastapi.testclient import TestClient\n"
        "from titirilquen_core.presets import DEFAULT_STRATA\n"
        "from api.main import app\n"
        "c=TestClient(app)\n"
        "base={'sim':{'city':{'n_celdas':51,'largo_ciudad_km':5},"
        "'demand':{'estratos':DEFAULT_STRATA},'max_iter':2,'seed':1},"
        "'land_use':{'H_por_estrato':[50,100,100],'max_iter':500}}\n"
        f"for n in ({api.group(3)}, {ui}):\n"
        "    r=c.post('/coupled/solve', json={**base,'outer_max_iter':n,'outer_tol':1.0})\n"
        "    print(n, r.status_code)\n"
    )
    res = subprocess.run(
        ["uv", "run", "python", "-c", sonda],
        cwd=API,
        capture_output=True,
        text=True,
        check=True,
    )
    codigos = {}
    for ln in res.stdout.strip().splitlines():
        if ln.strip():
            n, code = ln.split()
            codigos[n] = int(code)
    return {
        "defaults": {
            "nucleo (coupled.py)": int(core.group(1)),
            "api (main.py)": int(api.group(1)),
            "worker (pyodide.worker.ts)": int(worker.group(1)),
            "interfaz (landUseStore.ts)": ui,
        },
        "cota_superior_de_la_api": int(api.group(3)),
        "respuesta_de_la_api": codigos,
        "la_interfaz_pasa_por_la_api": codigos.get(str(ui)) == 200,
    }


# ---------------------------------------------------------------------------
# 6. Payload
# ---------------------------------------------------------------------------


def payload() -> dict:
    sim = base._config_web()
    lu = base._land_use_web()
    tr = ConvergenceTrace()
    for _ in iter_msa_desde_suelo(sim, lu, tr, localizacion="original"):
        pass
    d = trace_to_dict(tr, sim)
    total = len(json.dumps(d))
    por_clave = {k: len(json.dumps(v)) for k, v in d.items()}
    it0 = next(
        iter(iter_coupled(sim=sim, land_use_config=lu, outer_max_iter=1, outer_tol=1.0))
    )
    od = outer_iteration_to_dict(it0)
    o_total = len(json.dumps(od))
    o_por_clave = {k: len(json.dumps(v)) for k, v in od.items()}
    ui = _ui_outer_max_iter()
    src_web = _fuente_web_sin_strings()
    lee = {k: len(re.findall(rf"\.{re.escape(k)}\b", src_web)) for k in od}
    top_trace = sorted(por_clave.items(), key=lambda x: -x[1])[:5]
    top_outer = sorted(o_por_clave.items(), key=lambda x: -x[1])
    return {
        "trace_to_dict_bytes": total,
        "trace_agentes": len(d["agentes"]),
        "trace_por_clave_pct": {k: round(100.0 * v / total, 2) for k, v in top_trace},
        "outer_iteration_bytes": o_total,
        "outer_por_clave_pct": {k: round(100.0 * v / o_total, 2) for k, v in top_outer},
        "referencias_en_el_frontend_por_campo_de_outer": lee,
        "mb_por_corrida_acoplada_al_maximo_de_la_ui": round(o_total * ui / 1e6, 1),
        "mb_que_el_frontend_abre_de_eso": round(
            sum(v for k, v in o_por_clave.items() if lee.get(k, 0) > 0) * ui / 1e6, 2
        ),
    }


# ---------------------------------------------------------------------------
# 7. Campos sin lector
# ---------------------------------------------------------------------------


def campos_sin_lector() -> dict:
    """Cada campo del contrato, contra los archivos del frontend (fuera de
    `lib/gen/`). Los nombres de una o dos letras no se pueden buscar con
    confianza y se declaran aparte."""
    src = _fuente_web_sin_strings()
    formas = {
        "TraceDict": list(TraceDict.__annotations__),
        "SnapshotDict": list(SnapshotDict.__annotations__),
        "AgenteDict": list(AgenteDict.__annotations__),
        "LandUseSolveDict": list(LandUseSolveDict.__annotations__),
        "LandUseResultDict": list(LandUseResultDict.__annotations__),
        "OuterIterationDict": list(OuterIterationDict.__annotations__),
        "CoupledResultDict": list(CoupledResultDict.__annotations__),
        "AgregadosDict": list(AgregadosDict.__annotations__),
        "StratumMetrics": [f.name for f in dc_fields(StratumMetrics)],
        "SystemMetrics": [f.name for f in dc_fields(SystemMetrics)],
    }
    sin_lector: dict[str, list[str]] = {}
    cortos: dict[str, list[str]] = {}
    total = 0
    for forma, campos in formas.items():
        for c in campos:
            total += 1
            if len(c) <= 2:
                cortos.setdefault(forma, []).append(c)
                continue
            if not re.search(rf"\b{re.escape(c)}\b", src):
                sin_lector.setdefault(forma, []).append(c)
    return {
        "campos_totales": total,
        "sin_lector": sin_lector,
        "no_verificables_por_grep": cortos,
        "cantidad_sin_lector": sum(len(v) for v in sin_lector.values()),
    }


# ---------------------------------------------------------------------------
# 8. Determinismo
# ---------------------------------------------------------------------------


def determinismo() -> dict:
    sim = base._config_web()
    lu = base._land_use_web()
    ciudad = CiudadLineal(
        n_celdas=sim.city.n_celdas, largo_total_km=sim.city.largo_ciudad_km
    )
    dx, c, L = ciudad.ancho_celda_km, ciudad.cbd_index, sim.city.n_celdas
    T = T_flujo_libre(sim.demand, L, c, dx, supply=sim.supply)
    a = LandUseCity.build(L=L, CBD=c, cfg=lu, T=T, ancho_celda_km=dx)
    b = LandUseCity.build(L=L, CBD=c, cfg=lu, T=T, ancho_celda_km=dx)
    assert a.result is not None and b.result is not None
    it0 = next(
        iter(iter_coupled(sim=sim, land_use_config=lu, outer_max_iter=1, outer_tol=1.0))
    )
    return {
        "standalone_dos_corridas": {
            "Q_iguales": bool(np.array_equal(a.result.Q, b.result.Q)),
            "parcelas_iguales": a.parcelas == b.parcelas,
            "nota": (
                "`/land-use/solve` y el worker construyen la ciudad sin `rng`: la "
                "asignación entera se sortea distinto cada vez; `Q`, `p`, Theil y "
                "distancias son deterministas."
            ),
        },
        "acoplado_vuelta_0_vs_standalone": {
            "max_dQ": float(np.max(np.abs(it0.land_use.Q - a.result.Q))),
            "nota": "La página de suelo y la vuelta 0 del acoplado resuelven la MISMA ciudad.",
        },
    }


# ---------------------------------------------------------------------------
# 9. Pines, goldens y contrato
# ---------------------------------------------------------------------------


def pines() -> dict:
    py = (NUCLEO / "pyproject.toml").read_text(encoding="utf-8")
    wk = WORKER.read_text(encoding="utf-8")
    ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    def cap(pat: str, texto: str, flags: int = 0) -> str:
        m = re.search(pat, texto, flags)
        assert m, pat
        return m.group(1)

    version = cap(r'^version\s*=\s*"([^"]+)"', py, re.MULTILINE)
    wheel_en_worker = cap(r"titirilquen_core-([\d.]+)-py3-none-any\.whl", wk)
    pyodide = cap(r'PYODIDE_VERSION\s*=\s*"([^"]+)"', wk)
    pydantic = cap(r'"pydantic(>=[^"]*)"', py)
    ramas = cap(r"push:\s*\n\s*branches:\s*\[([^\]]+)\]", ci)
    jobs = re.findall(r"^\s{4}name:\s*(.+)$", ci, re.MULTILINE)
    fixtures = WEB / "e2e" / "fixtures"
    goldens = {}
    for f in sorted(fixtures.glob("*-golden.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if "cases" in d:
            goldens[f.name] = len(d["cases"])
    gen = sorted((WEB / "src" / "lib" / "gen").glob("*.gen.ts"))
    return {
        "goldens_casos": goldens,
        "contrato_generado": {
            "archivos": [g.name for g in gen],
            "lineas": sum(len(g.read_text(encoding="utf-8").splitlines()) for g in gen),
            "interfaces": sum(
                len(
                    re.findall(
                        r"^export (?:interface|type) ",
                        g.read_text(encoding="utf-8"),
                        re.MULTILINE,
                    )
                )
                for g in gen
            ),
        },
        "version_del_nucleo": version,
        "wheel_que_pide_el_worker": wheel_en_worker,
        "coinciden": version == wheel_en_worker,
        "pyodide": pyodide,
        "piso_pydantic": pydantic.strip(),
        "ci_dispara_en_push_a": [r.strip() for r in ramas.split(",")],
        "ci_jobs": jobs,
    }


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap08.py",
            "configuracion": (
                "La de la aplicación (`test_linea_base._config_web` y `_land_use_web`). "
                "El bloque Python del worker se extrae de `pyodide.worker.ts` y se "
                "ejecuta en CPython sin las dos líneas de micropip; la sonda de la API "
                "corre en el venv de `apps/api` con `TestClient`."
            ),
        },
        "wheel_al_dia": wheel_al_dia(),
        "paridad_worker_api": paridad_worker_api(),
        "c02": c02(),
        "defaults": defaults(),
        "outer_max_iter": outer_max_iter(),
        "payload": payload(),
        "campos_sin_lector": campos_sin_lector(),
        "determinismo": determinismo(),
        "pines": pines(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    w = datos["wheel_al_dia"]
    estado = (
        "al día"
        if w["al_dia"]
        else "DESFASADO: " + ", ".join(w["archivos_con_hash_distinto"])
    )
    print(f"Wheel {w['wheel_servido']}: {estado}")
    print("\nParidad worker ↔ API:")
    for k, v in datos["paridad_worker_api"]["entradas"].items():
        print(f"  {k:<26} {v}")
    c = datos["c02"]
    print(
        "\nC-02 (cerrado): diferencia entre motores "
        f"{c['diferencia_maxima_pp']} pp · {c['diferencia_agentes']} agentes"
    )
    d = datos["defaults"]
    print(
        f"\nDefaults: golden + overrides == línea base: "
        f"{d['golden_mas_overrides_igual_a_linea_base']} {d['claves_distintas']}"
    )
    o = datos["outer_max_iter"]
    print(
        f"\nouter_max_iter: {o['defaults']} · API responde {o['respuesta_de_la_api']}"
    )
    p = datos["payload"]
    print(
        f"\nPayload: trace {p['trace_to_dict_bytes'] / 1e6:.2f} MB ({p['trace_agentes']} agentes) · "
        f"outer {p['outer_iteration_bytes'] / 1e6:.2f} MB · por corrida acoplada "
        f"{p['mb_por_corrida_acoplada_al_maximo_de_la_ui']} MB, de los que el frontend abre "
        f"{p['mb_que_el_frontend_abre_de_eso']} MB"
    )
    print(
        f"  campos de OuterIteration referenciados: {p['referencias_en_el_frontend_por_campo_de_outer']}"
    )
    s = datos["campos_sin_lector"]
    print(
        f"\nCampos sin lector: {s['cantidad_sin_lector']} de {s['campos_totales']}: {s['sin_lector']}"
    )
    print(f"\nPines: {datos['pines']}")
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
