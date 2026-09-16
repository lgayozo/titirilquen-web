"""Cuánto cambia el resultado al pasar de la forma cerrada al HEV.

    uv run python impacto.py

**Qué compara y por qué así.** Los mismos datos, con los mismos `λ_h`
heterogéneos, resueltos de las dos maneras:

* **antes** — `solve_logit`, la forma cerrada, con UNA precisión en dinero
  común a los tres estratos. Es lo que hacía el simulador hasta el commit del
  HEV: `ciudad.py` llamaba `solve_logit(..., beta=cfg.beta, ...)`, y esa
  función aplica `beta` tal cual sobre la puja en dinero. Entonces λ valía 1 en
  los tres estratos, así que `b = β`. Hoy λ está en útiles por peso (D-34) y la
  conversión honesta es `b_h = β·λ_h` (D-31); la forma cerrada sólo admite un
  `b`, y se toma `b = β·λ_medio`: el estrato medio es el ancla del barrido, y
  con λ uniforme (r = 1) las dos ramas coinciden exactamente.
* **ahora** — `solve_subasta`, que con `λ` heterogéneos despacha al HEV y
  escala el ruido de cada estrato a `1/(β·λ_h)`.

La diferencia entre las dos ES el impacto de aplicar la formulación correcta.
No hay recalibración de por medio: mismos `y`, `α`, `ρ`, `β`, misma `T` y
misma ciudad. Lo único que cambia es el modelo de la subasta.

**El barrido.** `λ = (λ_m/r, λ_m, λ_m·r)` con `λ_m` el λ vigente del estrato
medio — decreciente en el ingreso, como manda Martínez (p. 77). En `r = 1` los
dos modelos coinciden y sirve de ancla. Se agrega la fila **vigente**: los tres
λ literales de `LandUseConfig()` (= |b_costo| de transporte, D-34), que no son
exactamente geométricos; su `r_eq = sqrt(λ_bajo/λ_alto)` ≈ 1,97.

**La accesibilidad** `T` es la de la app standalone: el logsum mensual de
transporte a flujo libre sobre la red vacía configurada (D-34, D-42), común a
las dos ramas y a todas las filas.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from titirilquen_core.config import DemandConfig, SupplyConfig
from titirilquen_core.land_use.accesibilidad import T_flujo_libre
from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig
from titirilquen_core.land_use.equilibrium import solve_logit, solve_subasta
from titirilquen_core.presets import DEFAULT_STRATA

SALIDA = Path(__file__).parent / "salida"
ESTRATOS = ("Alto", "Medio", "Bajo")
L, CBD, LARGO_KM = 201, 100, 20.0
DX = LARGO_KM / L
#: Razones de heterogeneidad a barrer: λ = (λ_m/r, λ_m, λ_m·r).
RAZONES = (1.0, 1.25, 1.5, 2.0, 3.0, 4.0)
#: Razones para las que se guarda el perfil celda a celda.
PERFILES = (1.5, 2.0, 4.0)
EULER_GAMMA = 0.5772156649015329


def _config(lams: tuple[float, float, float]) -> LandUseConfig:
    base = LandUseConfig()
    return LandUseConfig(
        **{
            **base.model_dump(by_alias=True),
            "estratos": tuple(
                LandUseStratumConfig(y=e.y, alpha=e.alpha, rho=e.rho, **{"lambda": lam})
                for e, lam in zip(base.estratos, lams, strict=True)
            ),
        }
    )


def _T() -> np.ndarray:
    """La T standalone de la app: logsum de transporte a flujo libre (D-34, D-42)."""
    dem = DemandConfig.model_validate({"estratos": DEFAULT_STRATA})
    return T_flujo_libre(dem, L, CBD, DX, supply=SupplyConfig())


def _entradas(cfg: LandUseConfig, T: np.ndarray) -> dict:
    """Los argumentos del solver, idénticos para las dos ramas."""
    ciudad = LandUseCity.build(
        L=L, CBD=CBD, cfg=cfg, ancho_celda_km=DX, T=T, rng=np.random.default_rng(42)
    )
    return {
        "H": np.asarray(cfg.H_por_estrato, dtype=int),
        "S": ciudad.S,
        "y": np.asarray([s.y for s in cfg.estratos], dtype=float),
        "T": T,
        "alpha": np.asarray([s.alpha for s in cfg.estratos], dtype=float),
        "rho": np.asarray([s.rho for s in cfg.estratos], dtype=float),
        "lambda_h": np.asarray([s.lambda_ for s in cfg.estratos], dtype=float),
        "beta": cfg.beta,
        "tol": cfg.tol,
        "max_iter": cfg.max_iter,
        "ancho_celda_km": DX,
    }


def _km() -> np.ndarray:
    return np.abs(np.arange(L) - CBD) * DX


def _metricas(Q: np.ndarray, S: np.ndarray, p: np.ndarray) -> dict:
    """Distancia media al CBD por estrato y gradiente de precio."""
    km = _km()
    hogares = Q * S
    d = [float(hogares[h] @ km / hogares[h].sum()) for h in range(3)]
    con_oferta = S > 0
    grad = float(np.polyfit(km[con_oferta], p[con_oferta], 1)[0])
    return {"d": d, "grad_p": grad}


def _cruce(Q: np.ndarray, a: int, b: int) -> float | None:
    """Primer x > 0 (km) donde la composición `a` deja de ir por encima de `b`."""
    x = (np.arange(L) - CBD) * DX
    dif = Q[a] - Q[b]
    for k in range(CBD, L - 1):
        if dif[k] > 0 >= dif[k + 1]:
            t = dif[k] / (dif[k] - dif[k + 1])
            return float(x[k] + t * (x[k + 1] - x[k]))
    return None


def _fila(r: float | None, lams: tuple[float, float, float], T: np.ndarray) -> tuple[dict, dict]:
    cfg = _config(lams)
    kw = _entradas(cfg, T)
    S = np.asarray(kw["S"], dtype=float)
    lam_m = lams[1]

    # La forma cerrada recibe UNA precisión en dinero: b = β·λ_medio.
    antes = solve_logit(**{**kw, "beta": kw["beta"] * lam_m})
    ahora = solve_subasta(**kw)  # HEV si los λ difieren; cerrada si no

    # Hogares que cambian de celda. |ΔQ|·S sumado y dividido por 2 es el
    # transporte mínimo entre las dos asignaciones: lo que sale de un lado
    # entra en otro, y sin el /2 se contaría dos veces.
    dQS = np.abs(ahora.Q - antes.Q) * S / 2.0
    movidos = [float(dQS[h].sum()) for h in range(3)]
    total = float(sum(movidos))
    por_celda = np.sort(dQS.sum(axis=0))[::-1]
    concentracion = {
        str(n): (float(por_celda[:n].sum() / total) if total > 0 else 0.0) for n in (10, 20, 30)
    }

    m_antes = _metricas(antes.Q, S, antes.p)
    m_ahora = _metricas(ahora.Q, S, ahora.p)

    con_oferta = S > 0
    brecha = ahora.p[con_oferta] - antes.p[con_oferta]
    fila = {
        "r": r,
        "r_eq": float(np.sqrt(lams[2] / lams[0])),
        "vigente": r is None,
        "lambda": list(lams),
        "b_cerrada": float(kw["beta"] * lam_m),
        "theta_hev": [float(1.0 / (kw["beta"] * lam)) for lam in lams],
        "gamma_sobre_b": float(EULER_GAMMA / (kw["beta"] * lam_m)),
        "max_dQ": float(np.max(np.abs(ahora.Q - antes.Q))),
        "movidos": movidos,
        "movidos_total": total,
        "H": [int(x) for x in kw["H"]],
        "pct_movidos": [100.0 * m / h for m, h in zip(movidos, kw["H"], strict=True)],
        "concentracion": concentracion,
        "d_antes": m_antes["d"],
        "d_ahora": m_ahora["d"],
        "grad_antes": m_antes["grad_p"],
        "grad_ahora": m_ahora["grad_p"],
        "u_antes": antes.u.tolist(),
        "u_ahora": ahora.u.tolist(),
        "rango_p_antes": float(np.ptp(antes.p[con_oferta])),
        "rango_p_ahora": float(np.ptp(ahora.p[con_oferta])),
        "brecha_p_media": float(brecha.mean()),
        "brecha_p_std": float(brecha.std()),
        "fronteras_antes": [_cruce(antes.Q, 0, 1), _cruce(antes.Q, 1, 2)],
        "fronteras_ahora": [_cruce(ahora.Q, 0, 1), _cruce(ahora.Q, 1, 2)],
        "converge": bool(ahora.converged and antes.converged),
        "iteraciones": [int(antes.iterations), int(ahora.iterations)],
    }
    perfil = {"S": S.tolist(), "Q_antes": antes.Q.tolist(), "Q_ahora": ahora.Q.tolist()}
    return fila, perfil


def main() -> None:
    base = LandUseConfig()
    lam_vig = tuple(float(s.lambda_) for s in base.estratos)
    lam_m = lam_vig[1]
    T = _T()

    filas: list[dict] = []
    perfiles: dict[str, dict] = {}
    for r in RAZONES:
        fila, perfil = _fila(r, (lam_m / r, lam_m, lam_m * r), T)
        filas.append(fila)
        if r in PERFILES:
            perfiles[str(r)] = perfil
    fila, perfil = _fila(None, lam_vig, T)
    filas.append(fila)
    perfiles["vigente"] = perfil

    def etiq(f: dict) -> str:
        return "vig." if f["vigente"] else f"{f['r']:.2f}"

    print("\n  IMPACTO DE PASAR DE LA FORMA CERRADA AL HEV")
    print("  mismos datos, mismos lambda, dos solvers")
    print(f"  beta = {base.beta:.4f}   lambda_m = {lam_m:.6f}   b_cerrada = beta*lambda_m\n")
    print(
        f"  {'r':>5}{'lambda (alto/medio/bajo) x1e-3':>32}{'max|dQ|':>10}{'movidos':>10}{'% tot':>8}"
    )
    print("  " + "-" * 65)
    for f in filas:
        lam = "/".join(f"{1e3 * v:.3f}" for v in f["lambda"])
        print(
            f"  {etiq(f):>5}{lam:>32}{f['max_dQ']:>10.4f}"
            f"{f['movidos_total']:>10,.0f}{100 * f['movidos_total'] / sum(f['H']):>7.2f}%"
        )

    print("\n  Distancia media al CBD por estrato (km), antes -> ahora")
    print(f"  {'r':>5}   " + "".join(f"{e:>22}" for e in ESTRATOS))
    print("  " + "-" * 73)
    for f in filas:
        cols = "".join(f"{f['d_antes'][h]:>10.2f} ->{f['d_ahora'][h]:>9.2f}" for h in range(3))
        print(f"  {etiq(f):>5}   {cols}")

    print("\n  Gradiente de precio ($/km), antes -> ahora, y fronteras (km)")
    for f in filas:
        fr = " ".join(
            f"{a if a is None else round(a, 3)}->{b if b is None else round(b, 3)}"
            for a, b in zip(f["fronteras_antes"], f["fronteras_ahora"], strict=True)
        )
        print(f"  r={etiq(f):<5} {f['grad_antes']:>12.1f} ->{f['grad_ahora']:>12.1f}   {fr}")

    print("\n  En r = 1 los dos modelos son el mismo, asi que la primera fila")
    print("  tiene que dar cero exacto: es el ancla de que la comparacion mide")
    print("  el modelo y no una diferencia de implementacion.\n")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "impacto.json").write_text(
        json.dumps(
            {
                "L": L,
                "CBD": CBD,
                "dx": DX,
                "beta": base.beta,
                "lambda_vigente": list(lam_vig),
                "alpha": [s.alpha for s in base.estratos],
                "rho": [s.rho for s in base.estratos],
                "filas": filas,
                "perfiles": perfiles,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"  Datos en {SALIDA / 'impacto.json'}\n")


if __name__ == "__main__":
    main()
