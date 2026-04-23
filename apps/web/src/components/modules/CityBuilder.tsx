import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { PresetSelector } from "@/components/ui/PresetSelector";
import { SidebarSection } from "@/components/ui/SidebarSection";
import { CITY_PRESETS } from "@/lib/presets";
import type { SimulationConfig } from "@/lib/types";

interface CityBuilderProps {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
}

export function CityBuilder({ config, onChange }: CityBuilderProps) {
  const { t } = useTranslation("simulator");

  const setCity = (patch: Partial<SimulationConfig["city"]>) =>
    onChange((c) => ({ ...c, city: { ...c.city, ...patch } }));

  const applyPreset = (name: string) => {
    const preset = CITY_PRESETS[name];
    if (!preset) return;
    setCity({
      ...(preset.largo_ciudad !== undefined && { largo_ciudad_km: preset.largo_ciudad }),
      ...(preset.densidad !== undefined && { densidad_por_celda: preset.densidad }),
    });
  };

  const matchingPreset =
    Object.entries(CITY_PRESETS).find(
      ([, v]) =>
        v.largo_ciudad === config.city.largo_ciudad_km &&
        v.densidad === config.city.densidad_por_celda
    )?.[0] ?? "Personalizado";

  const [sA, sM, sB] = config.city.share_estratos;

  const setShares = (nextA: number, nextM: number) => {
    const a = clamp01(nextA);
    const m = clamp01(nextM);
    const b = Math.max(0, 1 - a - m);
    setCity({ share_estratos: [round2(a), round2(m), round2(b)] });
  };

  return (
    <>
      <SidebarSection title={t("sections_sidebar.scenarios")}>
        <PresetSelector
          label={t("presets.city_label")}
          options={Object.keys(CITY_PRESETS)}
          value={matchingPreset}
          onChange={applyPreset}
        />
      </SidebarSection>

      <SidebarSection
        title={t("sections.city")}
        meta={`${config.city.largo_ciudad_km} km · ${config.city.n_celdas} celdas`}
      >
        <LabeledSlider
          label={t("city_params.largo_ciudad_km")}
          value={config.city.largo_ciudad_km}
          min={5}
          max={40}
          step={1}
          unit="km"
          onChange={(v) => setCity({ largo_ciudad_km: v })}
        />
        <LabeledSlider
          label={t("city_params.n_celdas")}
          value={config.city.n_celdas}
          min={51}
          max={1001}
          step={50}
          onChange={(v) => setCity({ n_celdas: v % 2 === 0 ? v + 1 : v })}
        />
        <LabeledSlider
          label={t("city_params.densidad_por_celda")}
          value={config.city.densidad_por_celda}
          min={10}
          max={300}
          step={10}
          unit={t("city_params.density_unit")}
          onChange={(v) => setCity({ densidad_por_celda: v })}
        />
        <LabeledSlider
          label={t("city_params.pendiente_porcentaje")}
          value={config.city.pendiente_porcentaje}
          min={-10}
          max={10}
          step={0.5}
          unit="%"
          onChange={(v) => setCity({ pendiente_porcentaje: v })}
        />
        <LabeledSlider
          label={t("city_params.teletrabajo_factor")}
          value={config.city.teletrabajo_factor}
          min={0}
          max={2}
          step={0.1}
          onChange={(v) => setCity({ teletrabajo_factor: v })}
        />
      </SidebarSection>

      <SidebarSection
        title={t("strata.distribution")}
        meta={`${(sA * 100).toFixed(0)}/${(sM * 100).toFixed(0)}/${(sB * 100).toFixed(0)}`}
      >
        <LabeledSlider
          label={t("strata.alto")}
          value={sA}
          min={0}
          max={1}
          step={0.05}
          format={(v) => `${(v * 100).toFixed(0)}%`}
          onChange={(v) => setShares(v, sM)}
        />
        <LabeledSlider
          label={t("strata.medio")}
          value={sM}
          min={0}
          max={1 - sA}
          step={0.05}
          format={(v) => `${(v * 100).toFixed(0)}%`}
          onChange={(v) => setShares(sA, v)}
        />
        <div className="text-[11px] text-muted">
          {t("strata.bajo")}: {(sB * 100).toFixed(0)}% ({t("strata.auto_calculated")})
        </div>
      </SidebarSection>
    </>
  );
}

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}
