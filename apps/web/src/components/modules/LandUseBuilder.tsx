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
    patch: Partial<LandUseConfig["estratos"][number]>,
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

  const labels = [
    t("strata.alto"),
    t("strata.medio"),
    t("strata.bajo"),
  ] as const;

  return (
    <>
      <SidebarSection
        title={t("land_use.title")}
        meta={`β=${config.beta.toFixed(1)}`}
      >
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
          <div className="flex flex-wrap gap-1.5">
            {(["heteroscedastic", "logit"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onChange((c) => ({ ...c, solver: s }))}
                className={`chip-toggle${config.solver === s ? " active" : ""}`}
              >
                {t(`land_use.solver_${s}`)}
              </button>
            ))}
          </div>
          <p className="mt-1 text-[10px] text-muted">
            {t(`land_use.solver_hint_${config.solver}`)}
          </p>
        </div>

        <div className="mb-3">
          <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
            {t("land_use.forma")}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(
              [
                "normal",
                "uniforme",
                "exponencial",
                "meseta",
                "bimodal",
                "valle",
              ] as const
            ).map((f) => (
              <button
                key={f}
                type="button"
                className={`chip-toggle${config.forma === f ? " active" : ""}`}
                onClick={() => onChange((c) => ({ ...c, forma: f }))}
              >
                {t(`land_use.forma_${f}`)}
              </button>
            ))}
          </div>
          <p className="mt-1 text-[10px] text-muted">
            {t(`land_use.forma_hint_${config.forma}`)}
          </p>
        </div>

        <LabeledSlider
          label={t("land_use.param_oferta_sigma")}
          value={config.oferta_sigma_frac}
          min={0.1}
          max={1.5}
          step={0.05}
          disabled={config.forma === "uniforme"}
          onChange={(v) => onChange((c) => ({ ...c, oferta_sigma_frac: v }))}
        />
        <p className="-mt-1 text-[10px] text-muted">
          {config.forma === "uniforme"
            ? t("land_use.oferta_sigma_na")
            : t("land_use.oferta_sigma_hint")}
        </p>

        {config.forma === "bimodal" && (
          <LabeledSlider
            label={t("land_use.param_separacion")}
            value={config.forma_param}
            min={0.1}
            max={1}
            step={0.05}
            onChange={(v) => onChange((c) => ({ ...c, forma_param: v }))}
          />
        )}
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
