import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import type { SimulationConfig } from "@/lib/types";

interface EconomyBuilderProps {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
}

/**
 * Las palancas de política que actúan sobre la DEMANDA — cuánto y cómo se
 * viaja— por oposición a `SupplyBuilder`, que mueve la oferta física:
 *   - Tarifa Metro ($)
 *   - Estacionamiento ($)
 *   - Bencina ($/km)
 *   - Factor de teletrabajo (×)
 *
 * El teletrabajo llegó acá el 2026-08-17. Vivía en `CityBuilder`, o sea en la
 * página de Uso de Suelo, porque su campo está en `city.teletrabajo_factor`; y
 * el alumno tenía que cambiar de página para usar la única palanca que saca
 * viajes de la punta, mientras las otras tres estaban en esta sección. La
 * interfaz llegaba a admitirlo: el panel de calibración decía «la política de
 * teletrabajo es el factor multiplicador que está en Uso de Suelo».
 *
 * El campo del schema NO se movió —sigue en `city`—, para no romper los
 * escenarios `.ttrq.json` ya guardados. Lo que cambió es dónde se edita.
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

  const setCity = (patch: Partial<SimulationConfig["city"]>) =>
    onChange((c) => ({ ...c, city: { ...c.city, ...patch } }));

  const { costo_tarifa_metro, costo_parking, costo_combustible_km } =
    config.demand.globales;

  const fmtCurrency = (v: number) => `$${v.toLocaleString("es-CL")}`;
  const fmtCurrencyPerKm = (v: number) => `$${v.toLocaleString("es-CL")}/km`;

  return (
    <CollapsibleSection
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
        hint={t("economy_params.bencina_hint")}
        onChange={(v) => setGlobal({ costo_combustible_km: v })}
      />
      {/* Única palanca de esta sección que no es un precio: multiplica la tasa
          de teletrabajo de cada estrato, y esos agentes salen de la demanda. */}
      <LabeledSlider
        label={t("economy_params.teletrabajo_factor")}
        value={config.city.teletrabajo_factor}
        min={0}
        max={2}
        step={0.1}
        format={(v) => `× ${v.toFixed(1)}`}
        hint={t("economy_params.teletrabajo_hint")}
        onChange={(v) => setCity({ teletrabajo_factor: v })}
      />
    </CollapsibleSection>
  );
}
