import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import {
  accessibilityHansen,
  formatDelta,
  meanUtilityByStratum,
  theilSegregation,
} from "@/lib/metrics";
import type { CoupledResult, LandUseConfig } from "@/lib/types-v2";

interface CoupledMetricsProps {
  result: CoupledResult;
  landUseConfig: LandUseConfig;
  className?: string;
}

type Series = {
  segregation: number;
  welfare: [number | null, number | null, number | null];
  accessibility: [number | null, number | null, number | null];
};

/**
 * Panel compacto con 3 métricas de interdependencia, evolucionando a lo largo
 * de las iteraciones exteriores del loop acoplado. Cada métrica muestra:
 *   - Valor final (grande, tipografía display)
 *   - Delta respecto a la primera iteración
 *   - Sparkline con trayectoria
 */
export function CoupledMetrics({ result, landUseConfig, className }: CoupledMetricsProps) {
  const { t } = useTranslation("simulator");
  const alpha = landUseConfig.estratos.map((s) => s.alpha);

  const series = useMemo<Series[]>(() => {
    return result.iterations.map((it) => ({
      segregation: theilSegregation(it.land_use.Q),
      welfare: meanUtilityByStratum(it.transport.agentes),
      accessibility: accessibilityHansen(it.T_matrix, alpha),
    }));
  }, [result.iterations, alpha]);

  if (series.length === 0) return null;

  const first = series[0]!;
  const last = series[series.length - 1]!;

  return (
    <div
      className={cn(className)}
      style={{
        border: "1px solid var(--rule)",
        background: "var(--paper)",
      }}
    >
      <div
        style={{
          padding: "10px 14px 8px",
          borderBottom: "1px solid var(--rule)",
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-fig)",
            fontSize: 10,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            color: "var(--accent)",
            fontWeight: 600,
          }}
        >
          {t("coupled_metrics.header")}
        </div>
        <div
          style={{
            fontFamily: "var(--font-fig)",
            fontSize: 10,
            color: "var(--muted)",
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          {t("coupled_metrics.outer_count", { n: series.length })}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 0,
        }}
      >
        <MetricCell
          label={t("coupled_metrics.segregation")}
          unit={t("coupled_metrics.segregation_unit")}
          current={last.segregation}
          baseline={first.segregation}
          values={series.map((s) => s.segregation)}
          hint={t("coupled_metrics.segregation_hint")}
          positiveIsGood={false}
          format={(v) => v.toFixed(3)}
        />

        <MetricCell
          label={t("coupled_metrics.welfare")}
          unit={t("coupled_metrics.welfare_unit")}
          current={aggregateMean(last.welfare)}
          baseline={aggregateMean(first.welfare)}
          values={series.map((s) => aggregateMean(s.welfare))}
          hint={t("coupled_metrics.welfare_hint")}
          positiveIsGood={true}
          stratumBreakdown={last.welfare}
          stratumLabels={[
            t("strata.alto"),
            t("strata.medio"),
            t("strata.bajo"),
          ]}
          format={(v) => (Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2))}
        />

        <MetricCell
          label={t("coupled_metrics.accessibility")}
          unit={t("coupled_metrics.accessibility_unit")}
          current={aggregateMean(last.accessibility)}
          baseline={aggregateMean(first.accessibility)}
          values={series.map((s) => aggregateMean(s.accessibility))}
          hint={t("coupled_metrics.accessibility_hint")}
          positiveIsGood={true}
          stratumBreakdown={last.accessibility}
          stratumLabels={[
            t("strata.alto"),
            t("strata.medio"),
            t("strata.bajo"),
          ]}
          format={(v) => v.toFixed(3)}
        />
      </div>
    </div>
  );
}

/** Promedio ignorando valores null. Retorna null si no hay ninguno. */
function aggregateMean(xs: readonly (number | null)[]): number | null {
  const nums = xs.filter((x): x is number => x != null);
  if (nums.length === 0) return null;
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

interface MetricCellProps {
  label: string;
  unit: string;
  current: number | null;
  baseline: number | null;
  values: readonly (number | null)[];
  hint: string;
  /** Si true, subida = mejora (accesibilidad); si false, bajada = mejora (segregación). */
  positiveIsGood: boolean;
  stratumBreakdown?: readonly (number | null)[];
  stratumLabels?: readonly string[];
  format: (v: number) => string;
}

function MetricCell({
  label,
  unit,
  current,
  baseline,
  values,
  hint,
  positiveIsGood,
  stratumBreakdown,
  stratumLabels,
  format,
}: MetricCellProps) {
  const delta = current != null && baseline != null ? current - baseline : null;
  const trendColor =
    delta == null || Math.abs(delta) < 1e-9
      ? "var(--muted)"
      : (delta > 0) === positiveIsGood
      ? "var(--bici)"
      : "var(--accent)";
  const arrow = delta == null ? "" : delta > 1e-9 ? "↑" : delta < -1e-9 ? "↓" : "→";

  return (
    <div
      style={{
        padding: "14px 16px 12px",
        borderRight: "1px solid var(--rule)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
      className="coupled-metric-cell"
    >
      <div
        style={{
          fontFamily: "var(--font-fig)",
          fontSize: 10,
          fontWeight: 500,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "var(--muted)",
        }}
      >
        {label}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 8,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: "-0.01em",
            color: "var(--ink)",
            fontVariantNumeric: "tabular-nums",
            lineHeight: 1.1,
          }}
        >
          {current == null ? "—" : format(current)}
        </span>
        <span
          style={{
            fontFamily: "var(--font-fig)",
            fontSize: 10,
            color: "var(--muted)",
            letterSpacing: "0.04em",
          }}
        >
          {unit}
        </span>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 6,
          fontFamily: "var(--font-fig)",
          fontSize: 11,
          color: trendColor,
          fontVariantNumeric: "tabular-nums",
        }}
        title={hint}
      >
        <span style={{ fontWeight: 600 }}>{arrow}</span>
        <span>Δ {formatDelta(current, baseline)}</span>
      </div>

      <Sparkline values={values} color={trendColor} />

      {stratumBreakdown && stratumLabels && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 2,
            marginTop: 4,
            paddingTop: 6,
            borderTop: "1px dashed var(--rule)",
          }}
        >
          {stratumBreakdown.map((v, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontFamily: "var(--font-fig)",
                fontSize: 10,
                color: "var(--muted)",
                letterSpacing: "0.04em",
              }}
            >
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 8,
                    background: `var(--s${i + 1})`,
                  }}
                />
                {stratumLabels[i]}
              </span>
              <span
                style={{
                  color: "var(--ink-2)",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {v == null ? "—" : format(v)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface SparklineProps {
  values: readonly (number | null)[];
  color: string;
  width?: number;
  height?: number;
}

function Sparkline({ values, color, width = 140, height = 26 }: SparklineProps) {
  const nums = values.filter((v): v is number => v != null);
  if (nums.length < 2) return <div style={{ height }} />;

  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const range = Math.max(max - min, 1e-9);
  const n = values.length;

  const pts = values
    .map((v, i) => {
      if (v == null) return null;
      const x = (i / Math.max(n - 1, 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return { x, y };
    })
    .filter((p): p is { x: number; y: number } => p != null);

  if (pts.length < 2) return <div style={{ height }} />;

  const path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1]!;

  return (
    <svg width={width} height={height} style={{ display: "block" }} aria-hidden>
      <path d={path} stroke={color} strokeWidth={1.2} fill="none" strokeLinejoin="round" />
      <circle cx={last.x} cy={last.y} r={2.2} fill={color} />
    </svg>
  );
}
