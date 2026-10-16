import { useTranslation } from "react-i18next";

import { CalibrationPanel } from "@/components/modules/CalibrationPanel";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { Panel } from "@/components/ui/Panel";
import { PorQue } from "@/components/ui/PorQue";
import { votClpHora } from "@/lib/agregados";
import { conHeterogeneidad, sDeDemanda } from "@/lib/heterogeneidadLambda";
import { COLOR_ESTRATO } from "@/lib/modos";
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

const fmtMoney = (v: number) => `$${Math.round(v).toLocaleString("es-CL")}`;

export function CalibrationPage() {
  const { t } = useTranslation("simulator");
  const config = useSimulationStore((s) => s.config);
  const setConfig = useSimulationStore((s) => s.setConfig);

  const mu = useLandUseStore((s) => s.config.mu);
  // Heterogeneidad de λ: `null` si los b_costo no caen en la curva.
  const sLam = sDeDemanda(config.demand);
  const setS = (v: number) => setConfig((c) => conHeterogeneidad(c, v));
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

  const perillas = ["b_costo", "b_tiempo", "asc", "prob_auto"] as const;

  return (
    <div className="page">
      <aside className="sidebar">
        <CollapsibleSection
          title={t("calibration_page.het_section")}
          meta={
            sLam == null
              ? t("calibration_page.het_custom")
              : `s=${sLam.toFixed(2)}`
          }
          defaultOpen
        >
          <LabeledSlider
            label={t("calibration_page.het_label")}
            value={sLam ?? 1}
            min={0}
            max={2}
            step={0.05}
            format={(v) =>
              sLam == null ? t("calibration_page.het_custom") : v.toFixed(2)
            }
            hint={t("calibration_page.het_corto")}
            onChange={setS}
          />
          <PorQue>{t("calibration_page.het_porque")}</PorQue>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              className="chip-toggle"
              style={{ flex: 1 }}
              onClick={() => setS(0)}
            >
              {t("calibration_page.het_iguales")}
            </button>
            <button
              type="button"
              className="chip-toggle"
              style={{ flex: 1 }}
              onClick={() => setS(1)}
            >
              {t("calibration_page.het_calibrada")}
            </button>
          </div>
        </CollapsibleSection>
        <CalibrationPanel config={config} onChange={setConfig} defaultOpen />
        <CollapsibleSection
          title={t("calibration_page.mu_section")}
          meta={t("calibration_page.mu_meta", { mu: mu.toFixed(2) })}
          defaultOpen
        >
          <div className="font-fig text-ayuda tabular-nums text-[var(--ink)]">
            μ = {mu.toFixed(2)}
          </div>
          <p className="mt-1 text-etiqueta leading-snug text-muted">
            {t("calibration_page.mu_corto")}
          </p>
          <PorQue>{t("calibration_page.mu_porque")}</PorQue>
        </CollapsibleSection>
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
            meta={`μ = ${mu.toFixed(2)}`}
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
