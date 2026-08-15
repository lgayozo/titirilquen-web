import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { AgentRecord, Modo } from "@/lib/types";

interface UtilityScatterProps {
  agents: readonly AgentRecord[];
  nCeldas: number;
  largoKm: number;
  height?: number;
  /** Cota de puntos a dibujar (se submuestrea por stride para no saturar el SVG). */
  maxPoints?: number;
  className?: string;
}

const MARGIN = { top: 12, right: 12, bottom: 28, left: 46 };

const TRAVEL_MODES: Modo[] = ["Auto", "Metro", "Bici", "Caminata"];
const MODE_COLORS: Record<Modo, string> = {
  Auto: "var(--auto)",
  Metro: "var(--metro)",
  Bici: "var(--bici)",
  Caminata: "var(--walk)",
  Teletrabajo: "var(--tele)",
};

/**
 * Dispersión de la utilidad elegida (eje Y) contra la distancia al CBD (eje X),
 * coloreada por modo. Los teletrabajadores (sin viaje) se excluyen. Si hay
 * demasiados agentes se submuestrea por stride para mantener el SVG liviano.
 */
export function UtilityScatter({
  agents,
  nCeldas,
  largoKm,
  height = 200,
  maxPoints = 2500,
  className,
}: UtilityScatterProps) {
  const { t } = useTranslation("simulator");

  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(600);
  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(280, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const cellKm = largoKm / nCeldas;
  // Eje X = posición en la ciudad (0 → L), con el CBD al centro (como FIG 08).
  const xMax = largoKm;

  const { points, yMin, yMax, shown, total } = useMemo(() => {
    const pts = agents.filter(
      (a) =>
        a.modo_elegido &&
        a.modo_elegido !== "Teletrabajo" &&
        isFinite(a.utilidad_elegida),
    );
    const stride = Math.max(1, Math.ceil(pts.length / maxPoints));
    const sampled = pts.filter((_, i) => i % stride === 0);
    let yLo = Infinity;
    let yHi = -Infinity;
    const mapped = sampled.map((a) => {
      const pos = (a.celda_origen + 0.5) * cellKm;
      const u = a.utilidad_elegida;
      if (u < yLo) yLo = u;
      if (u > yHi) yHi = u;
      return { x: pos, y: u, mode: a.modo_elegido as Modo };
    });
    if (!isFinite(yLo)) {
      yLo = 0;
      yHi = 1;
    }
    return {
      points: mapped,
      yMin: yLo,
      yMax: yHi,
      shown: mapped.length,
      total: pts.length,
    };
  }, [agents, cellKm, maxPoints]);

  const H = height;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;
  const ySpan = yMax - yMin || 1;

  const xOf = (km: number) => MARGIN.left + (km / xMax) * plotW;
  const yOf = (u: number) => MARGIN.top + plotH - ((u - yMin) / ySpan) * plotH;

  // Solo extremos: el centro lo ocupa el marcador del CBD.
  const xTicks = [0, xMax];
  const cbdX = MARGIN.left + plotW / 2;
  const yTicks = [yMin, yMin + ySpan / 2, yMax];
  const fmtY = (v: number) => (Math.abs(v) >= 10 ? v.toFixed(0) : v.toFixed(1));

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="block"
        style={{
          display: "block",
          maxWidth: "100%",
          background: "var(--paper-2)",
          border: "1px solid var(--rule)",
        }}
        role="img"
        aria-label={t("sandbox.utility_scatter")}
      >
        {/* Grid + Y labels */}
        {yTicks.map((v, i) => (
          <g key={`y-${i}`}>
            <line
              x1={MARGIN.left}
              y1={yOf(v)}
              x2={MARGIN.left + plotW}
              y2={yOf(v)}
              stroke="var(--rule)"
              strokeWidth={0.6}
              strokeDasharray="2 3"
              opacity={0.6}
            />
            <text
              x={MARGIN.left - 6}
              y={yOf(v) + 3}
              textAnchor="end"
              className="label"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {fmtY(v)}
            </text>
          </g>
        ))}

        {/* X labels */}
        {xTicks.map((v, i) => (
          <text
            key={`x-${i}`}
            x={xOf(v)}
            y={H - 8}
            textAnchor={
              i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"
            }
            className="label"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {v.toFixed(0)}
          </text>
        ))}

        {/* Puntos */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={xOf(p.x)}
            cy={yOf(p.y)}
            r={1.6}
            fill={MODE_COLORS[p.mode]}
            opacity={0.5}
          />
        ))}

        {/* Ejes */}
        <line
          x1={MARGIN.left}
          y1={MARGIN.top}
          x2={MARGIN.left}
          y2={MARGIN.top + plotH}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />
        <line
          x1={MARGIN.left}
          y1={MARGIN.top + plotH}
          x2={MARGIN.left + plotW}
          y2={MARGIN.top + plotH}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />

        {/* Marcador del CBD (centro de la ciudad) */}
        <line
          x1={cbdX}
          y1={MARGIN.top}
          x2={cbdX}
          y2={MARGIN.top + plotH}
          stroke="var(--accent)"
          strokeWidth={1}
          strokeDasharray="3 3"
          opacity={0.8}
        />
        <text
          x={cbdX}
          y={MARGIN.top - 2}
          textAnchor="middle"
          className="label"
          fill="var(--accent)"
        >
          CBD
        </text>

        {/* Títulos de eje */}
        <text
          x={-MARGIN.top - plotH / 2}
          y={12}
          textAnchor="middle"
          transform="rotate(-90)"
          className="label"
        >
          {t("sandbox.utility_axis")}
        </text>
        <text
          x={MARGIN.left + plotW / 2}
          y={H - 8}
          textAnchor="middle"
          className="label"
        >
          {t("sandbox.position_axis")}
        </text>
      </svg>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-fig text-[10px] uppercase tracking-[0.04em]">
        {TRAVEL_MODES.map((m) => (
          <span key={m} className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: MODE_COLORS[m] }}
              aria-hidden
            />
            <span className="text-ink-2">{t(`modes.${m.toLowerCase()}`)}</span>
          </span>
        ))}
        {shown < total && (
          <span className="ml-auto normal-case tracking-normal text-muted">
            {t("sandbox.sample_note", {
              shown: shown.toLocaleString(),
              total: total.toLocaleString(),
            })}
          </span>
        )}
      </div>
    </div>
  );
}
