import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { Play, Upload, X } from "lucide-react";

import { cn } from "@/lib/cn";
import { parseTtrqJson, readFileAsText, serializeToJson, downloadFile, TTRQ_EXT } from "@/lib/serialization";
import type { Scenario } from "@/store/compareStore";
import { useCompareStore } from "@/store/compareStore";
import { useSimulationStore } from "@/store/simulationStore";

interface ScenarioCardProps {
  scenario: Scenario;
  onRun: () => void;
  removable?: boolean;
}

export function ScenarioCard({ scenario, onRun, removable }: ScenarioCardProps) {
  const { t } = useTranslation("common");
  const { t: tS } = useTranslation("simulator");
  const inputRef = useRef<HTMLInputElement>(null);
  const setConfig = useCompareStore((s) => s.setConfig);
  const rename = useCompareStore((s) => s.renameScenario);
  const remove = useCompareStore((s) => s.removeScenario);
  const currentConfig = useSimulationStore((s) => s.config);

  const onUseCurrent = () => {
    setConfig(scenario.id, currentConfig, `Transporte · ${scenario.id}`);
  };

  const onImport = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file) return;
    try {
      const raw = await readFileAsText(file);
      const ttrq = parseTtrqJson(raw);
      setConfig(scenario.id, ttrq.config, ttrq.name ?? file.name.replace(/\.ttrq\.json$/, ""));
    } catch (e) {
      useCompareStore.getState().setError(
        scenario.id,
        e instanceof Error ? e.message : String(e)
      );
    }
  };

  const onExport = () => {
    if (!scenario.config) return;
    downloadFile(`${scenario.name}${TTRQ_EXT}`, serializeToJson(scenario.config, scenario.name));
  };

  return (
    <div className="rounded-lg border border-[var(--rule)] bg-[var(--paper)] p-3">
      <div className="mb-2 flex items-center gap-2">
        <input
          type="text"
          value={scenario.name}
          onChange={(e) => rename(scenario.id, e.target.value)}
          className="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 text-sm font-semibold focus:border-[var(--rule)] focus:outline-none"
        />
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
          <span>{tS("compare.scenario_card.cells", { n: scenario.config.city.n_celdas })}</span>
          <span>{tS("compare.scenario_card.length_km", { km: scenario.config.city.largo_ciudad_km })}</span>
          <span>{tS("compare.scenario_card.density", { rho: scenario.config.city.densidad_por_celda })}</span>
          <span>{tS("compare.scenario_card.max_iter", { n: scenario.config.max_iter })}</span>
          <span className="col-span-2">
            {tS("compare.scenario_card.parking_fare", {
              parking: scenario.config.demand.globales.costo_parking.toLocaleString(),
              fare: scenario.config.demand.globales.costo_tarifa_metro,
            })}
          </span>
        </div>
      ) : (
        <div className="mb-2 rounded bg-[var(--paper-2)] p-2 text-[11px] text-[var(--muted)]">
          {tS("compare.scenario_card.no_config")}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1">
        <SmallButton onClick={onUseCurrent}>{t("actions.use_sandbox")}</SmallButton>
        <SmallButton onClick={() => inputRef.current?.click()} icon={<Upload className="h-3 w-3" />}>
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
                : "bg-[var(--paper-2)] text-[var(--muted)]"
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
    <span className={cn("rounded px-2 py-0.5 text-[10px] font-medium", classes[status])}>
      {label[status]}
    </span>
  );
}
