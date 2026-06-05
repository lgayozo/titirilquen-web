import { cn } from "@/lib/cn";

interface LabeledSliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  format?: (v: number) => string;
  onChange: (v: number) => void;
  disabled?: boolean;
  /** Nota aclaratoria opcional bajo el slider (p. ej. cuándo la palanca muerde). */
  hint?: string;
  className?: string;
}

export function LabeledSlider({
  label,
  value,
  min,
  max,
  step = 1,
  unit,
  format,
  onChange,
  disabled,
  hint,
  className,
}: LabeledSliderProps) {
  const display = format
    ? format(value)
    : unit
      ? `${value} ${unit}`
      : String(value);

  return (
    <label className={cn("slider-row block", className)}>
      <div className="srow-top">
        <span className="srow-label">{label}</span>
        <span className="srow-val" aria-hidden="true">
          {display}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        aria-valuetext={display}
        aria-label={`${label}: ${display}`}
      />
      {hint && (
        <p className="mt-1 text-[11px] leading-snug text-muted">{hint}</p>
      )}
    </label>
  );
}
