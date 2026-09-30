import { useTranslation } from "react-i18next";

import { CalibrationPanel } from "@/components/modules/CalibrationPanel";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { Panel } from "@/components/ui/Panel";
import { votClpHora } from "@/lib/agregados";
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
 * No agrega estado: edita `SimulationConfig.demand` (store de simulación) y
 * `LandUseConfig.mu` (store de suelo), los mismos que leen las otras páginas.
 * Las cifras derivadas se calculan acá por ser aritmética de presentación
 * (VoT = β_t/β_c·60, β_h = μ·λ_h); ningún número de modelo sale de TS.
 */

const STRATA: StratumId[] = [1, 2, 3];
const STR = ["alto", "medio", "bajo"] as const;
const VAR = ["var(--s1)", "var(--s2)", "var(--s3)"];

const fmtMoney = (v: number) => `$${Math.round(v).toLocaleString("es-CL")}`;

export function CalibrationPage() {
  const { t } = useTranslation("simulator");
  const config = useSimulationStore((s) => s.config);
  const setConfig = useSimulationStore((s) => s.setConfig);
  const luConfig = useLandUseStore((s) => s.config);
  const setLuConfig = useLandUseStore((s) => s.setConfig);

  const mu = luConfig.mu;
  const filas = STRATA.map((h) => {
    const e = config.demand.estratos[h];
    const lam = -e.betas.b_costo;
    const definido = lam > 0;
    return {
      vot: definido ? fmtMoney(votClpHora(config.demand, h)) : "—",
      lambda: definido ? `${(lam * 1e4).toFixed(2)}·10⁻⁴` : "—",
      ruido: definido ? fmtMoney(1 / (mu * lam)) : "—",
      auto: `${Math.round(e.prob_auto * 100)}%`,
    };
  });

  const perillas = ["b_costo", "b_tiempo", "asc", "prob_auto", "mu"] as const;

  return (
    <div className="page">
      <aside className="sidebar">
        <CalibrationPanel config={config} onChange={setConfig} defaultOpen />
        <CollapsibleSection
          title={t("calibration_page.mu_section")}
          meta={`μ=${mu.toFixed(3)}`}
          defaultOpen
        >
          <LabeledSlider
            label={t("land_use.param_mu")}
            value={mu}
            min={0.01}
            max={2}
            step={0.01}
            format={(v) => v.toFixed(3)}
            hint={t("land_use.mu_hint")}
            onChange={(v) => setLuConfig((c) => ({ ...c, mu: v }))}
          />
        </CollapsibleSection>
      </aside>

      <section className="main">
        <div className="hero">
          <div className="hero-head">
            <h1 className="hero-title">{t("calibration_page.title")}</h1>
            <div className="hero-sub">
              <span className="dot">●</span> {t("calibration_page.subtitle")}
            </div>
          </div>
          <p
            className="font-display text-justify"
            style={{
              fontSize: 14,
              lineHeight: 1.6,
              color: "var(--ink-2)",
              marginBottom: 0,
            }}
          >
            {t("calibration_page.intro")}
          </p>
        </div>

        <div className="panel-grid">
          <Panel
            n="01"
            title={t("calibration_page.table_title")}
            meta={`μ = ${mu.toFixed(3)}`}
            cls="col-12"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--rule)] text-[11px] uppercase tracking-wide text-[var(--muted)]">
                    <th className="py-1 text-left font-normal" />
                    {STR.map((s, k) => (
                      <th
                        key={s}
                        className="py-1 text-right font-normal"
                        style={{ color: VAR[k] }}
                      >
                        {t(`strata.${s}`)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(["vot", "lambda", "ruido", "auto"] as const).map((k) => (
                    <tr key={k} className="border-t border-[var(--rule)]">
                      <td className="py-1.5 pr-2">
                        {t(`calibration_page.row.${k}`)}
                        <div className="text-[10px] leading-snug text-muted">
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
                  <dt className="font-fig text-[11px] uppercase tracking-[0.06em] text-[var(--ink)]">
                    {t(`calibration_page.knob.${p}`)}
                  </dt>
                  <dd className="text-[12px] leading-snug text-[var(--ink-2)]">
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
