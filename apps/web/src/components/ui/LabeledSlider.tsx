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
  className,
}: LabeledSliderProps) {
  const display = format ? format(value) : unit ? `${value} ${unit}` : String(value);

  return (
    <label className={cn("block text-xs", className)}>
      <div className="flex items-baseline justify-between">
        <span className="text-slate-600 dark:text-slate-300">{label}</span>
        <span
          className="font-mono text-sm font-medium tabular-nums text-slate-900 dark:text-slate-100"
          aria-hidden="true"
        >
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
        className="mt-1 w-full accent-slate-900 dark:accent-slate-200"
      />
    </label>
  );
}
