import { useTranslation } from "react-i18next";

import { BPRCurve } from "@/components/viz/BPRCurve";
import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { Section } from "@/components/ui/Section";
import type { SimulationConfig } from "@/lib/types";

interface SupplyBuilderProps {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
  operatingRatios?: {
    /** máx flujo/capacidad observado en la última corrida, por modo */
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
      <Section title={`${t("sections.supply")} · ${t("modes.auto")}`} defaultOpen={false}>
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
        <LabeledSlider
          label={t("supply_params.car.largo_vehiculo_m")}
          value={car.largo_vehiculo_m}
          min={3}
          max={7}
          step={0.5}
          unit="m"
          onChange={(v) => setSupply("car", { largo_vehiculo_m: v })}
        />
        <LabeledSlider
          label={t("supply_params.car.gap_m")}
          value={car.gap_m}
          min={1}
          max={5}
          step={0.5}
          unit="m"
          onChange={(v) => setSupply("car", { gap_m: v })}
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
        <div>
          <div className="mb-1 text-[11px] text-slate-500 dark:text-slate-400">
            {t("supply_builder.bpr_curve_auto")}
          </div>
          <BPRCurve
            alpha={car.alpha_bpr}
            beta={car.beta_bpr}
            operatingRatio={operatingRatios?.car ?? null}
          />
        </div>
      </Section>

      <Section title={`${t("sections.supply")} · ${t("modes.bici")}`} defaultOpen={false}>
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
        <div className="grid grid-cols-2 gap-3">
          <LabeledSlider
            label="α BPR"
            value={bike.alpha_bpr}
            min={0.1}
            max={2}
            step={0.05}
            onChange={(v) => setSupply("bike", { alpha_bpr: v })}
          />
          <LabeledSlider
            label="β BPR"
            value={bike.beta_bpr}
            min={1}
            max={6}
            step={0.1}
            onChange={(v) => setSupply("bike", { beta_bpr: v })}
          />
        </div>
        <div>
          <div className="mb-1 text-[11px] text-slate-500 dark:text-slate-400">
            {t("supply_builder.bpr_curve_bike")}
          </div>
          <BPRCurve
            alpha={bike.alpha_bpr}
            beta={bike.beta_bpr}
            operatingRatio={operatingRatios?.bike ?? null}
          />
        </div>
      </Section>

      <Section title={`${t("sections.supply")} · ${t("modes.metro")}`} defaultOpen={false}>
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
          unit="trenes/h"
          onChange={(v) => setSupply("train", { frec_max: v })}
        />
      </Section>
    </>
  );
}
