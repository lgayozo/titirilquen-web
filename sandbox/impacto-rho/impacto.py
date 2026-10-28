"""Que hace rho en la subasta de suelo, y en que rango la asignacion es realista.

    uv run python impacto.py

Ejecuta el plan de `PLAN.md` (E0-E8) y escribe `salida/*.json`. Ninguna cifra
del informe sale de otro lado.

**La tesis que se pone a prueba.** La puja es `y_h + f_h/lambda_h` con
`f_h = -alpha_h*T - rho_h*dens`. Como `dens` es exogena (D-32) y en las formas
monocentricas casi proporcional a `T` (AU-12), la parte que interactua
estrato x parcela colapsa en un solo coeficiente por estrato:

    kappa_h = (alpha_h - b*rho_h) / lambda_h

y gana el centro quien tenga mayor kappa. De ahi: rho no tiene un "rango
correcto" propio; lo que esta identificado por la localizacion es kappa. El
nivel de rho se ve en los PRECIOS, no en el mapa.

**Los dos regimenes.** Todo se corre dos veces:

* R0 -- la calibracion vigente: alpha = (6,5 6,0 5,5), lambda = 1, rho = 0,0025.
  Rama cerrada (logit).
* R1 -- la propuesta: alpha = 6,0 uniforme, lambda_h ~ 1/y_h (e_t = 1, que es
  `SVTTS = w` de Jara-Diaz ec. 2.25), rho parametrizada por la brecha de
  elasticidades. Rama HEV.

**Desviacion del plan.** El plan decia usar la ciudad de la auditoria (shares
10/40/50). Se usa la de la APP (7.200/18.000/10.800, shares 20/50/30, misma
SumaH = 36.000) para que E6 conecte directo con la linea base pineada sin
cambiar de ciudad a mitad del analisis.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from titirilquen_core.land_use.ciudad import LandUseCity, _default_T
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig

SALIDA = Path(__file__).parent / "salida"
SALIDA.mkdir(exist_ok=True)

L, CBD, LARGO_KM = 201, 100, 20.0
DX = LARGO_KM / L
H_BASE = (7200, 18000, 10800)
YS = (3.5e6, 1.5e6, 0.5e6)
Y_MED = 1.5e6
ALPHA0, RHO0 = 6.0, 0.0025
ALPHA_R0 = (6.5, 6.0, 5.5)
ESTRATOS = ("Alto", "Medio", "Bajo")
SEMILLA = 42


# --------------------------------------------------------------------------
# Construccion de configuraciones
# --------------------------------------------------------------------------
def estratos_elast(e_t: float, e_s: float, alpha: float = ALPHA0, rho0: float = RHO0):
    """alpha uniforme; lambda_h ~ y^-e_t ; rho_h/lambda_h ~ y^e_s.

    Con `e_s = e_t` la rho queda uniforme. La brecha `e_s - e_t` es el unico
    parametro que decide el vuelco de Muth/Wheaton; `rho0` decide el umbral.
    """
    return tuple(
        LandUseStratumConfig(
            y=y,
            alpha=alpha,
            rho=rho0 * (y / Y_MED) ** (e_s - e_t),
            **{"lambda": (y / Y_MED) ** (-e_t)},
        )
        for y in YS
    )


def estratos_r0(rho0: float = RHO0):
    """La calibracion vigente: alpha heterogenea, lambda uniforme."""
    return tuple(
        LandUseStratumConfig(y=y, alpha=a, rho=rho0, **{"lambda": 1.0})
        for y, a in zip(YS, ALPHA_R0, strict=True)
    )


def config(estr=None, *, forma="normal", H=H_BASE, sigma=0.5, beta=1.0) -> LandUseConfig:
    cfg = LandUseConfig(H_por_estrato=H, forma=forma, oferta_sigma_frac=sigma, beta=beta)
    if estr is not None:
        cfg.estratos = estr
    return cfg


def resolver(cfg: LandUseConfig, *, ele: int = L, cbd: int = CBD) -> dict:
    dx = LARGO_KM / ele
    t0 = time.perf_counter()
    ciudad = LandUseCity.build(
        L=ele, CBD=cbd, cfg=cfg, ancho_celda_km=dx, rng=np.random.default_rng(SEMILLA)
    )
    dt = time.perf_counter() - t0
    return {
        "Q": np.asarray(ciudad.result.Q, dtype=float),
        "S": np.asarray(ciudad.S, dtype=float),
        "p": np.asarray(ciudad.result.p, dtype=float),
        "dens": np.asarray(ciudad.densidad_por_celda(), dtype=float),
        "iters": int(getattr(ciudad.result, "iterations", -1)),
        "converge": bool(getattr(ciudad.result, "converged", True)),
        "seg": dt,
        "L": ele,
        "CBD": cbd,
        "dx": dx,
    }


# --------------------------------------------------------------------------
# Metricas
# --------------------------------------------------------------------------
def metricas(r: dict) -> dict:
    """Las metricas del plan (seccion 6), en unidades fisicas."""
    Q, S, p = r["Q"], r["S"], r["p"]
    ele, cbd, dx = r["L"], r["CBD"], r["dx"]
    km = np.abs(np.arange(ele) - cbd) * dx
    pos = (np.arange(ele) - cbd) * dx
    ocup = S[None, :] * Q
    tot_h = ocup.sum(axis=1)
    d = [float(ocup[h] @ km / max(tot_h[h], 1e-9)) for h in range(3)]

    # Dispersion del alto sobre la posicion SIGNADA: una asignacion bimodal
    # centro/periferia tiene que leerse como dispersa.
    w = ocup[0] / max(float(ocup[0].sum()), 1e-9)
    mu = float(w @ pos)
    disp_a = float(np.sqrt(w @ (pos - mu) ** 2))

    tot = float(ocup.sum())
    pi = tot_h / tot
    theil = 0.0
    for i in range(ele):
        n_i = float(ocup[:, i].sum())
        if n_i <= 0:
            continue
        for h in range(3):
            q = ocup[h, i] / n_i
            if q > 0 and pi[h] > 0:
                theil += (n_i / tot) * q * float(np.log(q / pi[h]))

    con = S > 0
    mezcla = float(np.mean(1.0 - Q[:, con].max(axis=0)))

    # Precio. El NIVEL de p no esta determinado por el modelo (falta la 4a
    # condicion de Alonso), asi que cualquier medida tiene que ser invariante a
    # sumarle una constante: la PENDIENTE lo es, un cociente como
    # (p1 - p10)/p1 NO. Por eso el plan se corrige aca.
    pend = float(np.polyfit(km[con], p[con], 1)[0])  # $/km, positivo = sube con d
    hab = np.flatnonzero(con)
    centro = int(hab[int(np.argmin(np.abs(hab - cbd)))])
    p_per = float(np.nanmean([p[hab[0]], p[hab[-1]]]))
    rango = float(np.nanmax(p[con]) - np.nanmin(p[con]))
    grad_p = (float(p[centro]) - p_per) / rango if rango > 1e-12 else 0.0

    def _en(k):
        i = np.argmin(np.abs(km[con] - k))
        return float(p[con][i])

    return {
        "d": d,
        "disp_a": disp_a,
        "theil": theil,
        "mezcla": mezcla,
        "grad_p": grad_p,
        "pend_p": pend,
        "dif_p_1_10": _en(1.0) - _en(10.0),
        "orden_ok": bool(d[0] < d[1] < d[2]),
        "iters": r["iters"],
        "seg": r["seg"],
    }


def tasa_b(r: dict) -> tuple[float, float]:
    """Ajusta dens ~ a - b*T. `b` es la tasa de cambio rho <-> alpha."""
    T = _default_T(r["L"], r["CBD"], 3, r["dx"])[0]
    m = np.arange(r["L"]) != r["CBD"]
    b = -float(np.polyfit(T[m], r["dens"][m], 1)[0])
    r2 = float(np.corrcoef(T[m], r["dens"][m])[0, 1] ** 2)
    return b, r2


def kappas(estr, b: float) -> list[float]:
    return [(e.alpha - b * e.rho) / e.lambda_ for e in estr]


def movidos(Qa: np.ndarray, Qb: np.ndarray, S: np.ndarray) -> list[float]:
    """Hogares reubicados entre dos asignaciones, por estrato."""
    return [float(np.abs(Qb[h] - Qa[h]) @ S / 2.0) for h in range(3)]


def fronteras(r: dict) -> list[float]:
    """Cruces entre estratos dominantes, en km desde el CBD (lado derecho)."""
    Q, ele, cbd, dx = r["Q"], r["L"], r["CBD"], r["dx"]
    dom = Q.argmax(axis=0)
    out = []
    for i in range(cbd + 1, ele - 1):
        if dom[i] != dom[i + 1]:
            a, bb = dom[i], dom[i + 1]
            f = Q[a] - Q[bb]
            if abs(f[i] - f[i + 1]) > 1e-12:
                t = f[i] / (f[i] - f[i + 1])
                out.append(float((i - cbd + t) * dx))
    return out


# --------------------------------------------------------------------------
# Experimentos
# --------------------------------------------------------------------------
def e0_sanidad() -> dict:
    """Sanidad (P1, P7) y la tasa de cambio b por geometria."""
    formas = ("normal", "uniforme", "exponencial", "meseta", "bimodal", "valle")
    geom = []
    for forma in formas:
        r = resolver(config(estratos_r0(), forma=forma))
        dens = r["dens"][np.arange(L) != CBD]
        plana = float(np.ptp(dens)) < 1.0
        b, r2 = (0.0, 0.0) if plana else tasa_b(r)
        T = _default_T(L, CBD, 3, DX)[0]
        m = np.arange(L) != CBD
        corr = None if plana else float(np.corrcoef(T[m], r["dens"][m])[0, 1])
        geom.append(
            {
                "forma": forma,
                "b": b,
                "r2": r2,
                "corr": corr,
                "plana": plana,
                "dens_min": float(dens.min()),
                "dens_max": float(dens.max()),
            }
        )

    # P1: rho uniforme con lambda uniforme no reasigna.
    q0 = resolver(config(estratos_r0(rho0=0.0)))["Q"]
    p1 = []
    for rho in (0.001, 0.0025, 0.01, 0.05):
        q = resolver(config(estratos_r0(rho0=rho)))["Q"]
        p1.append({"rho": rho, "max_dQ": float(np.abs(q - q0).max())})

    # P7: escalar (alpha, rho) por k y beta por 1/k deja Q identico (AU-13).
    qb = resolver(config(estratos_r0()))["Q"]
    p7 = []
    for k in (10.0, 377.0, 1000.0):
        estr = tuple(
            LandUseStratumConfig(y=y, alpha=a * k, rho=RHO0 * k, **{"lambda": 1.0})
            for y, a in zip(YS, ALPHA_R0, strict=True)
        )
        q = resolver(config(estr, beta=1.0 / k))["Q"]
        p7.append({"k": k, "max_dQ": float(np.abs(q - qb).max())})

    # b escala con la poblacion: dens ~ N.
    escala_N = []
    for H in ((3600, 14400, 18000), H_BASE, (21600, 54000, 32400)):
        b, _ = tasa_b(resolver(config(estratos_r0(), H=H)))
        escala_N.append({"sumaH": int(sum(H)), "b": b, "b_por_N": b / sum(H)})

    return {"geometria": geom, "P1": p1, "P7": p7, "escala_N": escala_N}


def e1_nivel() -> dict:
    """Nivel de rho uniforme, en los dos regimenes."""
    rhos = (0.0, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.05, 0.1)
    out = {}
    for reg, hacer in (("R0", estratos_r0), ("R1", lambda r: estratos_elast(1.0, 1.0, rho0=r))):
        filas, base_q = [], None
        for rho in rhos:
            r = resolver(config(hacer(rho)))
            m = metricas(r)
            if base_q is None:
                base_q = r["Q"]
            m["rho"] = rho
            m["max_dQ_vs_0"] = float(np.abs(r["Q"] - base_q).max())
            m["movidos"] = float(sum(movidos(base_q, r["Q"], r["S"])))
            filas.append(m)
        out[reg] = filas
    # Perfil de precios para la figura.
    perf = {}
    for rho in (0.0, 0.0025, 0.02, 0.1):
        r = resolver(config(estratos_elast(1.0, 1.0, rho0=rho)))
        perf[str(rho)] = {"p": r["p"].tolist(), "S": r["S"].tolist()}
    out["perfil_p_R1"] = perf
    return out


BRECHAS = (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
RHOS_E2 = (0.001, 0.0025, 0.005, 0.01, 0.02)


def e2_brecha() -> dict:
    """Grilla (brecha, rho0) en R1: donde se cumple C1 y donde vuelca."""
    filas = []
    for rho0 in RHOS_E2:
        for br in BRECHAS:
            estr = estratos_elast(1.0, 1.0 + br, rho0=rho0)
            r = resolver(config(estr))
            m = metricas(r)
            b, _ = tasa_b(r)
            m.update(
                {
                    "rho0": rho0,
                    "brecha": br,
                    "rho_h": [e.rho for e in estr],
                    "lambda_h": [e.lambda_ for e in estr],
                    "kappa": kappas(estr, b),
                    "b": b,
                    "fronteras": fronteras(r),
                }
            )
            filas.append(m)
    return {"filas": filas, "brechas": list(BRECHAS), "rhos": list(RHOS_E2)}


def e3_redundancia() -> dict:
    """Cuanto del efecto de rho lo reproduce alpha (AU-12), por geometria."""
    out = []
    rho_het = (0.0050, 0.0025, 0.0010)
    for forma in ("normal", "exponencial", "meseta", "bimodal", "valle"):
        base = resolver(config(estratos_r0(), forma=forma))
        b, r2 = tasa_b(base)
        estr_rho = tuple(
            LandUseStratumConfig(y=y, alpha=a, rho=rr, **{"lambda": 1.0})
            for y, a, rr in zip(YS, ALPHA_R0, rho_het, strict=True)
        )
        r_rho = resolver(config(estr_rho, forma=forma))
        estr_eq = tuple(
            LandUseStratumConfig(y=y, alpha=a - b * rr, rho=0.0, **{"lambda": 1.0})
            for y, a, rr in zip(YS, ALPHA_R0, rho_het, strict=True)
        )
        r_eq = resolver(config(estr_eq, forma=forma))
        S = base["S"]
        efecto = sum(movidos(base["Q"], r_rho["Q"], S))  # lo que rho movio
        residuo = sum(movidos(r_rho["Q"], r_eq["Q"], S))  # lo que alpha no imita
        out.append(
            {
                "forma": forma,
                "b": b,
                "r2": r2,
                "efecto_rho": efecto,
                "residuo": residuo,
                "frac_no_imitada": residuo / efecto if efecto > 1e-9 else float("nan"),
                "max_dQ": float(np.abs(r_rho["Q"] - r_eq["Q"]).max()),
                "d_rho": metricas(r_rho)["d"],
                "d_eq": metricas(r_eq)["d"],
            }
        )
    return {"filas": out, "rho_het": list(rho_het)}


def e4_donde() -> dict:
    """Donde cae el efecto: fronteras o repartido."""
    base = resolver(config(estratos_elast(1.0, 1.0)))
    out = {"base": {"fronteras": fronteras(base), "S": base["S"].tolist()}}
    casos = {}
    for br in (-0.5, 0.5, 1.0, 1.5):
        r = resolver(config(estratos_elast(1.0, 1.0 + br)))
        dQ = np.abs(r["Q"] - base["Q"]) * base["S"][None, :]
        por_celda = dQ.sum(axis=0) / 2.0
        orden = np.argsort(-por_celda)
        tot = float(por_celda.sum())
        casos[str(br)] = {
            "brecha": br,
            "movidos_total": tot,
            "fronteras": fronteras(r),
            "pct_top20": 100.0 * float(por_celda[orden[:20]].sum()) / tot if tot > 0 else 0.0,
            "pct_top30": 100.0 * float(por_celda[orden[:30]].sum()) / tot if tot > 0 else 0.0,
            "por_celda": por_celda.tolist(),
            "Q": r["Q"].tolist(),
        }
    out["casos"] = casos
    return out


def e5_precios() -> dict:
    """El nivel de rho contra el gradiente de precios (invariante al nivel de p)."""
    filas = []
    for rho0 in np.linspace(0.0, 0.03, 31):
        r = resolver(config(estratos_elast(1.0, 1.0, rho0=float(rho0))))
        m = metricas(r)
        filas.append(
            {
                "rho0": float(rho0),
                "pend_p": m["pend_p"],
                "dif_p_1_10": m["dif_p_1_10"],
                "grad_p": m["grad_p"],
                "d": m["d"],
            }
        )
    vig = metricas(resolver(config(estratos_r0())))
    return {
        "filas": filas,
        "vigente": {"rho0": RHO0, **{k: vig[k] for k in ("pend_p", "dif_p_1_10", "grad_p")}},
    }


def e6_transporte() -> dict:
    """Arrastre sobre el reparto modal de la corrida acoplada por defecto."""
    import sys

    raiz = Path(__file__).resolve().parents[2] / "packages" / "titirilquen_core"
    sys.path.insert(0, str(raiz / "tests"))
    import test_linea_base as tlb
    from titirilquen_core.equilibrium.msa import ConvergenceTrace

    def corre(estr, loc):
        cfg = LandUseConfig(
            H_por_estrato=H_BASE, forma="normal", oferta_sigma_frac=0.5, max_iter=2000
        )
        if estr is not None:
            cfg.estratos = estr
        tr = ConvergenceTrace()
        t0 = time.perf_counter()
        for _ in tlb.iter_msa_desde_suelo(tlb._config_web(), cfg, tr, localizacion=loc):
            pass
        dt = time.perf_counter() - t0
        sp = tr.iteraciones[-1].modal_split
        tot = sum(sp.values())
        return {m: 100.0 * v / tot for m, v in sp.items()}, len(tr.iteraciones), dt

    casos = [
        ("R0 vigente", None),
        ("R1 brecha 0, rho 0,0025", estratos_elast(1.0, 1.0)),
        ("R1 brecha 0, rho 0,01", estratos_elast(1.0, 1.0, rho0=0.01)),
        ("R1 brecha +0,5", estratos_elast(1.0, 1.5)),
        ("R1 brecha +1,0", estratos_elast(1.0, 2.0)),
        ("R1 brecha +1,5", estratos_elast(1.0, 2.5)),
    ]
    out = {"pineado": dict(tlb.ESPERADO), "filas": []}
    for nombre, estr in casos:
        fila = {"caso": nombre}
        for loc in ("equilibrio", "original"):
            pct, it, dt = corre(estr, loc)
            fila[loc] = {"pct": pct, "iters": it, "seg": dt}
        out["filas"].append(fila)
    return out


def e7_robustez() -> dict:
    """Que la brecha critica no dependa de detalles."""
    brechas = (0.0, 0.5, 1.0, 1.5, 2.0)
    variaciones = [
        ("beta", [("beta 0,5", {"beta": 0.5}), ("beta 1", {}), ("beta 2", {"beta": 2.0})]),
        (
            "sigma",
            [("sigma 0,3", {"sigma": 0.3}), ("sigma 0,5", {}), ("sigma 0,8", {"sigma": 0.8})],
        ),
        (
            "shares",
            [
                ("20/50/30", {}),
                ("10/40/50", {"H": (3600, 14400, 18000)}),
                ("33/33/33", {"H": (12000, 12000, 12000)}),
            ],
        ),
        ("forma", [("normal", {}), ("bimodal", {"forma": "bimodal"})]),
    ]
    out = []
    for eje, casos in variaciones:
        for nombre, kw in casos:
            fila = {"eje": eje, "caso": nombre, "puntos": []}
            for br in brechas:
                r = resolver(config(estratos_elast(1.0, 1.0 + br), **kw))
                m = metricas(r)
                fila["puntos"].append(
                    {"brecha": br, "d": m["d"], "orden_ok": m["orden_ok"], "theil": m["theil"]}
                )
            out.append(fila)
    # Invariancia de grilla (D-26) aparte: cambia L, hay que reescalar CBD.
    grilla = []
    for ele in (101, 201, 401):
        fila = {"L": ele, "puntos": []}
        for br in brechas:
            r = resolver(config(estratos_elast(1.0, 1.0 + br)), ele=ele, cbd=ele // 2)
            m = metricas(r)
            fila["puntos"].append({"brecha": br, "d": m["d"], "orden_ok": m["orden_ok"]})
        grilla.append(fila)
    return {"variaciones": out, "grilla": grilla, "brechas": list(brechas)}


def main() -> None:
    tareas = [
        ("e0-sanidad", e0_sanidad),
        ("e1-nivel", e1_nivel),
        ("e2-brecha", e2_brecha),
        ("e3-redundancia", e3_redundancia),
        ("e4-donde", e4_donde),
        ("e5-precios", e5_precios),
        ("e6-transporte", e6_transporte),
        ("e7-robustez", e7_robustez),
    ]
    for nombre, fn in tareas:
        t0 = time.perf_counter()
        datos = fn()
        (SALIDA / f"{nombre}.json").write_text(
            json.dumps(datos, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  {nombre:<16} {time.perf_counter() - t0:7.1f} s")
    print(f"\n  Salida en {SALIDA}")


if __name__ == "__main__":
    main()
