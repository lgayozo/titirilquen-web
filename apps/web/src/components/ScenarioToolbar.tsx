import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Download, Link2, Upload } from "lucide-react";

import { cn } from "@/lib/cn";
import {
  configToUrlParam,
  downloadFile,
  parseTtrqJson,
  readFileAsText,
  serializeToJson,
  TTRQ_EXT,
} from "@/lib/serialization";
import { useSimulationStore } from "@/store/simulationStore";

export function ScenarioToolbar() {
  const { t } = useTranslation("common");
  const config = useSimulationStore((s) => s.config);
  const replaceConfig = useSimulationStore((s) => s.replaceConfig);
  const inputRef = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onExport = () => {
    const name = `scenario_${new Date().toISOString().slice(0, 10)}${TTRQ_EXT}`;
    downloadFile(name, serializeToJson(config, name));
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
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const onShare = async () => {
    const url = new URL(window.location.href);
    url.searchParams.set("s", configToUrlParam(config));
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
    <div className="seg" role="toolbar" aria-label="Scenario">
      <ToolbarButton onClick={onImportClick} icon={<Upload className="h-3 w-3" aria-hidden />} label={t("actions.import")} />
      <ToolbarButton onClick={onExport} icon={<Download className="h-3 w-3" aria-hidden />} label={t("actions.export")} />
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
        <span className="ml-1 text-[10px]" style={{ color: "var(--metro)" }} title={error}>
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
