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
  Auto: "#FF8C00",
  Metro: "#FF0000",
  Bici: "#228B22",
  Caminata: "#0000FF",
  Teletrabajo: "#A9A9A9",
};

const COMPONENT_COLORS = {
  asc: "#94a3b8",
  v_tiempo: "#38bdf8",
  v_costo: "#f43f5e",
  v_penalizaciones: "#a855f7",
};

/**
 * Muestra la utilidad de cada modo descompuesta en sus componentes (ASC,
 * tiempo, costo, penalizaciones) y la probabilidad logit resultante.
 */
export function UtilityBreakdown({ utilities, className }: UtilityBreakdownProps) {
  const { t } = useTranslation("simulator");
  const probs = useMemo(() => probabilidadesLogit(utilities), [utilities]);

  const modes: Modo[] = ["Auto", "Metro", "Bici", "Caminata"];
  const feasibles = modes.filter((m) => utilities[m].feasible);
  const values = feasibles.map((m) => utilities[m].valor);
  const minV = Math.min(...values, 0);
  const maxV = Math.max(...values, 0);
  const range = Math.max(Math.abs(minV), Math.abs(maxV), 0.1);

  return (
    <div className={cn("space-y-2", className)}>
      <div className="grid grid-cols-[70px_1fr_60px_50px] gap-2 text-[11px] font-medium text-slate-500 dark:text-slate-400">
        <span>{t("utility_breakdown.mode")}</span>
        <span>{t("utility_breakdown.breakdown")}</span>
        <span className="text-right">{t("utility_breakdown.v")}</span>
        <span className="text-right">{t("utility_breakdown.p")}</span>
      </div>

      {modes.map((modo) => {
        const u = utilities[modo];
        const p = probs[modo] ?? 0;
        if (!u.feasible) {
          return (
            <div key={modo} className="grid grid-cols-[70px_1fr_60px_50px] items-center gap-2 text-xs opacity-40">
              <span className="font-medium" style={{ color: MODE_COLORS[modo] }}>
                {t(`modes.${modo.toLowerCase()}`)}
              </span>
              <span className="italic text-slate-400">{t("utility_breakdown.infeasible")}</span>
              <span className="text-right font-mono tabular-nums">—</span>
              <span className="text-right font-mono tabular-nums">0%</span>
            </div>
          );
        }
        return (
          <div key={modo} className="grid grid-cols-[70px_1fr_60px_50px] items-center gap-2 text-xs">
            <span className="font-medium" style={{ color: MODE_COLORS[modo] }}>
              {t(`modes.${modo.toLowerCase()}`)}
            </span>
            <UtilityBar u={u} range={range} />
            <span className="text-right font-mono tabular-nums">
              {u.valor.toFixed(2)}
            </span>
            <span className="text-right font-mono tabular-nums font-medium">
              {(p * 100).toFixed(0)}%
            </span>
          </div>
        );
      })}

      <div className="pt-2 text-[10px] text-slate-500">
        <span className="mr-3">
          <Swatch color={COMPONENT_COLORS.asc} /> {t("utility_breakdown.asc")}
        </span>
        <span className="mr-3">
          <Swatch color={COMPONENT_COLORS.v_tiempo} /> {t("utility_breakdown.beta_tiempo")}
        </span>
        <span className="mr-3">
          <Swatch color={COMPONENT_COLORS.v_costo} /> {t("utility_breakdown.beta_costo")}
        </span>
        <span>
          <Swatch color={COMPONENT_COLORS.v_penalizaciones} /> {t("utility_breakdown.penalizaciones")}
        </span>
      </div>
    </div>
  );
}

function UtilityBar({ u, range }: { u: UB; range: number }) {
  const parts = [
    { key: "asc", v: u.asc, color: COMPONENT_COLORS.asc },
    { key: "v_tiempo", v: u.v_tiempo, color: COMPONENT_COLORS.v_tiempo },
    { key: "v_costo", v: u.v_costo, color: COMPONENT_COLORS.v_costo },
    { key: "v_penalizaciones", v: u.v_penalizaciones, color: COMPONENT_COLORS.v_penalizaciones },
  ].filter((p) => p.v !== 0);

  return (
    <div className="relative h-5 rounded bg-slate-100 dark:bg-slate-800">
      <div className="absolute left-1/2 top-0 h-full w-px bg-slate-400" />
      {parts.map((p) => {
        const w = (Math.abs(p.v) / range) * 50;
        const sign = p.v < 0 ? -1 : 1;
        const left = sign < 0 ? 50 - w : 50;
        return (
          <div
            key={p.key}
            className="absolute top-0 h-full opacity-80"
            style={{
              left: `${left}%`,
              width: `${w}%`,
              backgroundColor: p.color,
            }}
            title={`${p.key} = ${p.v.toFixed(3)}`}
          />
        );
      })}
    </div>
  );
}

function Swatch({ color }: { color: string }) {
  return (
    <span
      className="mr-1 inline-block h-2 w-2 rounded-sm align-middle"
      style={{ backgroundColor: color }}
    />
  );
}
