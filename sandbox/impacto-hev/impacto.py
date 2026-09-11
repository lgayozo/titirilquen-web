"""Cuánto cambia el resultado al pasar de la forma cerrada al HEV.

    uv run python impacto.py

**Qué compara y por qué así.** Los mismos datos, con los mismos `λ_h`
heterogéneos, resueltos de las dos maneras:

* **antes** — `solve_logit`, la forma cerrada. Es literalmente lo que hacía el
  simulador: hasta el commit del HEV, `ciudad.py` llamaba
  `solve_logit(..., beta=self.cfg.beta, ...)` con estos mismos argumentos, y esa
  función **conservó su semántica** a través de D-31, así que reproduce el
  comportamiento viejo sin desenterrar código.
* **ahora** — `solve_subasta`, que con `λ` heterogéneos despacha al HEV.

La diferencia entre las dos ES el impacto de aplicar la formulación correcta.
No hay recalibración de por medio: mismos `y`, `α`, `ρ`, `λ`, `β` y misma
ciudad. Lo único que cambia es el modelo de la subasta.

**Por qué un barrido y no un caso.** No sabemos el `λ` verdadero. Lo que se
puede afirmar es cómo crece el impacto con la heterogeneidad, así que se barre
la razón `r` con `λ = (1/r, 1, r)` — decreciente en el ingreso, como manda
Martínez (p. 77). En `r = 1` los dos modelos coinciden y sirve de ancla.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from titirilquen_core.land_use.ciudad import LandUseCity, _default_T
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig
from titirilquen_core.land_use.equilibrium import solve_logit, solve_subasta

SALIDA = Path(__file__).parent / "salida"
ESTRATOS = ("Alto", "Medio", "Bajo")
L, CBD, LARGO_KM = 201, 100, 20.0
DX = LARGO_KM / L
#: Razones de heterogeneidad a barrer: λ = (1/r, 1, r).
RAZONES = (1.0, 1.25, 1.5, 2.0, 3.0, 4.0)


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


def _entradas(cfg: LandUseConfig) -> dict:
    """Los argumentos del solver, idénticos para las dos ramas."""
    ciudad = LandUseCity.build(
        L=L, CBD=CBD, cfg=cfg, ancho_celda_km=DX, rng=np.random.default_rng(42)
    )
    return {
        "H": np.asarray(cfg.H_por_estrato, dtype=int),
        "S": ciudad.S,
        "y": np.asarray([s.y for s in cfg.estratos], dtype=float),
        "T": _default_T(L, CBD, 3, DX),
        "alpha": np.asarray([s.alpha for s in cfg.estratos], dtype=float),
        "rho": np.asarray([s.rho for s in cfg.estratos], dtype=float),
        "lambda_h": np.asarray([s.lambda_ for s in cfg.estratos], dtype=float),
        "beta": cfg.beta,
        "tol": cfg.tol,
        "max_iter": cfg.max_iter,
        "ancho_celda_km": DX,
    }


def _metricas(Q: np.ndarray, S: np.ndarray, p: np.ndarray) -> dict:
    """Distancia media al CBD por estrato y gradiente de precio."""
    km = np.abs(np.arange(L) - CBD) * DX
    hogares = Q * S
    d = [float(hogares[h] @ km / hogares[h].sum()) for h in range(3)]
    con_oferta = S > 0
    grad = float(np.polyfit(km[con_oferta], p[con_oferta], 1)[0])
    return {"d": d, "grad_p": grad}


#: Razones para las que se guarda el perfil celda a celda.
PERFILES = (1.5, 2.0, 4.0)


def main() -> None:
    filas: list[dict] = []
    perfiles: dict[str, dict] = {}
    for r in RAZONES:
        lams = (1.0 / r, 1.0, r)
        kw = _entradas(_config(lams))
        S = np.asarray(kw["S"], dtype=float)

        antes = solve_logit(**kw)  # la forma cerrada: lo que hacia el simulador
        ahora = solve_subasta(**kw)  # HEV, si los lambda difieren

        # Hogares que cambian de celda. |ΔQ|·S sumado y dividido por 2 es el
        # transporte minimo entre las dos asignaciones: lo que sale de un lado
        # entra en otro, y sin el /2 se contaria dos veces.
        movidos = [float(np.abs(ahora.Q[h] - antes.Q[h]) @ S / 2.0) for h in range(3)]
        m_antes = _metricas(antes.Q, S, antes.p)
        m_ahora = _metricas(ahora.Q, S, ahora.p)

        filas.append(
            {
                "r": r,
                "lambda": list(lams),
                "max_dQ": float(np.max(np.abs(ahora.Q - antes.Q))),
                "movidos": movidos,
                "movidos_total": float(sum(movidos)),
                "H": [int(x) for x in kw["H"]],
                "pct_movidos": [100.0 * m / h for m, h in zip(movidos, kw["H"], strict=True)],
                "d_antes": m_antes["d"],
                "d_ahora": m_ahora["d"],
                "grad_antes": m_antes["grad_p"],
                "grad_ahora": m_ahora["grad_p"],
                "converge": bool(ahora.converged and antes.converged),
            }
        )
        # Perfil espacial completo para las razones que ilustra el informe. Es
        # lo que muestra que la diferencia NO esta repartida: se concentra en la
        # frontera entre estratos, que es donde el modelo decide la segregacion.
        if r in PERFILES:
            perfiles[str(r)] = {
                "S": S.tolist(),
                "Q_antes": antes.Q.tolist(),
                "Q_ahora": ahora.Q.tolist(),
            }

    an = 46
    print("\n  IMPACTO DE PASAR DE LA FORMA CERRADA AL HEV")
    print("  mismos datos, mismos lambda, dos solvers\n")
    print(
        f"  {'r':>4}{'lambda (alto/medio/bajo)':>26}{'max|dQ|':>10}"
        f"{'hogares movidos':>18}{'% del total':>13}"
    )
    print("  " + "-" * (an + 26))
    for f in filas:
        lam = "/".join(f"{v:.2f}" for v in f["lambda"])
        print(
            f"  {f['r']:>4}{lam:>26}{f['max_dQ']:>10.4f}"
            f"{f['movidos_total']:>18,.0f}{100 * f['movidos_total'] / sum(f['H']):>12.2f}%"
        )

    print("\n  Distancia media al CBD por estrato (km), antes -> ahora")
    print(f"  {'r':>4}   " + "".join(f"{e:>22}" for e in ESTRATOS))
    print("  " + "-" * 72)
    for f in filas:
        cols = "".join(f"{f['d_antes'][h]:>10.2f} ->{f['d_ahora'][h]:>9.2f}" for h in range(3))
        print(f"  {f['r']:>4}   {cols}")

    print("\n  Gradiente de precio ($/km), antes -> ahora")
    for f in filas:
        print(f"  r={f['r']:<5} {f['grad_antes']:>12.1f}  ->{f['grad_ahora']:>12.1f}")

    print("\n  En r = 1 los dos modelos son el mismo, asi que la primera fila")
    print("  tiene que dar cero exacto: es el ancla de que la comparacion mide")
    print("  el modelo y no una diferencia de implementacion.\n")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "impacto.json").write_text(
        json.dumps(
            {"L": L, "CBD": CBD, "dx": DX, "filas": filas, "perfiles": perfiles},
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"  Datos en {SALIDA / 'impacto.json'}\n")


if __name__ == "__main__":
    main()
