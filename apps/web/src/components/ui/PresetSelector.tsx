import { useTranslation } from "react-i18next";

interface PresetSelectorProps {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
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
    <div className="preset-row">
      <label>{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o} value={o}>
            {displayOf(o)}
          </option>
        ))}
      </select>
    </div>
  );
}
