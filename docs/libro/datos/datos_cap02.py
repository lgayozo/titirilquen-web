"""Datos del capítulo 5 — Uso de suelo: oferta y subasta.

Produce `cap05.json`. El módulo ya tiene tres informes y trece hallazgos (AU-01
a AU-13), así que este capítulo no repite lo medido: audita lo que quedó sin
mirar y verifica las conservaciones que sostienen todo lo demás.

Seis bloques:

1. `formas` — las seis ofertas de vivienda: perfil, conservación `Σ S = N` y
   CBD vacío. Es el único módulo del capítulo sin auditoría previa.
2. `conservacion` — `Σ_i S_i·Q_hi = H_h` (D-25) por forma y por escala. Es la
   ecuación (5.1) de Martínez y la condición que hace interpretable todo el
   equilibrio.
3. `despacho` — cuándo `solve_subasta` va a la forma cerrada y cuándo a HEV, y
   si el balance de hogares se cumple igual en ambas ramas. Es el pendiente que
   dejó la auditoría externa del 2026-09-05.
4. `asignacion_entera` — `allocation.py` conserva `S_i` por celda pero no `H_h`
   por estrato (D-44): cuánto se desvía.
5. `perillas` — β y ρ, los dos parámetros propios del módulo, con sus rangos
   medidos.
6. `invariancias` — grilla (D-26) y tamaño físico, sobre la configuración vigente.

Correr desde `packages/titirilquen_core` (~3 min):

    uv run python ../../docs/libro/datos/datos_cap05.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "packages" / "titirilquen_core" / "tests"))

from titirilquen_core.config import DemandConfig, SupplyConfig
from titirilquen_core.land_use import LandUseCity, LandUseConfig
from titirilquen_core.land_use.accesibilidad import T_flujo_libre
from titirilquen_core.land_use.config import LandUseStratumConfig
from titirilquen_core.land_use.supply import generar_oferta
from titirilquen_core.presets import DEFAULT_STRATA

SALIDA = Path(__file__).parent / "cap05.json"
FORMAS = ("normal", "uniforme", "exponencial", "meseta", "bimodal", "valle")
L, CBD, LARGO = 201, 100, 20.0
DX = LARGO / L
H_APP = (7200, 18000, 10800)


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


def _demanda() -> DemandConfig:
    return DemandConfig.model_validate({"estratos": DEFAULT_STRATA})


def _T():
    return T_flujo_libre(_demanda(), L, CBD, DX, supply=SupplyConfig())


def _ciudad(cfg: LandUseConfig, T=None):
    return LandUseCity.build(
        L=L,
        CBD=CBD,
        cfg=cfg,
        ancho_celda_km=DX,
        T=_T() if T is None else T,
        rng=np.random.default_rng(42),
    )


def formas() -> list[dict]:
    """Las seis ofertas: qué perfil dan y si conservan la población."""
    N = sum(H_APP)
    filas = []
    for f in FORMAS:
        S = generar_oferta(forma=f, I=L, N=N, CBD=CBD, sigma_frac=0.5, forma_param=0.5)
        dens = S / DX
        filas.append(
            {
                "forma": f,
                "suma_S": int(S.sum()),
                "conserva_N": bool(int(S.sum()) == N),
                "cbd_vacio": bool(S[CBD] == 0),
                "celdas_con_oferta": int(np.sum(S > 0)),
                "densidad_min_hab_km": round(float(dens.min()), 1),
                "densidad_max_hab_km": round(float(dens.max()), 1),
                "densidad_pico_en_km": round(
                    float(abs(int(np.argmax(S)) - CBD) * DX), 2
                ),
            }
        )
    return filas


def conservacion() -> dict:
    """`Σ_i S_i·Q_hi = H_h` — la ec. (5.1) de Martínez, por forma y por escala."""
    por_forma = []
    for f in FORMAS:
        cfg = LandUseConfig(H_por_estrato=H_APP, forma=f, max_iter=5000)
        c = _ciudad(cfg)
        H_obt = np.asarray(c.result.Q, float) @ np.asarray(c.S, float)
        err = np.abs(H_obt - np.asarray(H_APP, float))
        por_forma.append(
            {
                "forma": f,
                "convergio": bool(c.result.converged),
                "iteraciones": int(c.result.iterations),
                "error_max_hogares": float(f"{err.max():.3e}"),
                "error_relativo_max": float(f"{(err / np.asarray(H_APP)).max():.3e}"),
            }
        )
    por_escala = []
    for total in (3_600, 36_000, 144_000):
        H = (
            int(total * 0.2),
            int(total * 0.5),
            total - int(total * 0.2) - int(total * 0.5),
        )
        cfg = LandUseConfig(H_por_estrato=H, max_iter=5000)
        c = _ciudad(cfg)
        H_obt = np.asarray(c.result.Q, float) @ np.asarray(c.S, float)
        err = np.abs(H_obt - np.asarray(H, float))
        por_escala.append(
            {
                "suma_H": total,
                "error_max_hogares": float(f"{err.max():.3e}"),
                "iteraciones": int(c.result.iterations),
            }
        )
    return {"por_forma": por_forma, "por_escala": por_escala}


def despacho() -> dict:
    """Forma cerrada contra HEV: cuál corre, y si ambas conservan los hogares.

    `solve_subasta` elige según los datos: λ uniformes → forma cerrada (exacta
    ahí), λ distintos → HEV. El pendiente que dejó la auditoría externa era
    comprobar el balance de hogares al declarar convergencia en la rama HEV.
    """
    filas = []
    casos = (
        ("lambda uniforme (forma cerrada)", (1.0, 1.0, 1.0)),
        ("lambda del default (HEV)", None),
        ("lambda razon 10 (HEV)", (0.1, 1.0, 1.0)),
        ("lambda razon 100 (HEV)", (0.01, 1.0, 1.0)),
    )
    base_cfg = LandUseConfig(H_por_estrato=H_APP, max_iter=5000)
    for nombre, lams in casos:
        if lams is None:
            cfg = base_cfg
            lams_reales = tuple(e.lambda_ for e in base_cfg.estratos)
        else:
            cfg = base_cfg.model_copy(
                update={
                    "estratos": tuple(
                        LandUseStratumConfig(
                            y=e.y, alpha=e.alpha, rho=e.rho, **{"lambda": lam}
                        )
                        for e, lam in zip(base_cfg.estratos, lams, strict=True)
                    )
                }
            )
            lams_reales = lams
        c = _ciudad(cfg)
        Q = np.asarray(c.result.Q, float)
        H_obt = Q @ np.asarray(c.S, float)
        err = np.abs(H_obt - np.asarray(H_APP, float))
        cols = Q.sum(axis=0)
        con_oferta = np.asarray(c.S) > 0
        filas.append(
            {
                "caso": nombre,
                "lambdas": [round(float(x), 6) for x in lams_reales],
                "rama": "forma cerrada" if len(set(lams_reales)) == 1 else "HEV",
                "razon_escalas": round(max(lams_reales) / min(lams_reales), 1),
                "convergio": bool(c.result.converged),
                "iteraciones": int(c.result.iterations),
                "error_balance_hogares": float(f"{err.max():.3e}"),
                "columnas_suman_uno_error": float(
                    f"{np.abs(cols[con_oferta] - 1).max():.3e}"
                ),
            }
        )
    return {
        "filas": filas,
        "nota": (
            "El balance `Σ_i S_i·Q_hi = H_h` se cumple a precisión de máquina en "
            "las dos ramas, pero NINGUNA lo exige para declarar `converged`: la "
            "bandera sale del residuo del punto fijo. Es el pendiente que dejó la "
            "auditoría externa del 2026-09-05."
        ),
    }


def asignacion_entera() -> dict:
    """`allocation.py` reparte hogares enteros: conserva S_i, no H_h (D-44)."""
    cfg = LandUseConfig(H_por_estrato=H_APP, max_iter=5000)
    c = _ciudad(cfg)
    conteos = c.hogares_por_parcela_estrato()  # (3, L)
    por_celda = conteos.sum(axis=0)
    por_estrato = conteos.sum(axis=1)
    S = np.asarray(c.S)
    return {
        "S_conservado_por_celda": bool(np.array_equal(por_celda, S)),
        "H_objetivo": list(H_APP),
        "H_obtenido": [int(x) for x in por_estrato],
        "desvio_por_estrato": [
            int(a - b) for a, b in zip(por_estrato, H_APP, strict=True)
        ],
        "desvio_total_abs": int(np.abs(por_estrato - np.asarray(H_APP)).sum()),
        "desvio_relativo_max_pct": round(
            100.0 * float(np.abs(por_estrato - np.asarray(H_APP)).max() / max(H_APP)), 4
        ),
    }


def _metricas(c) -> dict:
    S = np.asarray(c.S, float)
    Q = np.asarray(c.result.Q, float)
    p = np.asarray(c.result.p, float)
    dist = np.abs(np.arange(L) - CBD) * DX
    ocup = S[None, :] * Q
    d = (ocup * dist[None, :]).sum(1) / ocup.sum(1)
    tot = ocup.sum()
    pi = ocup.sum(1) / tot
    th = 0.0
    for i in range(L):
        n_i = ocup[:, i].sum()
        if n_i <= 0:
            continue
        for h in range(3):
            q = ocup[h, i] / n_i
            if q > 0:
                th += (n_i / tot) * q * np.log(q / pi[h])
    hab = np.flatnonzero(np.asarray(c.S) > 0)
    cc = int(hab[np.argmin(np.abs(hab - CBD))])
    per = float(np.nanmean([p[hab[0]], p[hab[-1]]]))
    rango = float(np.nanmax(p) - np.nanmin(p))
    return {
        "dist_km": [round(float(x), 3) for x in d],
        "theil": round(th, 4),
        "grad_p": round((float(p[cc]) - per) / rango if rango > 1e-12 else 0.0, 3),
        "iteraciones": int(c.result.iterations),
    }


def perillas() -> dict:
    """β (nitidez) y ρ (densidad): los dos parámetros propios del módulo."""
    out = {"beta": [], "rho": []}
    for b in (0.05, 0.15, 0.5, 1.0):
        cfg = LandUseConfig(H_por_estrato=H_APP, beta=b, max_iter=5000)
        out["beta"].append({"beta": b, **_metricas(_ciudad(cfg))})
    for r in (0.0, 0.0052, 0.01, 0.02):
        cfg = LandUseConfig(
            H_por_estrato=H_APP,
            max_iter=5000,
            estratos=tuple(
                LandUseStratumConfig(
                    y=e.y, alpha=e.alpha, rho=r, **{"lambda": e.lambda_}
                )
                for e in LandUseConfig().estratos
            ),
        )
        out["rho"].append({"rho": r, **_metricas(_ciudad(cfg))})
    return out


def invariancias() -> dict:
    """Grilla (D-26) y tamaño físico, con la configuración vigente."""
    grilla = []
    for n in (101, 201, 401):
        cbd = n // 2
        dx = LARGO / n
        T = T_flujo_libre(_demanda(), n, cbd, dx, supply=SupplyConfig())
        c = LandUseCity.build(
            L=n,
            CBD=cbd,
            cfg=LandUseConfig(H_por_estrato=H_APP, max_iter=5000),
            ancho_celda_km=dx,
            T=T,
            rng=np.random.default_rng(42),
        )
        S = np.asarray(c.S, float)
        Q = np.asarray(c.result.Q, float)
        dist = np.abs(np.arange(n) - cbd) * dx
        ocup = S[None, :] * Q
        d = (ocup * dist[None, :]).sum(1) / ocup.sum(1)
        tot = ocup.sum()
        pi = ocup.sum(1) / tot
        th = 0.0
        for i in range(n):
            n_i = ocup[:, i].sum()
            if n_i <= 0:
                continue
            for h in range(3):
                q = ocup[h, i] / n_i
                if q > 0:
                    th += (n_i / tot) * q * np.log(q / pi[h])
        grilla.append(
            {
                "n_celdas": n,
                "theil": round(th, 4),
                "dist_km": [round(float(x), 3) for x in d],
            }
        )
    fisico = []
    for largo in (10.0, 20.0, 40.0):
        dx = largo / L
        T = T_flujo_libre(_demanda(), L, CBD, dx, supply=SupplyConfig())
        c = LandUseCity.build(
            L=L,
            CBD=CBD,
            cfg=LandUseConfig(H_por_estrato=H_APP, max_iter=5000),
            ancho_celda_km=dx,
            T=T,
            rng=np.random.default_rng(42),
        )
        fisico.append({"largo_km": largo, **_metricas(c)})
    return {"grilla": grilla, "tamano_fisico": fisico}


def main() -> None:
    datos = {
        "_meta": {
            "fecha": datetime.now(UTC).date().isoformat(),
            "commit": _commit(),
            "script": "docs/libro/datos/datos_cap05.py",
            "configuracion": (
                "Uso de suelo de la aplicación: 201 celdas, 20 km, ΣH = 36.000 "
                "(20/50/30), oferta normal σ=0,5, α=1, ρ=5,2e-3, β=0,15, "
                "λ=|b_costo| (D-34). Accesibilidad: red vacía configurada (D-42)."
            ),
        },
        "formas": formas(),
        "conservacion": conservacion(),
        "despacho": despacho(),
        "asignacion_entera": asignacion_entera(),
        "perillas": perillas(),
        "invariancias": invariancias(),
    }
    SALIDA.write_text(
        json.dumps(datos, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("Formas de oferta:")
    for f in datos["formas"]:
        print(
            f"  {f['forma']:<12} ΣS={f['suma_S']} conserva={f['conserva_N']} "
            f"CBD vacío={f['cbd_vacio']}  dens {f['densidad_min_hab_km']}–{f['densidad_max_hab_km']}"
        )
    print("\nConservación Σ S·Q = H (error máx. en hogares):")
    for f in datos["conservacion"]["por_forma"]:
        print(
            f"  {f['forma']:<12} {f['error_max_hogares']:>10.2e}  ({f['iteraciones']} iter)"
        )
    print("\nDespacho forma cerrada / HEV:")
    for f in datos["despacho"]["filas"]:
        print(
            f"  {f['caso']:<32} {f['rama']:<14} razón={f['razon_escalas']:>7} "
            f"balance={f['error_balance_hogares']:>10.2e} conv={f['convergio']}"
        )
    a = datos["asignacion_entera"]
    print(
        f"\nAsignación entera: S por celda conservado={a['S_conservado_por_celda']} · "
        f"desvío por estrato {a['desvio_por_estrato']} (máx {a['desvio_relativo_max_pct']}%)"
    )
    print(f"\nEscrito: {SALIDA}")


if __name__ == "__main__":
    main()
