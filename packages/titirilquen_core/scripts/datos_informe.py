"""Datos y graficos del informe docente (docs/informe-downs-thomson.html).

Dos productos, ambos sobre el DEFAULT vigente (K=1000, frec_min=2):

1. BARRIDO CENTRAL: pistas 1-8 x {montecarlo, expected, wardrop}, verificado
   fino (max_iter=120, tol=0.02). Para cada corrida: reparto, espera, bienestar
   emparejado y COSTO SOCIAL por viajero — tiempo valorado al VST del SNI 2026
   (3.338 $/h; espera y acceso x2 por su ponderador) mas el gasto monetario.
   Convencion declarada: los modos bici y caminata se valoran a VST x1 (la
   tabla del SNI cubre las etapas del transporte publico). Agregado de ciudad y
   por estrato (mismo VST unico: las diferencias son de composicion).
   Emite ademas los graficos SVG del informe.

2. SENSIBILIZACION DE LA CALIBRACION: variantes realistas de los parametros de
   demanda (razon de espera 1.5x/2.5x, VoT +-30%, ASC del auto +10/+30 min,
   escala del logit x0.75/x1.5) y el veredicto Downs-Thomson de cada una bajo
   expected y wardrop, con el mismo detector de mecanismo de
   buscar_downs_thomson.py.

Correr desde packages/titirilquen_core (~5 min):

    uv run python scripts/datos_informe.py
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

import buscar_downs_thomson as bdt

VST_H = 3338.0  # $/h-pax, SNI 2026, viaje urbano en vehiculo
PONDERADOR_ESPERA = 2.0  # SNI Tabla 2.1
PONDERADOR_ACCESO = 2.0
SALIDA = Path(__file__).parent.parent.parent.parent / "docs" / "_datos_informe"


def costo_social(sim, tr) -> dict:
    """Costo social por viajero ($/viaje): ciudad y por estrato."""
    last = tr.iteraciones[-1]
    n = sim.city.n_celdas
    dx = sim.city.largo_ciudad_km / n
    dist = np.abs(np.arange(n) - n // 2) * dx
    gl = sim.demand.globales
    vst_min = VST_H / 60.0
    t_cam = dist / gl.v_caminata * 60
    tiempo_social = {
        0: last.t_auto * vst_min,
        1: (
            last.t_tren_viaje
            + PONDERADOR_ESPERA * last.t_tren_espera
            + PONDERADOR_ACCESO * last.t_tren_acceso
        )
        * vst_min,
        2: last.t_bici * vst_min,
        3: t_cam * vst_min,
    }
    dinero = {
        0: dist * gl.costo_combustible_km + gl.costo_parking,
        1: np.full(n, float(gl.costo_tarifa_metro)),
        2: np.zeros(n),
        3: np.zeros(n),
    }
    de = tr.demanda_estrato
    por_h = {}
    tot_t = tot_d = tot_den = 0.0
    for h in (1, 2, 3):
        num_t = num_d = den = 0.0
        for m in range(4):
            d = de[h - 1][m]
            num_t += float((d * tiempo_social[m]).sum())
            num_d += float((d * dinero[m]).sum())
            den += float(d.sum())
        por_h[h] = (num_t + num_d) / max(den, 1)
        tot_t += num_t
        tot_d += num_d
        tot_den += den
    den = max(tot_den, 1)
    # La descomposicion tiempo/dinero importa: un alza de costo social por puro
    # DINERO (mas parking pagado) es una transferencia, no Downs-Thomson; la
    # paradoja exige que suba el componente de TIEMPO valorado.
    return {
        "ciudad": (tot_t + tot_d) / den,
        "ciudad_tiempo": tot_t / den,
        "ciudad_dinero": tot_d / den,
        **{f"h{h}": por_h[h] for h in (1, 2, 3)},
    }


def corre(esc: dict, metodo: str, pistas: int, max_iter=120, tol=0.02) -> dict:
    sim = bdt.config_de(esc, metodo, pistas).model_copy(
        update={"max_iter": max_iter, "tolerance": tol}
    )
    tr = bdt.ConvergenceTrace()
    for _ in bdt.iter_msa_desde_suelo(sim, bdt.lu_de(esc), tr, localizacion="equilibrio"):
        pass
    last = tr.iteraciones[-1]
    sp = last.modal_split
    t = sum(sp.values()) or 1
    w_ls, w_mx = bdt.bienestar_min(sim, tr)
    return {
        "auto": 100 * sp.get("Auto", 0) / t,
        "metro": 100 * sp.get("Metro", 0) / t,
        "otros": 100 * (sp.get("Bici", 0) + sp.get("Caminata", 0)) / t,
        "f_op": last.frecuencia_metro,
        "espera": float(last.t_tren_espera.max()),
        "w": w_mx if metodo == "wardrop" else w_ls,
        "cs": costo_social(sim, tr),
        "conv": tr.converged,
    }


# ---------------------------------------------------------------- SVG
def svg_lineas(titulo, ylabel, xs, series, ancho=640, alto=340) -> str:
    """Grafico de lineas minimo, autocontenido, estilo del informe."""
    ml, mr, mt, mb = 62, 16, 34, 40
    w, h = ancho - ml - mr, alto - mt - mb
    ys = [p for _, _, _, pts in series for p in pts]
    y0, y1 = min(ys), max(ys)
    margen = (y1 - y0) * 0.12 or 1.0
    y0, y1 = y0 - margen, y1 + margen
    x0, x1 = min(xs), max(xs)

    def ex(v):
        return ml + (v - x0) / (x1 - x0) * w

    def ey(v):
        return mt + (1 - (v - y0) / (y1 - y0)) * h

    p = [
        f'<svg viewBox="0 0 {ancho} {alto}" xmlns="http://www.w3.org/2000/svg" role="img" '
        f'style="max-width:100%;height:auto;font-family:Segoe UI,system-ui,sans-serif">',
        f'<text x="{ml}" y="18" font-size="13" font-weight="600" fill="#1a1a1a">{titulo}</text>',
    ]
    # rejilla y eje Y
    for k in range(5):
        yv = y0 + (y1 - y0) * k / 4
        yy = ey(yv)
        p.append(
            f'<line x1="{ml}" y1="{yy:.1f}" x2="{ancho - mr}" y2="{yy:.1f}" '
            f'stroke="#d8d4cc" stroke-width="0.7"/>'
        )
        p.append(
            f'<text x="{ml - 6}" y="{yy + 3.5:.1f}" font-size="10.5" '
            f'text-anchor="end" fill="#6b6b6b">{yv:,.0f}</text>'
        )
    for xv in xs:
        p.append(
            f'<text x="{ex(xv):.1f}" y="{alto - mb + 16}" font-size="10.5" '
            f'text-anchor="middle" fill="#6b6b6b">{xv}</text>'
        )
    p.append(
        f'<text x="{ml + w / 2:.0f}" y="{alto - 6}" font-size="11" '
        f'text-anchor="middle" fill="#444">pistas por sentido</text>'
    )
    p.append(
        f'<text x="14" y="{mt + h / 2:.0f}" font-size="11" text-anchor="middle" fill="#444" '
        f'transform="rotate(-90 14 {mt + h / 2:.0f})">{ylabel}</text>'
    )
    for nombre, color, dash, pts in series:
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{ex(x):.1f},{ey(v):.1f}"
            for i, (x, v) in enumerate(zip(xs, pts, strict=True))
        )
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.2"{extra}/>')
        for x, v in zip(xs, pts, strict=True):
            p.append(f'<circle cx="{ex(x):.1f}" cy="{ey(v):.1f}" r="2.6" fill="{color}"/>')
        p.append(
            f'<text x="{ex(xs[-1]) - 2:.1f}" y="{ey(pts[-1]) - 7:.1f}" font-size="10.5" '
            f'text-anchor="end" fill="{color}" font-weight="600">{nombre}</text>'
        )
    p.append("</svg>")
    return "\n".join(p)


def main() -> None:
    SALIDA.mkdir(exist_ok=True)
    pistas_barrido = [1, 2, 3, 4, 6, 8]

    # ---------------- 1. barrido central sobre el default
    datos: dict = {"pistas": pistas_barrido, "metodos": {}}
    for metodo in ("montecarlo", "expected", "wardrop"):
        filas = [corre({}, metodo, p) for p in pistas_barrido]
        datos["metodos"][metodo] = filas
        print(f"\n### default · {metodo}")
        print(
            f"{'pistas':>7}{'auto':>8}{'metro':>8}{'f_op':>7}{'espera':>8}"
            f"{'bienestar':>11}{'CS ciudad':>11}{'alto':>9}{'medio':>9}{'bajo':>9}"
        )
        for p, r in zip(pistas_barrido, filas, strict=True):
            cs = r["cs"]
            print(
                f"{p:>7}{r['auto']:>8.2f}{r['metro']:>8.2f}{r['f_op']:>7.1f}{r['espera']:>8.2f}"
                f"{r['w']:>11.3f}{cs['ciudad']:>11.0f}{cs['ciudad_tiempo']:>9.0f}{cs['ciudad_dinero']:>9.0f}"
                f"{cs['h1']:>9.0f}{cs['h2']:>9.0f}{cs['h3']:>9.0f}"
                + ("" if r["conv"] else "  [NO CONV]")
            )

    # graficos
    colores_m = {
        "montecarlo": ("#8a8a8a", "5 4"),
        "expected": ("#2e6e4e", ""),
        "wardrop": ("#b4532a", ""),
    }
    g1 = svg_lineas(
        "Costo social por viajero según capacidad vial — los tres equilibrios",
        "costo social ($/viaje)",
        pistas_barrido,
        [
            (m, colores_m[m][0], colores_m[m][1], [r["cs"]["ciudad"] for r in datos["metodos"][m]])
            for m in ("montecarlo", "expected", "wardrop")
        ],
    )
    col_h = {
        "h1": ("estrato alto", "#b4532a"),
        "h2": ("estrato medio", "#4a6fa5"),
        "h3": ("estrato bajo", "#2e6e4e"),
    }
    g2 = svg_lineas(
        "Costo social por estrato — Wardrop (equilibrio determinístico)",
        "costo social ($/viaje)",
        pistas_barrido,
        [
            (nom, c, "", [r["cs"][k] for r in datos["metodos"]["wardrop"]])
            for k, (nom, c) in col_h.items()
        ]
        + [("ciudad", "#1a1a1a", "5 4", [r["cs"]["ciudad"] for r in datos["metodos"]["wardrop"]])],
    )
    g3 = svg_lineas(
        "Costo social por estrato — Expected (equilibrio logit)",
        "costo social ($/viaje)",
        pistas_barrido,
        [
            (nom, c, "", [r["cs"][k] for r in datos["metodos"]["expected"]])
            for k, (nom, c) in col_h.items()
        ]
        + [("ciudad", "#1a1a1a", "5 4", [r["cs"]["ciudad"] for r in datos["metodos"]["expected"]])],
    )
    (SALIDA / "graficos.html").write_text(
        '<div class="grafico">' + g1 + "</div>\n"
        '<div class="grafico">' + g2 + "</div>\n"
        '<div class="grafico">' + g3 + "</div>\n",
        encoding="utf-8",
    )

    # ---------------- 2. sensibilizacion de la calibracion
    variantes = [
        ("espera 1.5x (piso empirico)", {"espera_x": 1.5}),
        ("espera 2.5x (techo empirico)", {"espera_x": 2.5}),
        ("VoT +30%", {"b_costo_x": 0.77}),
        ("VoT -30%", {"b_costo_x": 1.43}),
        ("ASC auto +10 min", {"asc_auto_min": 10.0}),
        ("ASC auto +30 min", {"asc_auto_min": 30.0}),
        ("escala logit x1.5 (menos ruido)", {"escala": 1.5}),
        ("escala logit x0.75 (mas ruido)", {"escala": 0.75}),
    ]
    p4 = [1, 2, 3, 4]
    print("\n\n### SENSIBILIZACION DE LA CALIBRACION (default K=1000)")
    print(f"{'variante':<34}{'expected':<26}{'wardrop':<26}")
    print("-" * 86)
    resumen = []
    for nombre, mods in variantes:
        celda = {}
        for metodo in ("expected", "wardrop"):
            filas = [corre_variante(mods, metodo, p) for p in p4]
            tramos = []
            for a, b in itertools.pairwise(filas):
                d_w = b["w"] - a["w"]
                if (
                    d_w < -0.01
                    and b["auto"] > a["auto"] + 0.05
                    and b["metro"] < a["metro"] - 0.05
                    and b["espera"] > a["espera"]
                    and abs(b["otros"] - a["otros"]) <= 0.5 * (b["auto"] - a["auto"]) + 0.1
                ):
                    tramos.append(d_w)
            celda[metodo] = f"PARADOJA ({min(tramos):+.2f} min)" if tramos else "sin paradoja"
        print(f"{nombre:<34}{celda['expected']:<26}{celda['wardrop']:<26}")
        resumen.append((nombre, celda))
    datos["sensibilidad"] = [(n, c["expected"], c["wardrop"]) for n, c in resumen]
    (SALIDA / "datos.json").write_text(json.dumps(datos, indent=1), encoding="utf-8")
    print(f"\nEscrito: {SALIDA / 'graficos.html'} y datos.json")


def corre_variante(mods: dict, metodo: str, pistas: int) -> dict:
    """Variante de calibracion sobre el default: muta betas y corre."""
    sim = bdt.config_de({}, metodo, pistas).model_copy(update={"max_iter": 60, "tolerance": 0.05})
    est = dict(sim.demand.estratos)
    for h in (1, 2, 3):
        c = est[h]
        b = c.betas
        upd: dict = {}
        if "espera_x" in mods:
            upd["b_tiempo_espera"] = b.b_tiempo_viaje * mods["espera_x"]
        if "b_costo_x" in mods:
            upd["b_costo"] = b.b_costo * mods["b_costo_x"]
        if "asc_auto_min" in mods:
            upd["asc_auto"] = b.asc_metro - mods["asc_auto_min"] * b.b_tiempo_viaje
        if "escala" in mods:
            e = mods["escala"]
            for campo in (
                "asc_auto",
                "asc_metro",
                "asc_bici",
                "asc_caminata",
                "b_tiempo_viaje",
                "b_costo",
                "b_tiempo_espera",
                "b_tiempo_acceso",
                "b_tiempo_caminata",
            ):
                upd[campo] = upd.get(campo, getattr(b, campo)) * e
            p = b.penalizaciones_fisicas
            upd["penalizaciones_fisicas"] = p.model_copy(
                update={f: getattr(p, f) * e for f in type(p).model_fields}
            )
        est[h] = c.model_copy(update={"betas": b.model_copy(update=upd)})
    sim = sim.model_copy(update={"demand": sim.demand.model_copy(update={"estratos": est})})
    tr = bdt.ConvergenceTrace()
    for _ in bdt.iter_msa_desde_suelo(sim, bdt.lu_de({}), tr, localizacion="equilibrio"):
        pass
    last = tr.iteraciones[-1]
    sp = last.modal_split
    t = sum(sp.values()) or 1
    w_ls, w_mx = bdt.bienestar_min(sim, tr)
    return {
        "auto": 100 * sp.get("Auto", 0) / t,
        "metro": 100 * sp.get("Metro", 0) / t,
        "otros": 100 * (sp.get("Bici", 0) + sp.get("Caminata", 0)) / t,
        "espera": float(last.t_tren_espera.max()),
        "w": w_mx if metodo == "wardrop" else w_ls,
    }


if __name__ == "__main__":
    main()
