/**
 * Primitivos compartidos para diagramas de flujo interactivos.
 *
 * Los diagramas concretos (MSAFlowchart, CoupledFlowchart) declaran sus
 * nodos y aristas como datos; este módulo se encarga del render SVG,
 * tooltip con KaTeX al hacer hover, y playback secuencial animado.
 */

import katex from "katex";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Pause, Play, RotateCcw } from "lucide-react";

import { cn } from "@/lib/cn";

export interface FlowNode {
  id: string;
  label: string;
  /** Número de paso (se muestra como §N). */
  num?: number;
  /** Centro del nodo en coordenadas del viewBox. */
  x: number;
  y: number;
  /** Ancho y alto del nodo (defaults según kind). */
  w?: number;
  h?: number;
  kind?: "step" | "decision" | "start" | "end";
  tooltip: {
    title: string;
    description?: string;
    /** Fuente KaTeX (sin $...$). */
    formula?: string;
    ref?: { path: string; label: string };
  };
}

export interface FlowEdge {
  from: string;
  to: string;
  /** Path SVG custom. Si no se entrega, se conecta verticalmente. */
  d?: string;
  label?: string;
  labelX?: number;
  labelY?: number;
  feedback?: boolean;
}

interface FlowchartProps {
  nodes: FlowNode[];
  edges: FlowEdge[];
  width: number;
  height: number;
  /** IDs en orden de reproducción. */
  playbackSteps: string[];
  className?: string;
  ariaLabel: string;
}

export function Flowchart({
  nodes,
  edges,
  width,
  height,
  playbackSteps,
  className,
  ariaLabel,
}: FlowchartProps) {
  const { t } = useTranslation("simulator");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const nodeById = useMemo(() => {
    const map = new Map<string, FlowNode>();
    nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [nodes]);

  // Playback: avanzar cada 900ms; al llegar al final, pausa.
  useEffect(() => {
    if (!playing) return;
    const iv = window.setInterval(() => {
      setActiveId((prev) => {
        const idx = prev == null ? -1 : playbackSteps.indexOf(prev);
        if (idx >= playbackSteps.length - 1) {
          setPlaying(false);
          return prev;
        }
        return playbackSteps[idx + 1] ?? null;
      });
    }, 900);
    return () => window.clearInterval(iv);
  }, [playing, playbackSteps]);

  const start = () => {
    if (activeId == null || activeId === playbackSteps[playbackSteps.length - 1]) {
      setActiveId(playbackSteps[0] ?? null);
    }
    setPlaying(true);
  };
  const pause = () => setPlaying(false);
  const reset = () => {
    setPlaying(false);
    setActiveId(null);
  };

  const displayedId = hoveredId ?? activeId;
  const hoveredNode = displayedId ? nodeById.get(displayedId) : null;

  // Posición del tooltip: al costado derecho del nodo hovered (o izquierdo
  // si está muy a la derecha). Coordenadas calculadas en el espacio del
  // viewBox y convertidas a px del contenedor.
  const tooltipPos = useMemo(() => {
    if (!hoveredNode || !wrapRef.current || !svgRef.current) return null;
    const wrapRect = wrapRef.current.getBoundingClientRect();
    const svgRect = svgRef.current.getBoundingClientRect();
    const scaleX = svgRect.width / width;
    const scaleY = svgRect.height / height;
    const w = hoveredNode.w ?? 280;
    const h = hoveredNode.h ?? 52;
    const nodeLeft = hoveredNode.x - w / 2;
    const nodeRight = hoveredNode.x + w / 2;
    const nodeTop = hoveredNode.y - h / 2;
    const svgOffsetLeft = svgRect.left - wrapRect.left;
    const svgOffsetTop = svgRect.top - wrapRect.top;
    // Tooltip a la derecha si hay espacio, si no a la izquierda
    const preferRight = hoveredNode.x + w / 2 + 280 <= width;
    const x = preferRight
      ? svgOffsetLeft + (nodeRight + 14) * scaleX
      : svgOffsetLeft + (nodeLeft - 14) * scaleX;
    const y = svgOffsetTop + nodeTop * scaleY;
    return { x, y, align: preferRight ? "left" : "right" };
  }, [hoveredNode, width, height]);

  return (
    <div ref={wrapRef} className={cn("flowchart", className)}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-label={ariaLabel}
        style={{ display: "block", maxWidth: "100%", height: "auto" }}
      >
        <defs>
          <marker
            id="fc-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerUnits="userSpaceOnUse"
            markerWidth="8"
            markerHeight="8"
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--ink)" />
          </marker>
          <marker
            id="fc-arrow-accent"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerUnits="userSpaceOnUse"
            markerWidth="8"
            markerHeight="8"
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)" />
          </marker>
        </defs>

        {/* Aristas */}
        {edges.map((edge, i) => {
          const from = nodeById.get(edge.from);
          const to = nodeById.get(edge.to);
          if (!from || !to) return null;
          const d = edge.d ?? defaultEdgePath(from, to);
          return (
            <g key={`e-${i}`}>
              <path
                d={d}
                fill="none"
                stroke={edge.feedback ? "var(--accent)" : "var(--ink)"}
                strokeWidth={edge.feedback ? 1.3 : 1.2}
                strokeDasharray={edge.feedback ? "4 3" : undefined}
                markerEnd={
                  edge.feedback ? "url(#fc-arrow-accent)" : "url(#fc-arrow)"
                }
              />
              {edge.label && (
                <text
                  x={edge.labelX ?? (from.x + to.x) / 2}
                  y={edge.labelY ?? (from.y + to.y) / 2}
                  className="fc-edge-label"
                  textAnchor="middle"
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodos */}
        {nodes.map((n) => {
          const w = n.w ?? 280;
          const h = n.h ?? 52;
          const isActive = activeId === n.id;
          const isHovered = hoveredId === n.id;
          const kind = n.kind ?? "step";
          return (
            <g
              key={n.id}
              transform={`translate(${n.x - w / 2} ${n.y - h / 2})`}
              className={cn(
                "fc-node",
                `fc-node--${kind}`,
                isActive && "fc-node--active",
                isHovered && "fc-node--hovered"
              )}
              onMouseEnter={() => setHoveredId(n.id)}
              onMouseLeave={() => setHoveredId((cur) => (cur === n.id ? null : cur))}
              tabIndex={0}
              onFocus={() => setHoveredId(n.id)}
              onBlur={() => setHoveredId((cur) => (cur === n.id ? null : cur))}
              role="button"
              aria-label={n.tooltip.title}
            >
              {kind === "decision" ? (
                <path
                  d={`M ${w / 2} 0 L ${w} ${h / 2} L ${w / 2} ${h} L 0 ${h / 2} Z`}
                  className="fc-node-shape"
                />
              ) : (
                <rect
                  x={0}
                  y={0}
                  width={w}
                  height={h}
                  className="fc-node-shape"
                />
              )}
              {n.num != null && (
                <text x={12} y={16} className="fc-node-num">
                  §{n.num}
                </text>
              )}
              <text
                x={w / 2}
                y={h / 2 + 4}
                textAnchor="middle"
                className="fc-node-label"
              >
                {n.label}
              </text>
            </g>
          );
        })}
      </svg>

      {hoveredNode && tooltipPos && (
        <div
          className={cn(
            "fc-tooltip",
            tooltipPos.align === "right" && "fc-tooltip--right"
          )}
          style={{
            left: tooltipPos.align === "right" ? undefined : tooltipPos.x,
            right:
              tooltipPos.align === "right"
                ? undefined
                : undefined /* computed below */,
            top: tooltipPos.y,
            transform:
              tooltipPos.align === "right"
                ? `translateX(calc(${tooltipPos.x}px - 100%))`
                : undefined,
          }}
          role="tooltip"
        >
          <div className="fc-tooltip-title">{hoveredNode.tooltip.title}</div>
          {hoveredNode.tooltip.description && (
            <p className="fc-tooltip-desc">{hoveredNode.tooltip.description}</p>
          )}
          {hoveredNode.tooltip.formula && <Katex src={hoveredNode.tooltip.formula} />}
          {hoveredNode.tooltip.ref && (
            <div className="fc-tooltip-ref">
              <span className="fc-tooltip-ref-label">
                {t("flowchart.source")}
              </span>{" "}
              <code>{hoveredNode.tooltip.ref.path}</code>{" "}
              <span className="fc-tooltip-ref-fn">{hoveredNode.tooltip.ref.label}</span>
            </div>
          )}
        </div>
      )}

      <div className="fc-controls">
        {playing ? (
          <button type="button" className="fc-btn" onClick={pause}>
            <Pause className="fc-icon" aria-hidden />
            {t("flowchart.pause")}
          </button>
        ) : (
          <button type="button" className="fc-btn fc-btn--primary" onClick={start}>
            <Play className="fc-icon" aria-hidden />
            {t("flowchart.play")}
          </button>
        )}
        <button type="button" className="fc-btn" onClick={reset} disabled={activeId == null}>
          <RotateCcw className="fc-icon" aria-hidden />
          {t("flowchart.reset")}
        </button>
        <span className="fc-step-indicator" aria-live="polite">
          {activeId
            ? `${playbackSteps.indexOf(activeId) + 1} / ${playbackSteps.length}`
            : `· / ${playbackSteps.length}`}
        </span>
      </div>
    </div>
  );
}

/** Default: línea recta vertical entre centros, acortada por h/2 a cada extremo. */
function defaultEdgePath(from: FlowNode, to: FlowNode): string {
  const fromH = from.h ?? 52;
  const toH = to.h ?? 52;
  const fy = from.y + fromH / 2;
  const ty = to.y - toH / 2;
  return `M ${from.x} ${fy} L ${to.x} ${ty}`;
}

function Katex({ src }: { src: string }) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(src, {
        throwOnError: false,
        displayMode: true,
      });
    } catch {
      return src;
    }
  }, [src]);
  return (
    <div
      className="fc-tooltip-formula"
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
