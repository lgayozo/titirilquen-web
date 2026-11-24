import { useTranslation } from "react-i18next";

import {
  CalibrationPanel,
  NumberField,
} from "@/components/modules/CalibrationPanel";
import { IngresoPanel } from "@/components/modules/IngresoPanel";
import { PreciosSocialesPanel } from "@/components/modules/PreciosSocialesPanel";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { Panel } from "@/components/ui/Panel";
import { PorQue } from "@/components/ui/PorQue";
import { votClpHora } from "@/lib/agregados";
import {
  conMultiplos,
  MULTIPLOS_CALIBRADOS,
  multiplosDe,
  type MultiplosVot,
} from "@/lib/heterogeneidadLambda";
import { COLOR_ESTRATO, fmtDecimal, fmtPct, fmtPesos } from "@/lib/modos";
import type { StratumId } from "@/lib/types";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

/**
 * Página de CALIBRACIÓN: el modelo de comportamiento del hogar, antes que
 * cualquier módulo. Existe porque los betas no son de Transporte: un hogar
 * tiene UNA función de utilidad (D-34), y la misma calibración fija el reparto
 * modal, la accesibilidad T con que se puja por suelo y, desde el schema v6,
 * el λ_h = |b_costo_h| de la puja. Dentro de Transporte quedaba escondida
 * como un panel más, y no lo es.
 *
 * No agrega estado: edita `SimulationConfig.demand` (store de simulación), el
 * mismo que leen las otras páginas. Las cifras derivadas se calculan acá por
 * ser aritmética de presentación (VoT = β_t/β_c·60, β_h = μ·λ_h); ningún
 * número de modelo sale de TS.
 *
 * μ es `LandUseConfig.mu`, valor de escenario desde el schema v10 (en v7–v9
 * fue la constante 1/√44); se lee del store de suelo.
 */

const STRATA: StratumId[] = [1, 2, 3];
const STR = ["alto", "medio", "bajo"] as const;
const VAR = STRATA.map((h) => COLOR_ESTRATO[h]);

const fmtMoney = fmtPesos;

export function CalibrationPage() {
  const { t } = useTranslation("simulator");
  const config = useSimulationStore((s) => s.config);
  const setConfig = useSimulationStore((s) => s.setConfig);

  const mu = useLandUseStore((s) => s.config.mu);
  const landUse = useLandUseStore((s) => s.config);
  const setLandUse = useLandUseStore((s) => s.setConfig);
  // Cuántas veces vale el tiempo del medio y del alto respecto del bajo.
  const multiplos = multiplosDe(config.demand);
  const setMultiplos = (m: MultiplosVot) =>
    setConfig((c) => conMultiplos(c, m));
  const esIguales = multiplos?.medio === 1 && multiplos.alto === 1;
  const esCalibrada =
    multiplos != null &&
    Math.abs(multiplos.medio - MULTIPLOS_CALIBRADOS.medio) < 1e-9 &&
    Math.abs(multiplos.alto - MULTIPLOS_CALIBRADOS.alto) < 1e-9;
  const filas = STRATA.map((h) => {
    const e = config.demand.estratos[h];
    const lam = -e.betas.b_costo;
    const definido = lam > 0;
    return {
      vot: definido ? fmtMoney(votClpHora(config.demand, h)) : "—",
      lambda: definido ? `${fmtDecimal(lam * 1e4, 2)}·10⁻⁴` : "—",
      ruido: definido ? fmtMoney(1 / (mu * lam)) : "—",
      auto: fmtPct(e.prob_auto * 100, 0),
    };
  });

  const perillas = ["b_costo", "b_tiempo", "asc", "prob_auto"] as const;

  return (
    <div className="page">
      <aside className="sidebar">
        <CollapsibleSection
          title={t("calibration_page.het_section")}
          meta={
            multiplos == null
              ? "—"
              : `${fmtDecimal(multiplos.alto, 2)} : ${fmtDecimal(multiplos.medio, 2)} : 1`
          }
          defaultOpen
        >
          <p className="mb-2 text-etiqueta leading-snug text-muted">
            {t("calibration_page.het_corto")}
          </p>
          {/* Dos múltiplos del estrato bajo, no un exponente: «el medio vale
              2 veces el bajo» se lee directo. El medio queda fijo; al mover
              un múltiplo cambian el bajo y el alto. */}
          <div className="flex flex-col gap-1.5">
            <NumberField
              label={t("calibration_page.het_medio")}
              value={Number((multiplos?.medio ?? 1).toFixed(4))}
              step={0.1}
              onChange={(v) =>
                setMultiplos({
                  medio: Math.max(0.05, v),
                  alto: multiplos?.alto ?? 1,
                })
              }
            />
            <NumberField
              label={t("calibration_page.het_alto")}
              value={Number((multiplos?.alto ?? 1).toFixed(4))}
              step={0.1}
              onChange={(v) =>
                setMultiplos({
                  medio: multiplos?.medio ?? 1,
                  alto: Math.max(0.05, v),
                })
              }
            />
          </div>
          {/* El efecto, a la vista: el VoT que resulta para cada estrato. */}
          <dl className="mt-2 grid grid-cols-3 gap-2 text-etiqueta tabular-nums">
            {STRATA.map((h, i) => (
              <div key={h}>
                <dt className="text-muted">{t(`strata.${STR[i]}`)}</dt>
                <dd className="font-fig text-[var(--ink)]">
                  {filas[i]!.vot}
                  {filas[i]!.vot !== "—" && "/h"}
                </dd>
              </div>
            ))}
          </dl>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              className={esIguales ? "chip-toggle active" : "chip-toggle"}
              style={{ flex: 1 }}
              onClick={() => setMultiplos({ medio: 1, alto: 1 })}
            >
              {t("calibration_page.het_iguales")}
            </button>
            <button
              type="button"
              className={esCalibrada ? "chip-toggle active" : "chip-toggle"}
              style={{ flex: 1 }}
              onClick={() => setMultiplos(MULTIPLOS_CALIBRADOS)}
            >
              {t("calibration_page.het_calibrada", {
                medio: fmtDecimal(MULTIPLOS_CALIBRADOS.medio, 0),
                alto: fmtDecimal(MULTIPLOS_CALIBRADOS.alto, 0),
              })}
            </button>
          </div>
          <PorQue>{t("calibration_page.het_porque")}</PorQue>
        </CollapsibleSection>
        <CalibrationPanel config={config} onChange={setConfig} defaultOpen />
        <CollapsibleSection
          title={t("calibration_page.mu_section")}
          meta={t("calibration_page.mu_meta", { mu: fmtDecimal(mu, 2) })}
          defaultOpen
        >
          <div className="font-fig text-ayuda tabular-nums text-[var(--ink)]">
            μ = {fmtDecimal(mu, 2)}
          </div>
          <p className="mt-1 text-etiqueta leading-snug text-muted">
            {t("calibration_page.mu_corto")}
          </p>
          <PorQue>{t("calibration_page.mu_porque")}</PorQue>
        </CollapsibleSection>
        <IngresoPanel config={landUse} onChange={setLandUse} />
        <PreciosSocialesPanel config={config} onChange={setConfig} />
      </aside>

      <section className="main">
        <div className="hero">
          <div className="hero-head">
            <div>
              <h1 className="hero-title">{t("calibration_page.title")}</h1>
              <p className="hero-sub" style={{ margin: "6px 0 0" }}>
                {t("calibration_page.subtitle")}
              </p>
            </div>
          </div>
          <p
            className="font-display text-justify"
            style={{
              fontSize: "var(--fs-cuerpo)",
              lineHeight: 1.6,
              color: "var(--ink-2)",
              marginBottom: 0,
            }}
          >
            {t("calibration_page.intro_corto")}
          </p>
          <PorQue>{t("calibration_page.intro_porque")}</PorQue>
        </div>

        <div className="panel-grid">
          <Panel
            n="01"
            title={t("calibration_page.table_title")}
            meta={`μ = ${fmtDecimal(mu, 2)}`}
            cls="col-12"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-cuerpo">
                <thead>
                  <tr className="border-b border-[var(--rule)] text-etiqueta text-[var(--muted)]">
                    <th className="py-1 text-left font-normal" />
                    {STR.map((s, k) => (
                      // El color del estrato va en el punto, no en el texto: el
                      // beige del estrato bajo no alcanza contraste como letra.
                      <th key={s} className="py-1 text-right font-normal">
                        <span className="inline-flex items-center gap-1.5">
                          <span
                            className="kpi-dot"
                            style={{ background: VAR[k] }}
                            aria-hidden
                          />
                          {t(`strata.${s}`)}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(["vot", "lambda", "ruido", "auto"] as const).map((k) => (
                    <tr key={k} className="border-t border-[var(--rule)]">
                      <td className="py-1.5 pr-2">
                        {t(`calibration_page.row.${k}`)}
                        <div className="text-etiqueta leading-snug text-muted">
                          {t(`calibration_page.row_hint.${k}`)}
                        </div>
                      </td>
                      {filas.map((f, i) => (
                        <td
                          key={i}
                          className="py-1.5 text-right align-top font-fig tabular-nums"
                        >
                          {f[k]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <Panel
            n="02"
            title={t("calibration_page.knobs_title")}
            meta={t("calibration_page.knobs_meta")}
            cls="col-12"
          >
            <dl className="flex flex-col gap-2">
              {perillas.map((p) => (
                <div key={p}>
                  <dt className="text-etiqueta text-[var(--ink)]">
                    {t(`calibration_page.knob.${p}`)}
                  </dt>
                  <dd className="text-etiqueta leading-snug text-[var(--ink-2)]">
                    {t(`calibration_page.knob_effect.${p}`)}
                  </dd>
                </div>
              ))}
            </dl>
            <p
              className="kpi-caption"
              style={{ marginTop: 10, marginBottom: 0 }}
            >
              {t("calibration_page.stale_note")}
            </p>
          </Panel>
        </div>
      </section>
    </div>
  );
}
