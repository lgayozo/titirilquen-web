import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Download, Link2, Upload, Check } from "lucide-react";

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
      // fallback: push to URL
      window.history.replaceState(null, "", link);
    }
  };

  return (
    <div className="flex items-center gap-1 text-xs">
      <ToolbarButton onClick={onImportClick} icon={<Upload className="h-3.5 w-3.5" />}>
        {t("actions.import")}
      </ToolbarButton>
      <ToolbarButton onClick={onExport} icon={<Download className="h-3.5 w-3.5" />}>
        {t("actions.export")}
      </ToolbarButton>
      <ToolbarButton
        onClick={onShare}
        icon={copied ? <Check className="h-3.5 w-3.5" /> : <Link2 className="h-3.5 w-3.5" />}
      >
        {copied ? "✓" : t("actions.share")}
      </ToolbarButton>

      <input
        ref={inputRef}
        type="file"
        accept=".json,application/json"
        onChange={onFile}
        className="hidden"
      />

      {error && (
        <span className="ml-2 text-red-600 dark:text-red-400" title={error}>
          ⚠
        </span>
      )}
    </div>
  );
}

function ToolbarButton({
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
      className="flex items-center gap-1 rounded px-2 py-1 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
