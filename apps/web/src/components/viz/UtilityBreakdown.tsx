import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { Modo } from "@/lib/types";
import { probabilidadesLogit, type UtilityBreakdown as UB } from "@/lib/utility";

interface UtilityBreakdownProps {
  utilities: Record<Modo, UB>;
  className?: string;
}

const MODE_COLORS: Record<Modo, string> = {
  Auto: "var(--auto)",
  Metro: "var(--metro)",
  Bici: "var(--bici)",
  Caminata: "var(--walk)",
  Teletrabajo: "var(--tele)",
};

const COMPONENT_COLORS = {
  asc: "var(--muted)",
  v_tiempo: "var(--walk)",
  v_costo: "var(--metro)",
  v_penalizaciones: "var(--s1)",
};

/**
 * Utility breakdown editorial con normalización simétrica: cada lado de la
 * barra se escala al máximo acumulado (positivo / negativo) de los
 * componentes entre todos los modos feasibles. Esto garantiza que las
 * componentes apiladas nunca se desborden del contenedor.
 *
 * Tipografía equilibrada: modo 11px, V 12px, P 18px serif.
 * Filas compactas (32px) para que la tabla entera case visualmente con
 * figuras en paralelo (ej. FIG. 6).
 */
export function UtilityBreakdown({ utilities, className }: UtilityBreakdownProps) {
  const { t } = useTranslation("simulator");
  const probs = useMemo(() => probabilidadesLogit(utilities), [utilities]);

  const modes: Modo[] = ["Auto", "Metro", "Bici", "Caminata"];

  // Normalización: máximo entre la suma positiva y la suma negativa de
  // cualquier modo feasible. Cada mitad de la barra (± 50%) usa este tope.
  const { maxAbsSide } = useMemo(() => {
    let max = 0.1;
    for (const modo of modes) {
      const u = utilities[modo];
      if (!u.feasible) continue;
      const sumPos =
        (u.asc > 0 ? u.asc : 0) +
        (u.v_tiempo > 0 ? u.v_tiempo : 0) +
        (u.v_costo > 0 ? u.v_costo : 0) +
        (u.v_penalizaciones > 0 ? u.v_penalizaciones : 0);
      const sumNeg =
        (u.asc < 0 ? -u.asc : 0) +
        (u.v_tiempo < 0 ? -u.v_tiempo : 0) +
        (u.v_costo < 0 ? -u.v_costo : 0) +
        (u.v_penalizaciones < 0 ? -u.v_penalizaciones : 0);
      max = Math.max(max, sumPos, sumNeg);
    }
    return { maxAbsSide: max };
  }, [utilities]);

  const GRID = "64px 1fr 52px 56px";

  return (
    <div className={cn("w-full", className)}>
      <div
        className="grid items-center gap-3 border-b pb-1.5 font-fig text-[10px] uppercase tracking-[0.1em] text-muted"
        style={{ gridTemplateColumns: GRID, borderColor: "var(--rule)" }}
      >
        <span>{t("utility_breakdown.mode")}</span>
        <span>{t("utility_breakdown.breakdown")}</span>
        <span className="text-right">{t("utility_breakdown.v")}</span>
        <span className="text-right">{t("utility_breakdown.p")}</span>
      </div>

      <div className="flex flex-col">
        {modes.map((modo) => {
          const u = utilities[modo];
          const p = probs[modo] ?? 0;
          const isLast = modo === modes[modes.length - 1];
          const rowStyle = {
            gridTemplateColumns: GRID,
            borderColor: "var(--rule)",
          } as const;

          if (!u.feasible) {
            return (
              <div
                key={modo}
                className={cn(
                  "grid items-center gap-3 py-2 opacity-45",
                  !isLast && "border-b"
                )}
                style={rowStyle}
              >
                <span
                  className="font-fig text-[11px] font-semibold uppercase tracking-[0.04em]"
                  style={{ color: MODE_COLORS[modo] }}
                >
                  {t(`modes.${modo.toLowerCase()}`)}
                </span>
                <span className="font-fig text-[10px] italic text-muted">
                  {t("utility_breakdown.infeasible")}
                </span>
                <span className="text-right font-fig text-[12px] tabular-nums">—</span>
                <span className="text-right font-fig text-[13px] font-semibold tabular-nums text-muted">
                  0%
                </span>
              </div>
            );
          }

          return (
            <div
              key={modo}
              className={cn("grid items-center gap-3 py-2", !isLast && "border-b")}
              style={rowStyle}
            >
              <span
                className="font-fig text-[11px] font-semibold uppercase tracking-[0.04em]"
                style={{ color: MODE_COLORS[modo] }}
              >
                {t(`modes.${modo.toLowerCase()}`)}
              </span>
              <UtilityBar u={u} maxAbsSide={maxAbsSide} />
              <span className="text-right font-fig text-[12px] tabular-nums">
                {u.valor.toFixed(2)}
              </span>
              <span
                className="text-right font-fig text-[13px] font-semibold tabular-nums"
                style={{ color: "var(--ink)" }}
              >
                {(p * 100).toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>

      <div
        className="mt-2 flex flex-wrap gap-x-4 gap-y-1 border-t pt-2 font-fig text-[10px] uppercase tracking-[0.06em] text-muted"
        style={{ borderColor: "var(--rule)" }}
      >
        <Swatch color={COMPONENT_COLORS.asc} label={t("utility_breakdown.asc")} />
        <Swatch color={COMPONENT_COLORS.v_tiempo} label={t("utility_breakdown.beta_tiempo")} />
        <Swatch color={COMPONENT_COLORS.v_costo} label={t("utility_breakdown.beta_costo")} />
        <Swatch
          color={COMPONENT_COLORS.v_penalizaciones}
          label={t("utility_breakdown.penalizaciones")}
        />
      </div>
    </div>
  );
}

/**
 * Barra divergente con apilado seguro: nunca se desborda de los 50% de cada
 * lado porque la normalización usa `maxAbsSide ≥ sumPos ≥ sumNeg` individuales.
 */
function UtilityBar({ u, maxAbsSide }: { u: UB; maxAbsSide: number }) {
  const parts = [
    { key: "asc", v: u.asc, color: COMPONENT_COLORS.asc },
    { key: "v_tiempo", v: u.v_tiempo, color: COMPONENT_COLORS.v_tiempo },
    { key: "v_costo", v: u.v_costo, color: COMPONENT_COLORS.v_costo },
    { key: "v_penalizaciones", v: u.v_penalizaciones, color: COMPONENT_COLORS.v_penalizaciones },
  ].filter((p) => p.v !== 0);

  const negs = parts.filter((p) => p.v < 0);
  const poss = parts.filter((p) => p.v > 0);
  let negCursor = 50;
  let posCursor = 50;

  return (
    <div
      className="relative h-4 w-full"
      style={{ background: "var(--paper-2)", border: "1px solid var(--rule)" }}
    >
      <div
        className="absolute left-1/2 top-0 h-full"
        style={{ width: 1, background: "var(--ink)", opacity: 0.6 }}
      />
      {negs.map((p) => {
        const w = (Math.abs(p.v) / maxAbsSide) * 50;
        negCursor -= w;
        return (
          <div
            key={p.key}
            className="absolute top-0 h-full transition-all"
            style={{
              left: `${negCursor}%`,
              width: `${w}%`,
              backgroundColor: p.color,
              opacity: 0.9,
            }}
            title={`${p.key} = ${p.v.toFixed(3)}`}
          />
        );
      })}
      {poss.map((p) => {
        const w = (p.v / maxAbsSide) * 50;
        const left = posCursor;
        posCursor += w;
        return (
          <div
            key={p.key}
            className="absolute top-0 h-full transition-all"
            style={{
              left: `${left}%`,
              width: `${w}%`,
              backgroundColor: p.color,
              opacity: 0.9,
            }}
            title={`${p.key} = ${p.v.toFixed(3)}`}
          />
        );
      })}
    </div>
  );
}

function Swatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="inline-block h-2 w-3" style={{ backgroundColor: color }} aria-hidden />
      <span>{label}</span>
    </span>
  );
}
