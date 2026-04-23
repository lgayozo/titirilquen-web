import { useEffect, useId, useMemo, useRef, useState } from "react";

import { cn } from "@/lib/cn";

interface CityStripProps {
  nCeldas: number;
  largoKm: number;
  pendientePct?: number;
  /** Perfil de tiempos por celda — eje Y (altura) */
  modeProfile?: Array<{ t_auto: number; t_metro: number; t_bici: number }>;
  /** Shares de estratos (A, M, B) — coloreado de barras */
  shareEstratos?: readonly [number, number, number];
  /** Tiempo seleccionado para colorear (auto|metro|bici) */
  heatMode?: "auto" | "metro" | "bici";
  /** Cuando cambia este token, se dispara un flash visual (para indicar "nueva iteración"). */
  iterationToken?: number | string;
  className?: string;
  height?: number;
}

/**
 * Visualización SVG de la ciudad lineal. Cada parcela es una barra vertical.
 * - Altura = tiempo de viaje del modo seleccionado (normalizado).
 * - Color = gradiente verde→rojo según congestión relativa.
 * - Pendiente visible como inclinación sutil del "piso".
 * - CBD marcado con una banderita roja.
 */
export function CityStrip({
  nCeldas,
  largoKm,
  pendientePct = 0,
  modeProfile,
  heatMode = "auto",
  iterationToken,
  className,
  height = 120,
}: CityStripProps) {
  const gradId = useId();
  const cbdIdx = Math.floor(nCeldas / 2);

  // Flash al cambiar iteración
  const [flash, setFlash] = useState(false);
  const prevToken = useRef(iterationToken);
  useEffect(() => {
    if (iterationToken !== undefined && iterationToken !== prevToken.current) {
      prevToken.current = iterationToken;
      setFlash(true);
      const tm = setTimeout(() => setFlash(false), 500);
      return () => clearTimeout(tm);
    }
  }, [iterationToken]);

  const barW = 100 / nCeldas;
  const svgW = 100;
  const svgH = 100;

  const bars = useMemo(() => {
    if (!modeProfile) {
      return Array.from({ length: nCeldas }, (_, i) => ({ idx: i, norm: 0 }));
    }
    const values = modeProfile.map((p) =>
      heatMode === "auto" ? p.t_auto : heatMode === "metro" ? p.t_metro : p.t_bici
    );
    const max = Math.max(...values, 1);
    return values.map((v, i) => ({ idx: i, norm: v / max }));
  }, [modeProfile, heatMode, nCeldas]);

  // Pendiente: desplaza el "piso" en Y según x (% de la ciudad)
  // p>0 sube a la derecha, p<0 baja a la derecha
  const slopeY = (xPct: number) => {
    const offset = (pendientePct / 20) * (xPct - 50);
    return 80 - offset;
  };

  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox={`0 0 ${svgW} ${svgH}`}
        preserveAspectRatio="none"
        className={cn("block w-full transition-colors", flash && "animate-iteration-flash")}
        style={{
          height,
          background: "var(--paper-2)",
          border: `1px solid ${flash ? "var(--accent)" : "var(--rule)"}`,
        }}
        role="img"
        aria-label="Ciudad lineal"
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--metro)" />
            <stop offset="50%" stopColor="var(--auto)" />
            <stop offset="100%" stopColor="var(--bici)" />
          </linearGradient>
        </defs>

        {/* Piso / pendiente */}
        <line
          x1={0}
          y1={slopeY(0)}
          x2={svgW}
          y2={slopeY(100)}
          stroke="var(--rule)"
          strokeWidth={0.3}
          strokeDasharray="0.5 0.5"
        />

        {/* Parcelas — animadas entre iteraciones vía transition CSS sobre y/height */}
        {bars.map(({ idx, norm }) => {
          const x = idx * barW;
          const isCbd = idx === cbdIdx;
          if (isCbd) return null; // CBD se dibuja aparte
          const barH = Math.max(0.5, norm * 50);
          const floorY = slopeY(x + barW / 2);
          return (
            <rect
              key={idx}
              x={x}
              y={floorY - barH}
              width={Math.max(barW - 0.05, 0.1)}
              height={barH}
              fill={modeProfile ? `url(#${gradId})` : "var(--rule)"}
              opacity={0.85}
              style={{
                transition: "y 400ms ease-out, height 400ms ease-out, fill 400ms ease-out",
              }}
            />
          );
        })}

        {/* CBD marker */}
        {(() => {
          const cbdX = cbdIdx * barW;
          const floorY = slopeY(cbdX + barW / 2);
          return (
            <g>
              <line
                x1={cbdX + barW / 2}
                y1={floorY}
                x2={cbdX + barW / 2}
                y2={floorY - 55}
                stroke="var(--accent)"
                strokeWidth={0.5}
                strokeDasharray="0.6 0.6"
              />
              <polygon
                points={`${cbdX + barW / 2},${floorY - 55} ${cbdX + barW / 2 + 4},${floorY - 53} ${cbdX + barW / 2},${floorY - 51}`}
                fill="var(--accent)"
              />
            </g>
          );
        })()}
      </svg>

      <div className="mt-1 flex justify-between font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
        <span>0 km</span>
        <span>CBD · {(largoKm / 2).toFixed(1)} km</span>
        <span>{largoKm.toFixed(0)} km</span>
      </div>
    </div>
  );
}
