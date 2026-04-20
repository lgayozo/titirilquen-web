import { useTranslation } from "react-i18next";

interface PresetSelectorProps {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
  /** Namespace bajo el cual buscar traducciones de los valores del enum. */
  translateValues?: boolean;
}

export function PresetSelector({
  label,
  options,
  value,
  onChange,
  translateValues = true,
}: PresetSelectorProps) {
  const { t } = useTranslation("simulator");
  const displayOf = (opt: string) =>
    translateValues ? t(`presets.names.${opt}`, opt) : opt;

  return (
    <label className="block text-xs">
      <span className="text-slate-600 dark:text-slate-300">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {displayOf(o)}
          </option>
        ))}
      </select>
    </label>
  );
}
