import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { SidebarSection } from "@/components/ui/SidebarSection";
import type { LandUseConfig } from "@/lib/types-v2";

interface LandUseBuilderProps {
  config: LandUseConfig;
  onChange: (updater: (prev: LandUseConfig) => LandUseConfig) => void;
}

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
    <>
      <SidebarSection title={t("land_use.title")} meta={`β=${config.beta.toFixed(1)}`}>
        <LabeledSlider
          label={t("land_use.param_beta")}
          value={config.beta}
          min={0.1}
          max={5}
          step={0.1}
          onChange={(v) => onChange((c) => ({ ...c, beta: v }))}
        />

        <div className="mb-3">
          <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
            {t("land_use.solver")}
          </div>
          <div className="seg" style={{ width: "100%" }}>
            {(["logit", "frechet"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onChange((c) => ({ ...c, solver: s }))}
                className={config.solver === s ? "active" : ""}
                style={{ flex: 1 }}
              >
                {s === "logit" ? t("land_use.solver_logit") : t("land_use.solver_frechet")}
              </button>
            ))}
          </div>
          {config.solver === "frechet" && (
            <p className="mt-1 text-[10px]" style={{ color: "var(--accent)" }}>
              {t("land_use.solver_frechet_warn")}
            </p>
          )}
        </div>
      </SidebarSection>

      {[0, 1, 2].map((i) => {
        const idx = i as 0 | 1 | 2;
        const s = config.estratos[idx];
        return (
          <SidebarSection
            key={i}
            title={labels[i]!}
            meta={`H=${config.H_por_estrato[idx].toLocaleString()}`}
          >
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
          </SidebarSection>
        );
      })}
    </>
  );
}
