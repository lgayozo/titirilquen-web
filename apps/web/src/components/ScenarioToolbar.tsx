import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Download, Link2, Upload } from "lucide-react";

import { cn } from "@/lib/cn";
import {
  downloadFile,
  parseTtrqJson,
  readFileAsText,
  scenarioToUrlParam,
  serializeToJson,
  TTRQ_EXT,
} from "@/lib/serialization";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

export function ScenarioToolbar() {
  const { t } = useTranslation("common");
  const config = useSimulationStore((s) => s.config);
  const replaceConfig = useSimulationStore((s) => s.replaceConfig);
  const landUse = useLandUseStore((s) => s.config);
  const setLandUseConfig = useLandUseStore((s) => s.setConfig);
  const coupledPoblacion = useLandUseStore((s) => s.coupledPoblacion);
  const coupledOuterMaxIter = useLandUseStore((s) => s.coupledOuterMaxIter);
  const setCoupledPoblacion = useLandUseStore((s) => s.setCoupledPoblacion);
  const setCoupledOuterMaxIter = useLandUseStore(
    (s) => s.setCoupledOuterMaxIter,
  );

  // El escenario completo: transporte + suelo + preferencias del acoplado.
  const scenarioExtras = () => ({
    land_use: landUse,
    coupled: {
      poblacion: coupledPoblacion,
      outer_max_iter: coupledOuterMaxIter,
    },
  });
  const inputRef = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onExport = () => {
    const name = `scenario_${new Date().toISOString().slice(0, 10)}${TTRQ_EXT}`;
    downloadFile(name, serializeToJson(config, name, scenarioExtras()));
  };

  const onImportClick = () => inputRef.current?.click();

  const onFile = async (ev: React.ChangeEvent<HTMLInputElement>) => {
    const file = ev.target.files?.[0];
    ev.target.value = "";
    if (!file) return;
    try {
      const raw = await readFileAsText(file);
      const ttrq = parseTtrqJson(raw);
      replaceConfig(ttrq.config);
      if (ttrq.land_use) setLandUseConfig(() => ttrq.land_use!);
      if (ttrq.coupled) {
        setCoupledPoblacion(ttrq.coupled.poblacion);
        setCoupledOuterMaxIter(ttrq.coupled.outer_max_iter);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const onShare = async () => {
    const url = new URL(window.location.href);
    url.searchParams.set(
      "s",
      scenarioToUrlParam({ config, ...scenarioExtras() }),
    );
    url.hash = "";
    const link = url.toString();
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      window.history.replaceState(null, "", link);
    }
  };

  return (
    <div
      className="seg"
      role="toolbar"
      aria-label={t("actions.scenario_toolbar")}
    >
      <ToolbarButton
        onClick={onImportClick}
        icon={<Upload className="h-3 w-3" aria-hidden />}
        label={t("actions.import")}
      />
      <ToolbarButton
        onClick={onExport}
        icon={<Download className="h-3 w-3" aria-hidden />}
        label={t("actions.export")}
      />
      <ToolbarButton
        onClick={onShare}
        icon={
          copied ? (
            <Check className="h-3 w-3" aria-hidden />
          ) : (
            <Link2 className="h-3 w-3" aria-hidden />
          )
        }
        label={t("actions.share")}
        active={copied}
      />
      <input
        ref={inputRef}
        type="file"
        accept=".json,application/json"
        onChange={onFile}
        className="hidden"
      />
      {error && (
        <span
          className="ml-1 text-[10px]"
          style={{ color: "var(--metro)" }}
          title={error}
        >
          ⚠
        </span>
      )}
    </div>
  );
}

function ToolbarButton({
  onClick,
  icon,
  label,
  active,
}: {
  onClick: () => void;
  icon?: React.ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={cn("flex items-center gap-1", active && "active")}
    >
      {icon}
      <span className="sr-only">{label}</span>
    </button>
  );
}
