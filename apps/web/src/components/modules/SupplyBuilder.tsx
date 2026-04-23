import { useTranslation } from "react-i18next";

import { BPRCurve } from "@/components/viz/BPRCurve";
import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { SidebarSection } from "@/components/ui/SidebarSection";
import type { SimulationConfig } from "@/lib/types";

interface SupplyBuilderProps {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
  operatingRatios?: {
    car: number | null;
    bike: number | null;
  };
}

export function SupplyBuilder({ config, onChange, operatingRatios }: SupplyBuilderProps) {
  const { t } = useTranslation("simulator");

  const setSupply = <K extends keyof SimulationConfig["supply"]>(
    key: K,
    patch: Partial<SimulationConfig["supply"][K]>
  ) =>
    onChange((c) => ({
      ...c,
      supply: { ...c.supply, [key]: { ...c.supply[key], ...patch } },
    }));

  const { bike, car, train } = config.supply;

  return (
    <>
      <SidebarSection
        title={`${t("sections.supply")} · ${t("modes.auto")}`}
        meta={`${car.num_pistas} × ${car.v_max_kmh} km/h`}
        defaultOpen={false}
      >
        <LabeledSlider
          label={t("supply_params.car.v_max_kmh")}
          value={car.v_max_kmh}
          min={20}
          max={80}
          step={1}
          unit="km/h"
          onChange={(v) => setSupply("car", { v_max_kmh: v })}
        />
        <LabeledSlider
          label={t("supply_params.car.num_pistas")}
          value={car.num_pistas}
          min={1}
          max={5}
          step={1}
          onChange={(v) => setSupply("car", { num_pistas: v })}
        />
        <LabeledSlider
          label={t("supply_params.car.ancho_pista_m")}
          value={car.ancho_pista_m}
          min={2.5}
          max={4}
          step={0.1}
          unit="m"
          onChange={(v) => setSupply("car", { ancho_pista_m: v })}
        />
        <div className="grid grid-cols-2 gap-3">
          <LabeledSlider
            label="α BPR"
            value={car.alpha_bpr}
            min={0.1}
            max={2}
            step={0.05}
            onChange={(v) => setSupply("car", { alpha_bpr: v })}
          />
          <LabeledSlider
            label="β BPR"
            value={car.beta_bpr}
            min={1}
            max={6}
            step={0.1}
            onChange={(v) => setSupply("car", { beta_bpr: v })}
          />
        </div>
        <BPRCurve alpha={car.alpha_bpr} beta={car.beta_bpr} operatingRatio={operatingRatios?.car ?? null} />
      </SidebarSection>

      <SidebarSection
        title={`${t("sections.supply")} · ${t("modes.bici")}`}
        meta={`${bike.capacidad_pista} bici/h`}
        defaultOpen={false}
      >
        <LabeledSlider
          label={t("supply_params.bike.v_media_kmh")}
          value={bike.v_media_kmh}
          min={6}
          max={30}
          step={0.5}
          unit="km/h"
          onChange={(v) => setSupply("bike", { v_media_kmh: v })}
        />
        <LabeledSlider
          label={t("supply_params.bike.capacidad_pista")}
          value={bike.capacidad_pista}
          min={200}
          max={6000}
          step={100}
          unit="bici/h"
          onChange={(v) => setSupply("bike", { capacidad_pista: v })}
        />
        <BPRCurve alpha={bike.alpha_bpr} beta={bike.beta_bpr} operatingRatio={operatingRatios?.bike ?? null} />
      </SidebarSection>

      <SidebarSection
        title={`${t("sections.supply")} · ${t("modes.metro")}`}
        meta={`${train.num_estaciones} st`}
        defaultOpen={false}
      >
        <LabeledSlider
          label={t("supply_params.train.v_tren_kmh")}
          value={train.v_tren_kmh}
          min={15}
          max={80}
          step={1}
          unit="km/h"
          onChange={(v) => setSupply("train", { v_tren_kmh: v })}
        />
        <LabeledSlider
          label={t("supply_params.train.capacidad_tren")}
          value={train.capacidad_tren}
          min={400}
          max={2500}
          step={50}
          unit="pax"
          onChange={(v) => setSupply("train", { capacidad_tren: v })}
        />
        <LabeledSlider
          label={t("supply_params.train.num_estaciones")}
          value={train.num_estaciones}
          min={3}
          max={30}
          step={1}
          onChange={(v) => setSupply("train", { num_estaciones: v })}
        />
        <LabeledSlider
          label={t("supply_params.train.frec_max")}
          value={train.frec_max}
          min={4}
          max={60}
          step={1}
          unit="tph"
          onChange={(v) => setSupply("train", { frec_max: v })}
        />
      </SidebarSection>
    </>
  );
}
