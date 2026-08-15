import { useTranslation } from "react-i18next";

import { BPRCurve } from "@/components/viz/BPRCurve";
import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import type { SimulationConfig } from "@/lib/types";

interface SupplyBuilderProps {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
  operatingRatios?: {
    car: number | null;
    bike: number | null;
  };
  /** Frecuencia del metro del último equilibrio: la operativa (recortada) y la
   *  teórica (`carga/K`, sin recortar). Ver `estadoFrecuencia`. */
  metroFreq?: { operativa: number; teorica: number };
}

/** Estado del recorte de la frecuencia endógena del metro (AT-08/AT-09).
 *
 * El core calcula `f_op = clip(carga/K, frec_min, frec_max)` y hasta ahora solo
 * exponía `f_op`. Con una sola cifra el usuario no puede distinguir «subí el
 * tope y no pasó nada» de «el tope no estaba mordiendo» — y medido, con los
 * defaults `frec_min` es inerte y `frec_max` satura sobre ~31 tph. Comparar la
 * operativa con la teórica lo resuelve exactamente. */
function estadoFrecuencia(
  freq: { operativa: number; teorica: number } | undefined,
  frecMin: number,
  frecMax: number,
): { caso: "max" | "min" | "libre"; op: string; teo: string } | null {
  if (!freq || freq.operativa <= 0) return null;
  const EPS = 1e-6;
  const cifras = {
    op: freq.operativa.toFixed(1),
    teo: freq.teorica.toFixed(1),
  };
  if (freq.teorica > frecMax + EPS) return { caso: "max", ...cifras };
  if (freq.teorica < frecMin - EPS) return { caso: "min", ...cifras };
  return { caso: "libre", ...cifras };
}

/** Espejo de display de la capacidad Greenshields de supply/car.py
 * (q_max = k_j·v_l/4, con el factor de ancho escalonado). Solo para el hint
 * del sidebar — la matemática vive en el core. */
function capGreenshields(car: SimulationConfig["supply"]["car"]): number {
  const fa =
    car.ancho_pista_m >= 3.5 ? 1.0 : car.ancho_pista_m >= 3 ? 0.9 : 0.75;
  const kJam = 1000 / (car.largo_vehiculo_m + car.gap_m);
  return Math.round((kJam * car.v_max_kmh * fa) / 4);
}

export function SupplyBuilder({
  config,
  onChange,
  operatingRatios,
  metroFreq,
}: SupplyBuilderProps) {
  const { t } = useTranslation("simulator");

  const setSupply = <K extends keyof SimulationConfig["supply"]>(
    key: K,
    patch: Partial<SimulationConfig["supply"][K]>,
  ) =>
    onChange((c) => ({
      ...c,
      supply: { ...c.supply, [key]: { ...c.supply[key], ...patch } },
    }));

  const { bike, car, train } = config.supply;

  return (
    <>
      <CollapsibleSection
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
          hint={t("supply_params.car.num_pistas_hint")}
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
        {/* S-04: capacidad por pista desacoplada de la velocidad. Apagado ⇒
            Greenshields (C ∝ v_libre, la velocidad nunca empeora congestión). */}
        <label className="mt-1 flex items-center gap-2 text-[11px] text-[var(--ink-2)]">
          <input
            type="checkbox"
            checked={car.capacidad_pista != null}
            onChange={(e) =>
              setSupply("car", {
                // Al activar, partir del valor Greenshields actual redondeado.
                capacidad_pista: e.target.checked ? capGreenshields(car) : null,
              })
            }
          />
          {t("supply_params.car.cap_manual")}
        </label>
        {car.capacidad_pista != null ? (
          <LabeledSlider
            label={t("supply_params.car.capacidad_pista")}
            value={car.capacidad_pista}
            min={300}
            max={4000}
            step={50}
            unit="veh/h"
            hint={t("supply_params.car.cap_manual_hint")}
            onChange={(v) => setSupply("car", { capacidad_pista: v })}
          />
        ) : (
          <p className="mb-2 text-[10px] leading-snug text-muted">
            {t("supply_params.car.cap_greenshields", {
              cap: capGreenshields(car).toLocaleString("es-CL"),
            })}
          </p>
        )}
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
        <BPRCurve
          alpha={car.alpha_bpr}
          beta={car.beta_bpr}
          operatingRatio={operatingRatios?.car ?? null}
          label={t("supply_builder.bpr_curve_auto")}
        />
      </CollapsibleSection>

      <CollapsibleSection
        title={`${t("sections.supply")} · ${t("modes.bici")}`}
        meta={`${bike.capacidad_pista} ${t("supply_params.bike.unit")}`}
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
          unit={t("supply_params.bike.unit")}
          onChange={(v) => setSupply("bike", { capacidad_pista: v })}
        />
        <BPRCurve
          alpha={bike.alpha_bpr}
          beta={bike.beta_bpr}
          operatingRatio={operatingRatios?.bike ?? null}
          label={t("supply_builder.bpr_curve_bike")}
        />
      </CollapsibleSection>

      <CollapsibleSection
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
          min={100}
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
          hint={t("supply_params.train.num_estaciones_hint")}
          onChange={(v) => setSupply("train", { num_estaciones: v })}
        />
        <LabeledSlider
          label={t("supply_params.train.costo_operacion")}
          value={train.costo_operacion_tren_km}
          min={0}
          max={40000}
          step={1000}
          format={(v) => `$${v.toLocaleString("es-CL")}`}
          hint={t("supply_params.train.costo_operacion_hint")}
          onChange={(v) => setSupply("train", { costo_operacion_tren_km: v })}
        />
        <LabeledSlider
          label={t("supply_params.train.factor_dia_punta")}
          value={train.factor_dia_punta}
          min={1}
          max={6}
          step={0.1}
          format={(v) => `× ${v.toFixed(1)}`}
          hint={t("supply_params.train.factor_dia_punta_hint")}
          onChange={(v) => setSupply("train", { factor_dia_punta: v })}
        />
        <LabeledSlider
          label={t("supply_params.train.tiempo_detencion")}
          value={train.tiempo_detencion_min}
          min={0}
          max={2}
          step={0.1}
          format={(v) => `${(v * 60).toFixed(0)} s`}
          onChange={(v) => setSupply("train", { tiempo_detencion_min: v })}
        />
        <div className="grid grid-cols-2 gap-3">
          <LabeledSlider
            label={t("supply_params.train.frec_min")}
            value={train.frec_min}
            min={2}
            max={20}
            step={1}
            unit="tph"
            onChange={(v) =>
              setSupply("train", { frec_min: Math.min(v, train.frec_max) })
            }
          />
          <LabeledSlider
            label={t("supply_params.train.frec_max")}
            value={train.frec_max}
            min={4}
            max={60}
            step={1}
            unit="tph"
            onChange={(v) =>
              setSupply("train", { frec_max: Math.max(v, train.frec_min) })
            }
          />
        </div>
        {(() => {
          const f = estadoFrecuencia(metroFreq, train.frec_min, train.frec_max);
          if (!f) return null;
          return (
            <p
              className="text-[10px]"
              style={{
                color: f.caso === "libre" ? "var(--muted)" : "var(--accent)",
              }}
            >
              {t(`supply_params.train.freq_clip_${f.caso}`, {
                op: f.op,
                teo: f.teo,
              })}
            </p>
          );
        })()}
        <div className="grid grid-cols-2 gap-3">
          <LabeledSlider
            label="α andén"
            value={train.anden_alpha}
            min={0}
            max={3}
            step={0.05}
            onChange={(v) => setSupply("train", { anden_alpha: v })}
          />
          <LabeledSlider
            label="β andén"
            value={train.anden_beta}
            min={1}
            max={8}
            step={0.5}
            onChange={(v) => setSupply("train", { anden_beta: v })}
          />
        </div>
        <p className="text-[10px] text-muted">
          {t("supply_params.train.anden_hint")}
        </p>
      </CollapsibleSection>
    </>
  );
}
