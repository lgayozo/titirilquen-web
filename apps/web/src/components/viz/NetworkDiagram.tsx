import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { IterationSnapshot, SimulationConfig, SimulationResult } from "@/lib/types";

interface NetworkDiagramProps {
  snapshot: IterationSnapshot;
  result: SimulationResult;
  config: SimulationConfig;
  className?: string;
}

const MARGIN = { top: 24, right: 16, bottom: 34, left: 54 };

/**
 * Red vial completa de la ciudad lineal. Muestra las 3 redes (auto, metro,
 * bici) como bandas horizontales paralelas; cada segmento coloreado según
 * su saturación (v/c). Permite ver de un vistazo dónde se forma la
 * congestión crítica y qué modo queda más tensionado por la política actual.
 */
export function NetworkDiagram({ snapshot, result, config, className }: NetworkDiagramProps) {
  const { t } = useTranslation("simulator");
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(900);
  const [hover, setHover] = useState<HoverPayload | null>(null);

  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(420, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const H = 280;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const plotH = H - MARGIN.top - MARGIN.bottom;
  const L = config.city.n_celdas;
  const lengthKm = config.city.largo_ciudad_km;
  const cellWidth = plotW / L;

  // Capacidades para computar v/c --------------------------------------------
  const capAuto = result.capacidad_auto * config.supply.car.num_pistas;
  const capTren = config.supply.train.capacidad_tren * config.supply.train.frec_max;
  const capBici = config.supply.bike.capacidad_pista;

  // Flujo acumulado hacia el CBD (igual que `supply/car.py` con np.cumsum).
  // En la ciudad lineal monocéntrica el volumen crítico no es la demanda
  // origen por celda sino el tráfico que *atraviesa* cada tramo rumbo al
  // centro — acumulando a la izquierda 0→CBD y a la derecha L→CBD.
  const flowAuto = useMemo(
    () => cumulativeFlowTowardCBD(snapshot.demanda_auto, L),
    [snapshot.demanda_auto, L]
  );
  const flowBici = useMemo(
    () => cumulativeFlowTowardCBD(snapshot.demanda_bici, L),
    [snapshot.demanda_bici, L]
  );

  const vcAuto = useMemo(
    () => flowAuto.map((q) => (capAuto > 0 ? q / capAuto : 0)),
    [flowAuto, capAuto]
  );
  const vcBici = useMemo(
    () => flowBici.map((q) => (capBici > 0 ? q / capBici : 0)),
    [flowBici, capBici]
  );

  // Metro: `result.carga_metro` es la carga (pax/h) por tramo interestación.
  // Para pintar la banda y llenar el tooltip, proyectamos la carga del tramo
  // más cercano a cada celda del espacio.
  const flowMetro = useMemo(() => {
    const carga = result.carga_metro ?? [];
    const estaciones = result.estaciones_km ?? [];
    if (carga.length === 0 || estaciones.length < 2) {
      return new Array(L).fill(0) as number[];
    }
    const out: number[] = new Array(L).fill(0);
    for (let i = 0; i < L; i++) {
      const xKm = ((i + 0.5) / L) * lengthKm;
      let tramoIdx = 0;
      for (let s = 0; s < estaciones.length - 1; s++) {
        const a = estaciones[s]!;
        const b = estaciones[s + 1]!;
        if (xKm >= a && xKm <= b) {
          tramoIdx = s;
          break;
        }
      }
      out[i] = carga[tramoIdx] ?? 0;
    }
    return out;
  }, [result.carga_metro, result.estaciones_km, L, lengthKm]);

  const vcMetro = useMemo(
    () => flowMetro.map((q) => (capTren > 0 ? q / capTren : 0)),
    [flowMetro, capTren]
  );

  // Bandas (y centers) -------------------------------------------------------
  const bandH = 40;
  const bandGap = 12;
  const bandsTop = MARGIN.top + 18;
  const yAuto = bandsTop;
  const yMetro = bandsTop + bandH + bandGap;
  const yBici = bandsTop + 2 * (bandH + bandGap);

  const cbdX = MARGIN.left + plotW / 2;

  // Stations proyectadas ------------------------------------------------------
  const stations = useMemo(() => {
    return (result.estaciones_km ?? []).map((km) => MARGIN.left + (km / lengthKm) * plotW);
  }, [result.estaciones_km, lengthKm, plotW]);

  // X ticks
  const xTicks = useMemo(() => {
    const n = 5;
    return Array.from({ length: n }, (_, i) => ({
      km: (i / (n - 1)) * lengthKm,
      x: MARGIN.left + (i / (n - 1)) * plotW,
    }));
  }, [lengthKm, plotW]);

  const onEnter = (payload: HoverPayload) => setHover(payload);
  const onLeave = () => setHover(null);

  return (
    <div ref={wrapRef} className={cn("network-diagram", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", maxWidth: "100%", height: "auto" }}
        role="img"
        aria-label={t("network.aria")}
      >
        {/* Fondo de bandas con borde --------------------------------------- */}
        <BandFrame x={MARGIN.left} y={yAuto} w={plotW} h={bandH} label={t("modes.auto")} labelColor="var(--auto)" />
        <BandFrame x={MARGIN.left} y={yMetro} w={plotW} h={bandH} label={t("modes.metro")} labelColor="var(--metro)" />
        <BandFrame x={MARGIN.left} y={yBici} w={plotW} h={bandH} label={t("modes.bici")} labelColor="var(--bici)" />

        {/* Celdas de cada modo --------------------------------------------- */}
        {vcAuto.map((vc, i) => (
          <rect
            key={`a-${i}`}
            x={MARGIN.left + i * cellWidth}
            y={yAuto + 1}
            width={Math.max(cellWidth, 0.5)}
            height={bandH - 2}
            fill={colorForVC(vc)}
            onMouseEnter={() =>
              onEnter({
                mode: "auto",
                cell: i,
                vc,
                flow: flowAuto[i] ?? 0,
                cap: capAuto,
                time: snapshot.t_auto[i] ?? null,
                km: ((i + 0.5) / L) * lengthKm,
              })
            }
            onMouseLeave={onLeave}
          />
        ))}

        {/* División de pistas (líneas horizontales suaves) */}
        {Array.from({ length: Math.max(0, config.supply.car.num_pistas - 1) }).map((_, i) => {
          const y = yAuto + ((i + 1) * bandH) / config.supply.car.num_pistas;
          return (
            <line
              key={`lane-${i}`}
              x1={MARGIN.left}
              y1={y}
              x2={MARGIN.left + plotW}
              y2={y}
              stroke="var(--paper)"
              strokeWidth={0.8}
              opacity={0.5}
              pointerEvents="none"
            />
          );
        })}

        {vcMetro.map((vc, i) => (
          <rect
            key={`m-${i}`}
            x={MARGIN.left + i * cellWidth}
            y={yMetro + 1}
            width={Math.max(cellWidth, 0.5)}
            height={bandH - 2}
            fill={colorForVC(vc)}
            onMouseEnter={() =>
              onEnter({
                mode: "metro",
                cell: i,
                vc,
                flow: flowMetro[i] ?? 0,
                cap: capTren,
                time: (snapshot.t_tren_viaje[i] ?? 0) + (snapshot.t_tren_espera[i] ?? 0) + (snapshot.t_tren_acceso[i] ?? 0),
                km: ((i + 0.5) / L) * lengthKm,
              })
            }
            onMouseLeave={onLeave}
          />
        ))}

        {vcBici.map((vc, i) => (
          <rect
            key={`b-${i}`}
            x={MARGIN.left + i * cellWidth}
            y={yBici + 1}
            width={Math.max(cellWidth, 0.5)}
            height={bandH - 2}
            fill={colorForVC(vc)}
            onMouseEnter={() =>
              onEnter({
                mode: "bici",
                cell: i,
                vc,
                flow: flowBici[i] ?? 0,
                cap: capBici,
                time: snapshot.t_bici[i] ?? null,
                km: ((i + 0.5) / L) * lengthKm,
              })
            }
            onMouseLeave={onLeave}
          />
        ))}

        {/* Estaciones de metro (sobre la banda metro) ---------------------- */}
        {stations.map((x, i) => (
          <g key={`st-${i}`}>
            <line
              x1={x}
              y1={yMetro - 3}
              x2={x}
              y2={yMetro + bandH + 3}
              stroke="var(--ink)"
              strokeWidth={1}
              opacity={0.5}
              pointerEvents="none"
            />
            <circle cx={x} cy={yMetro + bandH / 2} r={3} fill="var(--paper)" stroke="var(--ink)" strokeWidth={1.2} pointerEvents="none" />
          </g>
        ))}

        {/* CBD vertical ----------------------------------------------------- */}
        <line
          x1={cbdX}
          y1={MARGIN.top}
          x2={cbdX}
          y2={MARGIN.top + plotH}
          stroke="var(--accent)"
          strokeWidth={1.2}
          strokeDasharray="3 3"
          pointerEvents="none"
        />
        <text x={cbdX} y={MARGIN.top - 6} textAnchor="middle" className="label" fill="var(--accent)">
          CBD
        </text>

        {/* Eje X (km) ------------------------------------------------------- */}
        <line
          x1={MARGIN.left}
          y1={H - MARGIN.bottom + 4}
          x2={MARGIN.left + plotW}
          y2={H - MARGIN.bottom + 4}
          stroke="var(--ink)"
          strokeWidth={0.8}
        />
        {xTicks.map((tick, i) => (
          <g key={`x-${i}`}>
            <line x1={tick.x} y1={H - MARGIN.bottom + 4} x2={tick.x} y2={H - MARGIN.bottom + 8} stroke="var(--ink)" strokeWidth={0.8} />
            <text x={tick.x} y={H - MARGIN.bottom + 20} textAnchor="middle" className="label" style={{ fontVariantNumeric: "tabular-nums" }}>
              {tick.km.toFixed(0)}
            </text>
          </g>
        ))}
        <text x={MARGIN.left + plotW / 2} y={H - 4} textAnchor="middle" className="label">
          {t("network.x_axis")}
        </text>
      </svg>

      {hover && (
        <div className="network-tooltip" role="tooltip">
          <div className="nt-head" style={{ color: modeColor(hover.mode) }}>
            {t(`modes.${hover.mode === "bici" ? "bici" : hover.mode === "metro" ? "metro" : "auto"}`)} · {hover.km.toFixed(1)} km
          </div>
          <Row
            label={t("network.flow")}
            value={`${Math.round(hover.flow).toLocaleString()} ${t(`network.unit.${hover.mode}`)}`}
          />
          <Row
            label={t("network.capacity")}
            value={`${Math.round(hover.cap).toLocaleString()} ${t(`network.unit.${hover.mode}`)}`}
          />
          <Row label={t("network.vc")} value={hover.vc.toFixed(2)} emph={hover.vc > 1} />
          {hover.time != null && <Row label={t("network.time")} value={`${hover.time.toFixed(1)} min`} />}
        </div>
      )}

      <Legend t={t} />
    </div>
  );
}

function Row({ label, value, emph }: { label: string; value: string; emph?: boolean }) {
  return (
    <div className="nt-row">
      <span className="nt-label">{label}</span>
      <span className={cn("nt-value", emph && "nt-value--emph")}>{value}</span>
    </div>
  );
}

function Legend({ t }: { t: (k: string) => string }) {
  return (
    <div className="network-legend">
      <span className="nl-label">{t("network.legend.scale")}</span>
      <div
        className="nl-gradient"
        role="img"
        aria-label={t("network.legend.scale")}
      />
      <span className="nl-lo">{t("network.legend.free")}</span>
      <span className="nl-mid">{t("network.legend.moderate")}</span>
      <span className="nl-hi">{t("network.legend.saturated")}</span>
    </div>
  );
}

function BandFrame({
  x,
  y,
  w,
  h,
  label,
  labelColor,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  labelColor: string;
}) {
  return (
    <g pointerEvents="none">
      <rect x={x} y={y} width={w} height={h} fill="var(--paper-2)" stroke="var(--rule)" strokeWidth={0.8} />
      <text x={x - 8} y={y + h / 2 + 3} textAnchor="end" className="network-band-label" fill={labelColor}>
        {label.toUpperCase()}
      </text>
    </g>
  );
}

/**
 * Gradiente continuo verde→naranja→rojo en función de v/c ∈ [0, 1+].
 * Usa `color-mix` para interpolar entre las CSS vars de los modos, así el
 * sistema responde a los 3 temas sin hardcodear RGB.
 */
function colorForVC(vc: number): string {
  const v = Math.max(0, Math.min(1.2, vc));
  if (v <= 0.5) {
    const t = v / 0.5;
    const pct = Math.round(t * 100);
    return `color-mix(in srgb, var(--bici) ${100 - pct}%, var(--auto))`;
  }
  const t = Math.min(1, (v - 0.5) / 0.5);
  const pct = Math.round(t * 100);
  return `color-mix(in srgb, var(--auto) ${100 - pct}%, var(--metro))`;
}

/**
 * Acumula la demanda por celda hacia el CBD central, espejando el cálculo
 * `np.cumsum` del core Python (`supply/car.py`). En el CBD el flujo vuelve
 * a cero (ya arribaron todos los viajes).
 */
function cumulativeFlowTowardCBD(perCellDemand: readonly number[], L: number): number[] {
  const cbd = Math.floor(L / 2);
  const out = new Array(L).fill(0);
  let cum = 0;
  for (let i = 0; i < cbd; i++) {
    cum += perCellDemand[i] ?? 0;
    out[i] = cum;
  }
  cum = 0;
  for (let i = L - 1; i > cbd; i--) {
    cum += perCellDemand[i] ?? 0;
    out[i] = cum;
  }
  return out;
}

function modeColor(m: "auto" | "metro" | "bici"): string {
  return `var(--${m})`;
}

interface HoverPayload {
  mode: "auto" | "metro" | "bici";
  cell: number;
  vc: number;
  flow: number;
  cap: number;
  time: number | null;
  km: number;
}
