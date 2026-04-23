import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { SidebarSection } from "@/components/ui/SidebarSection";
import type { SimulationConfig } from "@/lib/types";

interface EconomyBuilderProps {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
}

/**
 * Controles de las 3 variables económicas que el estudiante ajusta con
 * mayor frecuencia en actividades de política:
 *   - Tarifa Metro ($)
 *   - Estacionamiento ($)
 *   - Bencina ($/km)
 *
 * Paridad con la versión Streamlit original (app.py → tab_conf2).
 */
export function EconomyBuilder({ config, onChange }: EconomyBuilderProps) {
  const { t } = useTranslation("simulator");

  const setGlobal = (patch: Partial<SimulationConfig["demand"]["globales"]>) =>
    onChange((c) => ({
      ...c,
      demand: {
        ...c.demand,
        globales: { ...c.demand.globales, ...patch },
      },
    }));

  const { costo_tarifa_metro, costo_parking, costo_combustible_km } = config.demand.globales;

  const fmtCurrency = (v: number) => `$${v.toLocaleString("es-CL")}`;
  const fmtCurrencyPerKm = (v: number) => `$${v.toLocaleString("es-CL")}/km`;

  return (
    <SidebarSection
      title={t("sections_sidebar.economy")}
      meta={`$${costo_tarifa_metro} · $${costo_parking}`}
    >
      <LabeledSlider
        label={t("economy_params.tarifa_metro")}
        value={costo_tarifa_metro}
        min={0}
        max={2000}
        step={50}
        format={fmtCurrency}
        onChange={(v) => setGlobal({ costo_tarifa_metro: v })}
      />
      <LabeledSlider
        label={t("economy_params.parking")}
        value={costo_parking}
        min={0}
        max={15000}
        step={500}
        format={fmtCurrency}
        onChange={(v) => setGlobal({ costo_parking: v })}
      />
      <LabeledSlider
        label={t("economy_params.bencina")}
        value={costo_combustible_km}
        min={50}
        max={300}
        step={10}
        format={fmtCurrencyPerKm}
        onChange={(v) => setGlobal({ costo_combustible_km: v })}
      />
    </SidebarSection>
  );
}
