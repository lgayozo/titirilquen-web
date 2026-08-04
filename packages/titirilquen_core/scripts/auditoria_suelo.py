"""Auditoría de sensibilidad del módulo de USO DE SUELO.

Barre cada parámetro de `LandUseConfig` (y los de ciudad que lo afectan) y
reporta el efecto sobre los resultados observables, para verificar que el modelo
responde en la DIRECCIÓN y la MAGNITUD que la teoría predice.

Métricas reportadas
-------------------
- `dist_h`  distancia media al CBD del estrato h (km), ponderada por la
            ocupación esperada E[N_hi] = S_i·Q_hi (no muestreada).
- `disp_a`  desviación estándar de la localización del estrato ALTO (km), con el
            mismo ponderador. Separa «se mudó» (cambia dist) de «se desparramó»
            (cambia disp) — necesario para leer el artefacto de lambda (AU-06).
- `theil`   segregación de Theil entre celdas (0 = mezcla perfecta).
- `grad_p`  gradiente de precio: (p_CBD - p_periferia)/|p| relativo; en el modelo
            Alonso-Muth-Mills debe ser POSITIVO (el suelo central vale más).
- `dens_pk` densidad máxima por celda (hab/km).
- `iters`   iteraciones del punto fijo (diagnóstico de convergencia).

Correr desde packages/titirilquen_core:

    uv run python scripts/auditoria_suelo.py
"""

from __future__ import annotations

import numpy as np

from titirilquen_core.land_use.ciudad import LandUseCity
from titirilquen_core.land_use.config import LandUseConfig, LandUseStratumConfig

L = 201
CBD = L // 2
LARGO_KM = 20.0
SUMA_H = 36000
H_BASE = (int(SUMA_H * 0.10), int(SUMA_H * 0.40), int(SUMA_H * 0.50))


def base_cfg(**kw) -> LandUseConfig:
    cfg = LandUseConfig(
        H_por_estrato=H_BASE,
        estratos=(
            LandUseStratumConfig(y=3_500_000.0, alpha=6.5, rho=0.1),
            LandUseStratumConfig(y=1_500_000.0, alpha=6.0, rho=0.1),
            LandUseStratumConfig(y=500_000.0, alpha=5.5, rho=0.1),
        ),
        beta=1.0,
        forma="normal",
        oferta_sigma_frac=0.5,
    )
    # `model_copy(update=...)` NO valida: una clave inexistente se cuela como
    # atributo suelto y el barrido reporta un efecto que no existe. Paso de
    # verdad con el `solver` eliminado (las filas decian `utility_logit` y
    # corrian `logit`). Se chequea contra los campos declarados.
    desconocidas = set(kw) - set(LandUseConfig.model_fields)
    if desconocidas:
        raise ValueError(f"no son campos de LandUseConfig: {sorted(desconocidas)}")
    return cfg.model_copy(update=kw) if kw else cfg


def resolver_q(cfg: LandUseConfig) -> np.ndarray:
    """Matriz de composición Q[h, i] del equilibrio (sin métricas derivadas)."""
    ciudad = LandUseCity.build(L=L, CBD=CBD, cfg=cfg, ancho_celda_km=LARGO_KM / L)
    return np.asarray(ciudad.result.Q, dtype=float)


def resolver(cfg: LandUseConfig) -> dict:
    ciudad = LandUseCity.build(L=L, CBD=CBD, cfg=cfg, ancho_celda_km=LARGO_KM / L)
    oferta = np.asarray(ciudad.S, dtype=float)
    q_mat = np.asarray(ciudad.result.Q, dtype=float)  # [h, i]
    p = np.asarray(ciudad.result.p, dtype=float)
    dx = LARGO_KM / L
    dist_km = np.abs(np.arange(L) - CBD) * dx

    # Ocupación esperada por estrato y celda.
    ocup = oferta[None, :] * q_mat  # [h, i]
    tot_h = ocup.sum(axis=1)
    dist_h = np.where(tot_h > 0, (ocup * dist_km[None, :]).sum(axis=1) / np.maximum(tot_h, 1e-9), 0)

    # Dispersión del estrato alto: sd de su posición SIGNADA (no de |d| al CBD),
    # para que una asignación bimodal centro/periferia se lea como dispersa.
    pos_km = (np.arange(L) - CBD) * dx
    w = ocup[0] / max(float(ocup[0].sum()), 1e-9)
    mu = float((w * pos_km).sum())
    disp_a = float(np.sqrt((w * (pos_km - mu) ** 2).sum()))

    # Theil entre celdas sobre la composición por estrato.
    tot = ocup.sum()
    theil = 0.0
    if tot > 0:
        pi = tot_h / tot
        for i in range(L):
            n_i = ocup[:, i].sum()
            if n_i <= 0:
                continue
            for h in range(ocup.shape[0]):
                q = ocup[h, i] / n_i
                if q > 0 and pi[h] > 0:
                    theil += (n_i / tot) * q * np.log(q / pi[h])

    # Gradiente de precio centro-periferia, normalizado por el rango.
    p_cbd = float(p[CBD]) if np.isfinite(p[CBD]) else float("nan")
    p_per = float(np.nanmean([p[0], p[-1]]))
    rango = float(np.nanmax(p) - np.nanmin(p))
    grad = (p_cbd - p_per) / rango if rango > 1e-12 else 0.0

    return {
        "dist": dist_h,
        "disp_a": disp_a,
        "theil": theil,
        "grad_p": grad,
        "dens_pk": float(np.max(ciudad.densidad_por_celda())),
        "iters": int(getattr(ciudad.result, "iterations", -1)),
    }


def fila(etiqueta: str, r: dict) -> str:
    d = r["dist"]
    return (
        f"{etiqueta:<22} {d[0]:>7.2f} {d[1]:>7.2f} {d[2]:>7.2f} {r['disp_a']:>7.2f} "
        f"{r['theil']:>8.4f} {r['grad_p']:>+8.2f} {r['dens_pk']:>9.0f} {r['iters']:>6}"
    )


def encabezado(titulo: str) -> None:
    print(f"\n### {titulo}")
    print(
        f"{'escenario':<22} {'d_alto':>7} {'d_medio':>7} {'d_bajo':>7} {'disp_a':>7} "
        f"{'theil':>8} {'grad_p':>8} {'dens_pk':>9} {'iters':>6}"
    )
    print("-" * 90)


def barrer(titulo: str, casos: list[tuple[str, LandUseConfig]]) -> None:
    encabezado(titulo)
    for etiqueta, cfg in casos:
        try:
            print(fila(etiqueta, resolver(cfg)))
        except Exception as e:
            print(f"{etiqueta:<22} ERROR {type(e).__name__}: {e}")


def _estratos(alphas=None, rhos=None, lambdas=None, ys=None):
    a = alphas or [6.5, 6.0, 5.5]
    r = rhos or [0.1, 0.1, 0.1]
    lam = lambdas or [1.0, 1.0, 1.0]
    y = ys or [3_500_000.0, 1_500_000.0, 500_000.0]
    return tuple(
        LandUseStratumConfig(y=y[i], alpha=a[i], rho=r[i], **{"lambda": lam[i]}) for i in range(3)
    )


def equivalencia_lambda() -> None:
    """Muestra POR QUE lambda es un artefacto: la puja es `y + f/lambda` con
    `f = -alpha*T - rho*dens`, asi que dividir por lambda_h es IDENTICO a
    re-escalar (alpha_h, rho_h) por 1/lambda_h. No hay parametro nuevo."""
    print("\n### 4b. lambda == re-escalar (alpha, rho) por 1/lambda — ¿identico?")
    print(f"  {'lambda':>7} {'alpha_ef':>9} {'rho_ef':>8} {'max|dQ|':>11}  veredicto")
    for lam in (0.4, 0.5, 1.5, 3.0):
        q_lam = np.asarray(resolver_q(base_cfg(estratos=_estratos(lambdas=[lam, 1, 1]))))
        q_pref = np.asarray(
            resolver_q(
                base_cfg(
                    estratos=_estratos(alphas=[6.5 / lam, 6.0, 5.5], rhos=[0.1 / lam, 0.1, 0.1])
                )
            )
        )
        d = float(np.abs(q_lam - q_pref).max())
        print(
            f"  {lam:>7} {6.5 / lam:>9.2f} {0.1 / lam:>8.3f} {d:>11.3e}  "
            f"{'IDENTICO' if d < 1e-12 else 'DIFIERE'}"
        )


def main() -> None:
    print("AUDITORÍA — MÓDULO DE USO DE SUELO")
    print(f"Base: L={L} celdas · {LARGO_KM:.0f} km · ΣH={SUMA_H} · shares 10/40/50")
    print("Teoría (Alonso-Muth-Mills): quien más valora el acceso (alpha alto) debe")
    print("localizarse MÁS CERCA del CBD; el precio debe caer con la distancia.")

    barrer(
        "1. alpha (peso del tiempo de viaje, utiles/min) — palanca de Alonso",
        [
            ("base 6.5/6.0/5.5", base_cfg()),
            ("alto=12 bajo=3", base_cfg(estratos=_estratos(alphas=[12, 6, 3]))),
            ("alto=3 bajo=12", base_cfg(estratos=_estratos(alphas=[3, 6, 12]))),
            ("todos iguales 6", base_cfg(estratos=_estratos(alphas=[6, 6, 6]))),
            ("alto=20 bajo=1", base_cfg(estratos=_estratos(alphas=[20, 6, 1]))),
        ],
    )

    barrer(
        "2. rho (penalización de densidad)",
        [
            ("base 0.1", base_cfg()),
            ("todos 0 (sin penal.)", base_cfg(estratos=_estratos(rhos=[0, 0, 0]))),
            ("todos 0.5", base_cfg(estratos=_estratos(rhos=[0.5, 0.5, 0.5]))),
            ("alto 0.5, resto 0", base_cfg(estratos=_estratos(rhos=[0.5, 0, 0]))),
        ],
    )

    barrer(
        "3. beta (escala del logit de subasta)",
        [
            ("beta 0.1", base_cfg(beta=0.1)),
            ("beta 0.5", base_cfg(beta=0.5)),
            ("beta 1 (base)", base_cfg()),
            ("beta 3", base_cfg(beta=3.0)),
            ("beta 10", base_cfg(beta=10.0)),
        ],
    )

    # LIMITACION DEL MODELO, no un parametro de comportamiento: `solve_logit`
    # aplica un beta uniforme sobre la puja `y + f/lambda`, asi que dividir por
    # lambda_h escala el RUIDO de eleccion de ese estrato (~1/(beta·lambda)). Lo
    # que se observa es ruido. La correccion es el logit heterocedastico
    # (Suelo.tex 2.7), NO implementado. Se barre fino para exhibir que el efecto
    # ni siquiera es monotono — la firma de un artefacto, no de una preferencia.
    barrer(
        "4. lambda (utilidad marginal del ingreso) — RUIDO, limitación D-08",
        [
            (f"alto {lam}", base_cfg(estratos=_estratos(lambdas=[lam, 1, 1])))
            for lam in (0.4, 0.5, 1.0, 1.5, 2.0, 3.0)
        ],
    )

    equivalencia_lambda()

    barrer(
        "5. y (ingreso) — debe ser INERTE en la asignación (se absorbe en ū)",
        [
            ("base 3.5M/1.5M/0.5M", base_cfg()),
            ("todos 1M", base_cfg(estratos=_estratos(ys=[1e6, 1e6, 1e6]))),
            ("alto 100M", base_cfg(estratos=_estratos(ys=[1e8, 1.5e6, 0.5e6]))),
        ],
    )

    barrer(
        "6. forma de la oferta",
        [
            (f, base_cfg(forma=f))
            for f in ("normal", "uniforme", "exponencial", "meseta", "bimodal", "valle")
        ],
    )

    barrer(
        "7. oferta_sigma_frac (compacidad)",
        [(f"sigma {s}", base_cfg(oferta_sigma_frac=s)) for s in (0.15, 0.3, 0.5, 0.8, 1.2)],
    )

    barrer(
        "8. composición de estratos (H)",
        [
            ("10/40/50 (base)", base_cfg()),
            (
                "mayoría alto",
                base_cfg(H_por_estrato=(int(SUMA_H * 0.8), int(SUMA_H * 0.1), int(SUMA_H * 0.1))),
            ),
            (
                "mayoría bajo",
                base_cfg(H_por_estrato=(int(SUMA_H * 0.1), int(SUMA_H * 0.1), int(SUMA_H * 0.8))),
            ),
            ("tercios", base_cfg(H_por_estrato=(SUMA_H // 3, SUMA_H // 3, SUMA_H // 3))),
        ],
    )

    barrer(
        "9. escala de población (ΣH) — ¿invariante la asignación?",
        [
            (f"ΣH={n}", base_cfg(H_por_estrato=(int(n * 0.1), int(n * 0.4), int(n * 0.5))))
            for n in (9000, 36000, 144000)
        ],
    )

    # Hubo un barrido «10. solver» comparando `logit` vs `utility_logit`. El
    # segundo decia corregir el lambda heterogeneo y solo lo dejaba inerte: se
    # elimino del core (AU-07), y con el este barrido.
    barrer(
        "10. vestigiales (densidad_max/min) — deben ser INERTES",
        [
            ("base 800/200", base_cfg()),
            ("9999/1", base_cfg(densidad_max=9999.0, densidad_min=1.0)),
        ],
    )


if __name__ == "__main__":
    main()
