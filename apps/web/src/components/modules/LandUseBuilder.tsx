import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { Section } from "@/components/ui/Section";
import type { LandUseConfig } from "@/lib/types-v2";

interface LandUseBuilderProps {
  config: LandUseConfig;
  onChange: (updater: (prev: LandUseConfig) => LandUseConfig) => void;
}

/**
 * Panel de parámetros del modelo de uso de suelo. Permite ajustar:
 *   - Totales por estrato (H)
 *   - α_h: peso del costo de transporte
 *   - ρ_h: peso de penalización de densidad
 *   - β: sensibilidad logit
 *   - Solver (logit / frechet — didáctico)
 */
export function LandUseBuilder({ config, onChange }: LandUseBuilderProps) {
  const { t } = useTranslation("simulator");

  const setStratum = (
    idx: 0 | 1 | 2,
    patch: Partial<LandUseConfig["estratos"][number]>
  ) =>
    onChange((c) => {
      const next = [...c.estratos] as LandUseConfig["estratos"];
      next[idx] = { ...next[idx], ...patch };
      return { ...c, estratos: next };
    });

  const setH = (idx: 0 | 1 | 2, v: number) =>
    onChange((c) => {
      const H = [...c.H_por_estrato] as [number, number, number];
      H[idx] = v;
      return { ...c, H_por_estrato: H };
    });

  const labels = [t("strata.alto"), t("strata.medio"), t("strata.bajo")] as const;

  return (
    <Section title={t("land_use.title")} subtitle={t("land_use.subtitle")} defaultOpen>
      <LabeledSlider
        label={t("land_use.param_beta")}
        value={config.beta}
        min={0.1}
        max={5}
        step={0.1}
        onChange={(v) => onChange((c) => ({ ...c, beta: v }))}
      />

      <div className="space-y-2 border-t border-slate-200 pt-2 dark:border-slate-800">
        <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">
          {t("land_use.solver")}
        </div>
        <div className="flex gap-2">
          {(["logit", "frechet"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => onChange((c) => ({ ...c, solver: s }))}
              className={
                config.solver === s
                  ? "flex-1 rounded bg-slate-900 px-2 py-1 text-xs font-medium text-white dark:bg-slate-100 dark:text-slate-900"
                  : "flex-1 rounded border border-slate-200 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
              }
            >
              {s === "logit" ? t("land_use.solver_logit") : t("land_use.solver_frechet")}
            </button>
          ))}
        </div>
        {config.solver === "frechet" && (
          <p className="text-[10px] text-amber-600 dark:text-amber-400">
            {t("land_use.solver_frechet_warn")}
          </p>
        )}
      </div>

      {[0, 1, 2].map((i) => {
        const idx = i as 0 | 1 | 2;
        const s = config.estratos[idx];
        return (
          <details
            key={i}
            className="rounded border border-slate-200 p-2 dark:border-slate-800"
            open={i === 0}
          >
            <summary className="cursor-pointer text-xs font-semibold">
              {labels[i]}
            </summary>
            <div className="mt-2 space-y-2">
              <LabeledSlider
                label={t("land_use.param_H", { stratum: labels[i] })}
                value={config.H_por_estrato[idx]}
                min={100}
                max={20000}
                step={100}
                onChange={(v) => setH(idx, v)}
              />
              <LabeledSlider
                label={t("land_use.param_y")}
                value={s.y}
                min={1}
                max={300}
                step={1}
                onChange={(v) => setStratum(idx, { y: v })}
              />
              <LabeledSlider
                label={t("land_use.param_alpha")}
                value={s.alpha}
                min={0.1}
                max={5}
                step={0.05}
                onChange={(v) => setStratum(idx, { alpha: v })}
              />
              <LabeledSlider
                label={t("land_use.param_rho")}
                value={s.rho}
                min={0}
                max={3}
                step={0.05}
                onChange={(v) => setStratum(idx, { rho: v })}
              />
              <LabeledSlider
                label={t("land_use.param_lambda")}
                value={s.lambda}
                min={0.1}
                max={3}
                step={0.05}
                onChange={(v) => setStratum(idx, { lambda: v })}
              />
            </div>
          </details>
        );
      })}
    </Section>
  );
}
