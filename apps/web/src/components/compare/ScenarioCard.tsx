import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { Play, Upload, X } from "lucide-react";

import { cn } from "@/lib/cn";
import { applyJointPreset } from "@/lib/joint-presets";
import { CITY_PRESETS, POLICY_PRESETS } from "@/lib/presets";
import {
  parseTtrqJson,
  readFileAsText,
  serializeToJson,
  downloadFile,
  TTRQ_EXT,
} from "@/lib/serialization";
import type { Scenario } from "@/store/compareStore";
import { useCompareStore } from "@/store/compareStore";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

interface ScenarioCardProps {
  scenario: Scenario;
  onRun: () => void;
  removable?: boolean;
  /** ¿Es el escenario contra el que se calculan los deltas? */
  isBase?: boolean;
  onMakeBase?: () => void;
}

export function ScenarioCard({
  scenario,
  onRun,
  removable,
  isBase,
  onMakeBase,
}: ScenarioCardProps) {
  const { t } = useTranslation("common");
  const { t: tS } = useTranslation("simulator");
  const inputRef = useRef<HTMLInputElement>(null);
  const setScenario = useCompareStore((s) => s.setScenario);
  const rename = useCompareStore((s) => s.renameScenario);
  const remove = useCompareStore((s) => s.removeScenario);
  const currentConfig = useSimulationStore((s) => s.config);
  // La selección vive en el escenario (persiste); «Personalizado» = sin preset.
  const city = scenario.presetCity ?? "Personalizado";
  const policy = scenario.presetPolicy ?? "Personalizado";
  // Último nombre que pusimos automáticamente. Sirve para distinguir «el
  // usuario no lo tocó» de «lo renombró a mano»: solo en el primer caso se
  // regenera al cambiar de preset. Sin esto, cambiar la ciudad de una tarjeta
  // dejaba el nombre viejo mintiendo («Base · Pro-Bici» con ciudad Compacta).
  const autoName = useRef<string | null>(null);

  // Captura el escenario COMPLETO: transporte + suelo + población del acoplado.
  // Qué se corre con él lo decide el tipo de comparación de la página.
  const onUseCurrent = () => {
    const lu = useLandUseStore.getState();
    // C-02: snapshot de la regla de localización del Sandbox (isPost) — si el
    // bid-rent corrió con geometría concordante, la lente Transporte usará la
    // localización de equilibrio, igual que una corrida en el Sandbox.
    const isPost =
      lu.result != null &&
      lu.result.L === currentConfig.city.n_celdas &&
      (lu.result.result?.Q?.length ?? 0) > 0;
    setScenario(scenario.id, {
      config: currentConfig,
      landUse: lu.config,
      localizacion: isPost ? "equilibrio" : "original",
      poblacion: lu.coupledPoblacion,
    });
  };

  // Carga un preset directo en la tarjeta. Antes la única forma de poblarla era
  // «usar la config actual» del Sandbox, así que armar una comparación de dos
  // políticas exigía un viaje de ida y vuelta a otra página POR ESCENARIO — y
  // como las dos tarjetas leen el mismo store, sin ese viaje quedaban idénticas.
  const onPreset = (city: string, policy: string) => {
    const { sim, landUse } = applyJointPreset({
      key: `${city}/${policy}`,
      titleKey: "",
      descriptionKey: "",
      city,
      policy,
      poblacionDefault: scenario.poblacion,
    });
    const nuevo = nombrePreset(city, policy);
    const renombradoAMano =
      scenario.name !== "" && scenario.name !== autoName.current;
    if (!renombradoAMano) autoName.current = nuevo;
    setScenario(scenario.id, {
      config: sim,
      landUse,
      // El preset define la ciudad entera, así que la localización se decide al
      // correr (misma regla que al importar un archivo).
      localizacion: null,
      presetCity: city,
      presetPolicy: policy,
      ...(renombradoAMano ? {} : { name: nuevo }),
    });
  };

  const onImport = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file) return;
    try {
      const raw = await readFileAsText(file);
      const ttrq = parseTtrqJson(raw);
      setScenario(scenario.id, {
        config: ttrq.config,
        landUse: ttrq.land_use ?? null,
        // El .ttrq no registra la localización: se decide al correr (según si
        // la tarjeta tiene resultado de suelo) — ver runOne en ComparePage.
        localizacion: null,
        poblacion: ttrq.coupled?.poblacion,
        name: ttrq.name ?? file.name.replace(/\.ttrq\.json$/, ""),
      });
    } catch (e) {
      useCompareStore
        .getState()
        .setError(scenario.id, e instanceof Error ? e.message : String(e));
    }
  };

  const onExport = () => {
    if (!scenario.config) return;
    const name = scenario.name || `escenario-${scenario.id}`;
    downloadFile(
      `${name}${TTRQ_EXT}`,
      serializeToJson(scenario.config, name, {
        land_use: scenario.landUse ?? undefined,
        coupled: { poblacion: scenario.poblacion, outer_max_iter: 12 },
      }),
    );
  };

  return (
    <div
      className="relative overflow-hidden rounded-lg border border-[var(--rule)] bg-[var(--paper)] p-3"
      aria-busy={scenario.status === "running"}
    >
      {/* Indicador sutil de procesamiento: barra indeterminada en el borde
          superior (el acoplado puede tardar ~10-20 s y sin esto la página
          parece congelada). */}
      {scenario.status === "running" && (
        <div className="card-progress" aria-hidden />
      )}
      <div className="mb-2 flex items-center gap-2">
        <input
          type="text"
          value={scenario.name}
          placeholder={tS("compare.scenario_card.untitled", {
            id: scenario.id,
          })}
          onChange={(e) => rename(scenario.id, e.target.value)}
          className="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 text-sm font-semibold focus:border-[var(--rule)] focus:outline-none"
        />
        {/* Base explícita (antes era «la primera con resultado», implícita y no
            elegible): los deltas de toda la página se calculan contra ella. */}
        {onMakeBase && (
          <button
            type="button"
            onClick={onMakeBase}
            aria-pressed={isBase}
            title={tS("compare.scenario_card.make_base")}
            className={cn(
              "rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
              isBase
                ? "border-[var(--accent)] text-[var(--accent)]"
                : "border-[var(--rule)] text-[var(--muted)] hover:bg-[var(--paper-2)]",
            )}
          >
            {isBase
              ? `● ${tS("compare.scenario_card.base")}`
              : `○ ${tS("compare.scenario_card.base")}`}
          </button>
        )}
        <StatusBadge status={scenario.status} />
        {removable && (
          <button
            type="button"
            onClick={() => remove(scenario.id)}
            className="rounded p-1 text-[var(--muted)] hover:bg-[var(--paper-2)] hover:text-[var(--metro)]"
            aria-label={t("actions.remove")}
          >
            <X className="h-3.5 w-3.5" aria-hidden />
          </button>
        )}
      </div>

      {scenario.config ? (
        <div className="mb-2 grid grid-cols-2 gap-1 text-[11px] text-[var(--muted)]">
          <span>
            {tS("compare.scenario_card.cells", {
              n: scenario.config.city.n_celdas,
            })}
          </span>
          <span>
            {tS("compare.scenario_card.length_km", {
              km: scenario.config.city.largo_ciudad_km,
            })}
          </span>
          <span>
            {tS("compare.scenario_card.density", {
              rho: scenario.config.city.densidad_hab_km,
            })}
          </span>
          <span>
            {tS("compare.scenario_card.max_iter", {
              n: scenario.config.max_iter,
            })}
          </span>
          <span className="col-span-2">
            {tS("compare.scenario_card.parking_fare", {
              parking:
                scenario.config.demand.globales.costo_parking.toLocaleString(
                  "es-CL",
                ),
              fare: scenario.config.demand.globales.costo_tarifa_metro,
            })}
          </span>
          {scenario.landUse && (
            <span className="col-span-2">
              {tS("compare.scenario_card.land_line", {
                forma: tS(`land_use.forma_${scenario.landUse.forma}`),
                pob: `${Math.round(scenario.poblacion / 1000)}k`,
              })}
            </span>
          )}
        </div>
      ) : (
        <div className="mb-2 rounded bg-[var(--paper-2)] p-2 text-[11px] text-[var(--muted)]">
          {tS("compare.scenario_card.no_config")}
        </div>
      )}

      {/* Preset directo: ciudad × política. Es el camino rápido — sin esto hay
          que ir al Sandbox, aplicar, y volver, por cada escenario. */}
      <div className="mb-2 flex flex-wrap items-center gap-1">
        <Combo
          label={tS("compare.scenario_card.city_preset")}
          value={city}
          options={Object.keys(CITY_PRESETS)}
          onChange={(v) => onPreset(v, policy)}
        />
        <Combo
          label={tS("compare.scenario_card.policy_preset")}
          value={policy}
          options={Object.keys(POLICY_PRESETS)}
          onChange={(v) => onPreset(city, v)}
        />
      </div>

      <div className="flex flex-wrap items-center gap-1">
        <SmallButton onClick={onUseCurrent}>
          {t("actions.use_sandbox")}
        </SmallButton>
        <SmallButton
          onClick={() => inputRef.current?.click()}
          icon={<Upload className="h-3 w-3" />}
        >
          {t("actions.import")}
        </SmallButton>
        {scenario.config && (
          <SmallButton onClick={onExport}>{t("actions.export")}</SmallButton>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".json,application/json"
          onChange={onImport}
          className="hidden"
        />
        <div className="ml-auto">
          <button
            type="button"
            onClick={onRun}
            disabled={!scenario.config || scenario.status === "running"}
            className={cn(
              "flex items-center gap-1 rounded px-2 py-1 text-xs font-medium",
              scenario.config && scenario.status !== "running"
                ? "bg-[var(--ink)] text-[var(--paper)] hover:opacity-85"
                : "bg-[var(--paper-2)] text-[var(--muted)]",
            )}
          >
            <Play className="h-3 w-3" />
            {scenario.status === "running" ? "…" : t("actions.run")}
          </button>
        </div>
      </div>

      {scenario.error && (
        <div className="mt-2 rounded border-l-2 border-[var(--metro)] bg-[var(--paper-2)] p-2 text-[11px] text-[var(--metro)]">
          {scenario.error}
        </div>
      )}
    </div>
  );
}

/** Nombre por defecto de una tarjeta poblada con preset: «Compacta · Pro-Bici».
 *  Se omite «Personalizado», que significa «sin preset en esa dimensión». */
function nombrePreset(city: string, policy: string): string {
  const partes = [city, policy].filter((p) => p && p !== "Personalizado");
  return partes.join(" · ");
}

function Combo({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded border border-[var(--rule)] bg-[var(--paper)] px-1 py-0.5 text-[11px] text-[var(--ink-2)]"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

function SmallButton({
  onClick,
  icon,
  children,
}: {
  onClick: () => void;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1 rounded border border-[var(--rule)] px-2 py-1 text-[11px] text-[var(--ink-2)] hover:bg-[var(--paper-2)]"
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}

function StatusBadge({ status }: { status: Scenario["status"] }) {
  const { t } = useTranslation("simulator");
  const label: Record<Scenario["status"], string> = {
    empty: t("compare.scenario_card.status.empty"),
    configured: t("compare.scenario_card.status.configured"),
    running: t("compare.scenario_card.status.running"),
    done: t("compare.scenario_card.status.done"),
    error: t("compare.scenario_card.status.error"),
  };
  const classes: Record<Scenario["status"], string> = {
    empty: "bg-[var(--paper-2)] text-[var(--muted)]",
    configured: "bg-[var(--paper-2)] text-[var(--walk)]",
    running: "bg-[var(--paper-2)] text-[var(--auto)]",
    done: "bg-[var(--paper-2)] text-[var(--bici)]",
    error: "bg-[var(--paper-2)] text-[var(--metro)]",
  };
  return (
    <span
      className={cn(
        "rounded px-2 py-0.5 text-[10px] font-medium",
        classes[status],
      )}
    >
      {label[status]}
    </span>
  );
}
