"""Sensibilidad al truncamiento del tiempo vivido en cero.

    uv run python sensibilidad.py

Las tres fases usan `x = τ + ε` sin truncar (ver `persona.py`). Esto corre los
casos del informe también con `max{τ + ε, 0}`, que era la convención hasta el
30-sep-2026, para mostrar cuánto sesgaba. Escribe `salida/truncamiento.json`.
"""

from __future__ import annotations

import json

import numpy as np

import persona
import poblacion
import pve

SALIDA = persona.SALIDA


def main() -> None:
    out: dict = {"fase0": [], "fase0b": [], "fase1": []}

    esc0 = persona.escenario()
    for mu, sigma in ((1.0, 20.0), (10.0, 10.0), (10.0, 20.0)):
        fila = {"mu": mu, "sigma": sigma}
        for truncar in (True, False):
            r = persona.simular(esc0, sigma, mu, 0.5, np.random.default_rng(42), truncar=truncar)
            fila["truncado" if truncar else "sin_truncar"] = {
                "cuota_final": r["share_auto_ultimos_20"],
                "abandono": r["abandono"],
                "mala": r["share_fin_mala_suerte"],
                "buena": r["share_fin_buena_suerte"],
            }
        out["fase0"].append(fila)

    ref = pve.referencia()
    for mu, sigma in ((1.0, 40.0), (3.0, 40.0), (10.0, 20.0), (10.0, 40.0)):
        out["fase0b"].append(
            {
                "mu": mu,
                "sigma": sigma,
                "truncado": pve.simular(ref, "ambos", sigma, mu, 0.5, truncar=True)[
                    "cuota_mejor_ultimos"
                ],
                "sin_truncar": pve.simular(ref, "ambos", sigma, mu, 0.5)["cuota_mejor_ultimos"],
            }
        )

    esc1 = poblacion.Escenario()
    for mu in (1.0, 10.0):
        r0 = poblacion.simular(esc1, 0.0, mu, 0.5, np.random.default_rng(42))
        fila = {"mu": mu, "sigma": 20.0}
        for truncar in (True, False):
            r = poblacion.simular(esc1, 20.0, mu, 0.5, np.random.default_rng(42), truncar=truncar)
            u = poblacion.ULTIMOS
            fila["truncado" if truncar else "sin_truncar"] = {
                "delta_auto": r["split_ultimos"][0] - r0["split_ultimos"][0],
                "delta_abandono_metro": r["abandono_metro"] - r0["abandono_metro"],
                "delta_bienestar": float(
                    np.mean(r["bienestar_por_dia"][-u:]) - np.mean(r0["bienestar_por_dia"][-u:])
                ),
            }
        out["fase1"].append(fila)

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "truncamiento.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
