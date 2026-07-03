import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface StrataHeatmapProps {
  /** Composición por celda ANTES del equilibrio (mezcla uniforme). [L][3] shares. */
  before: readonly (readonly number[])[];
  /** Composición por celda DESPUÉS del equilibrio. [L][3] shares. */
  after: readonly (readonly number[])[];
  className?: string;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.trim().replace("#", "");
  const s =
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h;
  const n = parseInt(s || "888888", 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const MARGIN = { top: 18, right: 8, bottom: 22, left: 64 };
const STRIP_H = 40;
const STRIP_GAP = 30;

/**
 * Mapa de calor de la **composición de estratos** a lo largo de la ciudad lineal,
 * ANTES (mezcla uniforme por celda) y DESPUÉS del equilibrio (ordenada por el
 * bid-rent). Cada celda se pinta con la mezcla de los colores de estrato ponderada
 * por sus participaciones. Hace visible el ordenamiento espacial que produce la
 * subasta (la densidad total por celda es fija — ver el perfil de densidad —; lo
 * que cambia es quién vive dónde).
 */
export function StrataHeatmap({ before, after, className }: StrataHeatmapProps) {
  const { t } = useTranslation("simulator");
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(700);
  const [colors, setColors] = useState<[number, number, number][]>([
    [62, 42, 95],
    [178, 67, 26],
    [45, 90, 61],
  ]);

  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const cs = getComputedStyle(el);
    setColors(
      [1, 2, 3].map((k) =>
        hexToRgb(cs.getPropertyValue(`--s${k}`) || "#888888"),
      ) as [number, number, number][],
    );
    const update = () => setW(Math.max(320, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const blend = (shares: readonly number[]) => {
    let r = 0,
      g = 0,
      b = 0,
      tot = 0;
    for (let h = 0; h < 3; h++) {
      const w = shares[h] ?? 0;
      const c = colors[h]!;
      r += c[0] * w;
      g += c[1] * w;
      b += c[2] * w;
      tot += w;
    }
    if (tot > 0) {
      r /= tot;
      g /= tot;
      b /= tot;
    }
    return `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`;
  };

  const H = MARGIN.top + STRIP_H * 2 + STRIP_GAP + MARGIN.bottom;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const L = Math.max(before.length, after.length);
  const cellW = plotW / Math.max(L, 1);
  const cbd = Math.floor(L / 2);
  const cbdX = MARGIN.left + (cbd + 0.5) * cellW;
  const yBefore = MARGIN.top;
  const yAfter = MARGIN.top + STRIP_H + STRIP_GAP;

  const strip = (data: readonly (readonly number[])[], y: number) =>
    data.map((sh, i) => (
      <rect
        key={i}
        x={MARGIN.left + i * cellW}
        y={y}
        width={Math.max(cellW + 0.5, 0.8)}
        height={STRIP_H}
        fill={blend(sh)}
      />
    ));

  return (
    <div ref={wrapRef} className={cn("relative", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", maxWidth: "100%" }}
        role="img"
        aria-label={t("land_use.heatmap_title")}
      >
        <text
          x={MARGIN.left - 8}
          y={yBefore + STRIP_H / 2}
          textAnchor="end"
          dominantBaseline="middle"
          className="label"
        >
          {t("land_use.heatmap_before")}
        </text>
        <text
          x={MARGIN.left - 8}
          y={yAfter + STRIP_H / 2}
          textAnchor="end"
          dominantBaseline="middle"
          className="label"
        >
          {t("land_use.heatmap_after")}
        </text>

        {strip(before, yBefore)}
        {strip(after, yAfter)}

        {[yBefore, yAfter].map((y, k) => (
          <line
            key={k}
            x1={cbdX}
            y1={y - 3}
            x2={cbdX}
            y2={y + STRIP_H + 3}
            stroke="var(--accent)"
            strokeWidth={1}
            strokeDasharray="2 2"
          />
        ))}
        <text
          x={cbdX}
          y={MARGIN.top - 6}
          textAnchor="middle"
          className="label"
          fill="var(--accent)"
        >
          CBD
        </text>
        <text x={MARGIN.left} y={H - 6} textAnchor="start" className="label">
          PERIFERIA
        </text>
        <text
          x={MARGIN.left + plotW}
          y={H - 6}
          textAnchor="end"
          className="label"
        >
          PERIFERIA
        </text>
      </svg>

      <div
        className="mt-2 flex flex-wrap gap-4"
        style={{ fontFamily: "var(--font-fig)", fontSize: 10 }}
      >
        {[1, 2, 3].map((h) => (
          <span
            key={h}
            className="flex items-center gap-1.5"
            style={{ color: "var(--muted)" }}
          >
            <span
              className="inline-block"
              style={{ width: 10, height: 10, backgroundColor: `var(--s${h})` }}
            />
            <span style={{ color: "var(--ink-2)" }}>
              {t(`strata.${h === 1 ? "alto" : h === 2 ? "medio" : "bajo"}`)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
