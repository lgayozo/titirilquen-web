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
    });
  };

  const matchingPreset =
    Object.entries(CITY_PRESETS).find(
      ([, v]) => v.largo_ciudad === config.city.largo_ciudad_km
    )?.[0] ?? "Personalizado";

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
        meta={t("city_params.meta", {
          km: config.city.largo_ciudad_km,
          n: config.city.n_celdas,
        })}
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
          label={t("city_params.n_parcelas")}
          value={config.city.n_celdas}
          min={51}
          max={1001}
          step={50}
          hint={t("city_params.n_parcelas_hint", {
            dx: Math.round(
              (config.city.largo_ciudad_km / config.city.n_celdas) * 1000,
            ),
          })}
          onChange={(v) => setCity({ n_celdas: v % 2 === 0 ? v + 1 : v })}
        />
        <LabeledSlider
          label={t("city_params.pendiente_porcentaje")}
          value={config.city.pendiente_porcentaje}
          min={-10}
          max={10}
          step={0.5}
          unit="%"
          hint={t("city_params.pendiente_hint")}
          onChange={(v) => setCity({ pendiente_porcentaje: v })}
        />
        <LabeledSlider
          label={t("city_params.teletrabajo_factor")}
          value={config.city.teletrabajo_factor}
          min={0}
          max={2}
          step={0.1}
          hint={t("city_params.teletrabajo_hint")}
          onChange={(v) => setCity({ teletrabajo_factor: v })}
        />
      </SidebarSection>
    </>
  );
}
