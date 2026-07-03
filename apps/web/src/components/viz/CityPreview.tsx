import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";
import type { SimulationConfig } from "@/lib/types";
import { useLandUseStore } from "@/store/landUseStore";

interface CityPreviewProps {
  config: SimulationConfig;
  className?: string;
}

const MARGIN = { top: 30, right: 16, bottom: 34, left: 130 };

/**
 * Posiciones (km) de las estaciones de metro, replicando el cálculo del core
 * (`supply/train.py`): estaciones equidistantes a paso `L/num_estaciones`,
 * ancladas en el CBD (centro) y recortadas a [0, L].
 */
function estacionesKm(largoKm: number, numEstaciones: number): number[] {
  if (numEstaciones <= 0) return [];
  const centro = largoKm / 2;
  const paso = largoKm / numEstaciones;
  const set = new Set<number>();
  for (let x = centro; x <= largoKm + 0.01; x += paso)
    set.add(Math.round(x * 1e6) / 1e6);
  for (let x = centro; x >= -0.01; x -= paso)
    set.add(Math.round(x * 1e6) / 1e6);
  return [...set].filter((x) => x >= 0 && x <= largoKm).sort((a, b) => a - b);
}

/** Bandas de infraestructura del "plano" (orden de apilado vertical). */
const BAND_H = 38;
const BAND_GAP = 14;
/** Franja de demanda (orígenes) — más baja que las de oferta, otra "capa". */
const DEMAND_H = 30;

/**
 * Vista de "plano" de la ciudad lineal a partir de la configuración, **sin
 * correr el equilibrio**. Muestra la infraestructura que definen los
 * parámetros: corredor de autos (nº de pistas), línea de metro con sus
 * estaciones, ciclovía y el perfil de pendiente. Es el primo "vacío" del
 * `NetworkDiagram` (que pinta saturación v/c una vez hay resultados): aquí no
 * hay flujos, solo geometría e infraestructura, para que el usuario vea lo que
 * está construyendo antes de simular.
 */
export function CityPreview({ config, className }: CityPreviewProps) {
  const { t } = useTranslation("simulator");
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [W, setW] = useState(900);

  useEffect(() => {
    if (!wrapRef.current) return;
    const el = wrapRef.current;
    const update = () => setW(Math.max(420, el.clientWidth));
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Opción A: la composición de estratos y la densidad las define Uso de Suelo.
  // La composición (proporciones) sale de H_por_estrato; la población exacta del
  // perfil densidad_celda del último resultado de suelo (si lo hay).
  const luConfig = useLandUseStore((s) => s.config);
  const luResult = useLandUseStore((s) => s.result);

  const largoKm = config.city.largo_ciudad_km;
  const nCeldas = config.city.n_celdas;
  const cbdIdx = Math.floor(nCeldas / 2);
  const numPistas = config.supply.car.num_pistas;
  const numEst = config.supply.train.num_estaciones;
  const pendiente = config.city.pendiente_porcentaje;

  // Proporciones de estratos = H_por_estrato normalizado (siempre disponible).
  const hTot = luConfig.H_por_estrato.reduce((a, b) => a + b, 0) || 1;
  const share = luConfig.H_por_estrato.map((h) => h / hTot) as [
    number,
    number,
    number,
  ];

  const dxMetros = Math.round((largoKm / nCeldas) * 1000);
  // Perfil densidad_celda válido solo si la geometría coincide con la del
  // resultado de suelo (si el usuario cambió L, el perfil viejo no aplica).
  const densidadCelda =
    luResult && luResult.densidad_celda.length === nCeldas
      ? luResult.densidad_celda
      : null;
  const densidadMediaKm = densidadCelda
    ? densidadCelda.reduce((a, b) => a + b, 0) / Math.max(densidadCelda.length, 1)
    : null;
  // Población = Σ_i densidad_celda(i)·Δx (exacta) cuando hay resultado de suelo.
  const poblacion = densidadCelda
    ? Math.round(
        densidadCelda.reduce((a, b) => a + b, 0) * (largoKm / nCeldas),
      )
    : null;

  const H = 320;
  const plotW = Math.max(1, W - MARGIN.left - MARGIN.right);
  const cbdX = MARGIN.left + plotW / 2;
  const xOfKm = (km: number) => MARGIN.left + (km / largoKm) * plotW;

  const bandsTop = MARGIN.top + 18;
  const yAuto = bandsTop;
  const yMetro = bandsTop + BAND_H + BAND_GAP;
  const yBici = bandsTop + 2 * (BAND_H + BAND_GAP);
  const yDemand = bandsTop + 3 * (BAND_H + BAND_GAP);

  const estaciones = useMemo(
    () => estacionesKm(largoKm, numEst),
    [largoKm, numEst],
  );

  // Comb de celdas en la franja de demanda: una marca por celda (salvo el CBD),
  // solo si son legibles (≥4 px). Hace tangible la discretización en N celdas.
  const cellTicks = useMemo(() => {
    if (plotW / nCeldas < 4) return [] as number[];
    const xs: number[] = [];
    for (let i = 0; i < nCeldas; i++) {
      if (i === cbdIdx) continue;
      xs.push(MARGIN.left + ((i + 0.5) / nCeldas) * plotW);
    }
    return xs;
  }, [plotW, nCeldas, cbdIdx]);

  const xTicks = useMemo(() => {
    const n = 5;
    return Array.from({ length: n }, (_, i) => ({
      km: (i / (n - 1)) * largoKm,
      x: MARGIN.left + (i / (n - 1)) * plotW,
    }));
  }, [largoKm, plotW]);

  // Perfil de pendiente: línea de terreno que se inclina según pendiente_%.
  // Subida hacia los bordes (el CBD al centro es la cota de referencia).
  const terrainY = MARGIN.top + 2;
  const terrainAmp = Math.min(14, Math.abs(pendiente) * 1.6);
  const terrainPath = useMemo(() => {
    const pts: string[] = [];
    const steps = 40;
    for (let i = 0; i <= steps; i++) {
      const f = i / steps; // 0..1 a lo largo del corredor
      const dxCentro = Math.abs(f - 0.5) * 2; // 0 en CBD, 1 en bordes
      const y = terrainY + terrainAmp * (1 - dxCentro);
      pts.push(`${MARGIN.left + f * plotW},${y}`);
    }
    return pts.join(" ");
  }, [plotW, terrainAmp, terrainY]);

  return (
    <div ref={wrapRef} className={cn("city-preview", className)}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block", maxWidth: "100%", height: "auto" }}
        role="img"
        aria-label={t("preview.aria")}
      >
        {/* Perfil de pendiente (sutil) */}
        {terrainAmp > 0.5 && (
          <g pointerEvents="none">
            <polyline
              points={terrainPath}
              fill="none"
              stroke="var(--muted)"
              strokeWidth={1}
              strokeDasharray="2 2"
              opacity={0.6}
            />
            <text
              x={MARGIN.left}
              y={terrainY - 4}
              className="label"
              fill="var(--muted)"
            >
              {t("preview.slope", { pct: pendiente })}
            </text>
          </g>
        )}

        {/* Banda AUTO — corredor con divisiones de pistas */}
        <InfraBand
          x={MARGIN.left}
          y={yAuto}
          w={plotW}
          label={t("modes.auto")}
          labelColor="var(--auto)"
          spec={t("preview.spec_auto", {
            lanes: numPistas,
            width: config.supply.car.ancho_pista_m,
          })}
        />
        {Array.from({ length: Math.max(0, numPistas - 1) }).map((_, i) => {
          const y = yAuto + ((i + 1) * BAND_H) / numPistas;
          return (
            <line
              key={`lane-${i}`}
              x1={MARGIN.left}
              y1={y}
              x2={MARGIN.left + plotW}
              y2={y}
              stroke="var(--auto)"
              strokeWidth={0.7}
              strokeDasharray="6 5"
              opacity={0.4}
              pointerEvents="none"
            />
          );
        })}

        {/* Banda METRO — línea + estaciones */}
        <InfraBand
          x={MARGIN.left}
          y={yMetro}
          w={plotW}
          label={t("modes.metro")}
          labelColor="var(--metro)"
          spec={t("preview.spec_metro", {
            stations: estaciones.length,
            cap: config.supply.train.capacidad_tren,
          })}
        />
        <line
          x1={MARGIN.left}
          y1={yMetro + BAND_H / 2}
          x2={MARGIN.left + plotW}
          y2={yMetro + BAND_H / 2}
          stroke="var(--metro)"
          strokeWidth={1.4}
          opacity={0.7}
          pointerEvents="none"
        />
        {estaciones.map((km, i) => (
          <circle
            key={`st-${i}`}
            cx={xOfKm(km)}
            cy={yMetro + BAND_H / 2}
            r={4}
            fill="var(--paper)"
            stroke="var(--metro)"
            strokeWidth={1.6}
            pointerEvents="none"
          />
        ))}

        {/* Banda BICI */}
        <InfraBand
          x={MARGIN.left}
          y={yBici}
          w={plotW}
          label={t("modes.bici")}
          labelColor="var(--bici)"
          spec={t("preview.spec_bici", {
            cap: config.supply.bike.capacidad_pista,
          })}
        />
        <line
          x1={MARGIN.left}
          y1={yBici + BAND_H / 2}
          x2={MARGIN.left + plotW}
          y2={yBici + BAND_H / 2}
          stroke="var(--bici)"
          strokeWidth={1.2}
          strokeDasharray="4 4"
          opacity={0.6}
          pointerEvents="none"
        />

        {/* Franja DEMANDA — orígenes de viaje. En V1: densidad uniforme (relleno
            plano), una marca por celda (comb) y el CBD excluido (sin orígenes). */}
        <g pointerEvents="none">
          <rect
            x={MARGIN.left}
            y={yDemand}
            width={plotW}
            height={DEMAND_H}
            fill="var(--paper-2)"
            stroke="var(--rule)"
            strokeWidth={0.8}
          />
          {/* Relleno uniforme = densidad constante en todas las celdas */}
          <rect
            x={MARGIN.left}
            y={yDemand + 4}
            width={plotW}
            height={DEMAND_H - 8}
            fill="var(--ink)"
            opacity={0.13}
          />
          {/* Comb de celdas (discretización) */}
          {cellTicks.map((x, i) => (
            <line
              key={`cell-${i}`}
              x1={x}
              y1={yDemand + 4}
              x2={x}
              y2={yDemand + DEMAND_H - 4}
              stroke="var(--ink)"
              strokeWidth={0.5}
              opacity={0.22}
            />
          ))}
          {/* CBD: sin orígenes (hueco marcado) */}
          <circle
            cx={cbdX}
            cy={yDemand + DEMAND_H / 2}
            r={3.5}
            fill="var(--paper)"
            stroke="var(--accent)"
            strokeWidth={1.4}
          />
          <text
            x={MARGIN.left - 8}
            y={yDemand + DEMAND_H / 2 - 1}
            textAnchor="end"
            className="network-band-label"
            fill="var(--ink-2)"
          >
            {t("preview.demand_label").toUpperCase()}
          </text>
          <text
            x={MARGIN.left - 8}
            y={yDemand + DEMAND_H / 2 + 11}
            textAnchor="end"
            className="label"
            fill="var(--muted)"
          >
            {densidadMediaKm != null
              ? t("preview.spec_demand_mean", {
                  dens: Math.round(densidadMediaKm),
                })
              : t("preview.spec_demand_land_use")}
          </text>
        </g>

        {/* CBD vertical */}
        <line
          x1={cbdX}
          y1={MARGIN.top}
          x2={cbdX}
          y2={yDemand + DEMAND_H + 6}
          stroke="var(--accent)"
          strokeWidth={1.2}
          strokeDasharray="3 3"
          pointerEvents="none"
        />
        <text
          x={cbdX}
          y={MARGIN.top - 6}
          textAnchor="middle"
          className="label"
          fill="var(--accent)"
        >
          CBD
        </text>

        {/* Eje X (km) */}
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
            <line
              x1={tick.x}
              y1={H - MARGIN.bottom + 4}
              x2={tick.x}
              y2={H - MARGIN.bottom + 8}
              stroke="var(--ink)"
              strokeWidth={0.8}
            />
            <text
              x={tick.x}
              y={H - MARGIN.bottom + 20}
              textAnchor="middle"
              className="label"
              style={{ fontVariantNumeric: "tabular-nums" }}
            >
              {tick.km.toFixed(0)}
            </text>
          </g>
        ))}
        <text
          x={MARGIN.left + plotW / 2}
          y={H - 4}
          textAnchor="middle"
          className="label"
        >
          {t("network.x_axis")}
        </text>
      </svg>

      {/* Pie: composición de estratos + texto explicativo (V1). El texto lleva
          los números, así no se duplica con una línea meta aparte. */}
      <div className="city-preview-foot">
        <div className="cpf-strata" aria-label={t("preview.strata_aria")}>
          {([0, 1, 2] as const).map((s) => (
            <span
              key={s}
              className="cpf-seg"
              style={{
                flex: Math.max(share[s], 0.001),
                background: `var(--s${s + 1})`,
              }}
              title={`${(share[s] * 100).toFixed(0)}%`}
            />
          ))}
        </div>
        <p className="cpf-caption">
          {poblacion != null
            ? t("preview.caption", {
                length: largoKm,
                cells: nCeldas,
                dx: dxMetros,
                pop: poblacion.toLocaleString(),
              })
            : t("preview.caption_no_pop", {
                length: largoKm,
                cells: nCeldas,
                dx: dxMetros,
              })}
        </p>
      </div>
    </div>
  );
}

function InfraBand({
  x,
  y,
  w,
  label,
  labelColor,
  spec,
}: {
  x: number;
  y: number;
  w: number;
  label: string;
  labelColor: string;
  spec: string;
}) {
  return (
    <g pointerEvents="none">
      <rect
        x={x}
        y={y}
        width={w}
        height={BAND_H}
        fill="var(--paper-2)"
        stroke="var(--rule)"
        strokeWidth={0.8}
      />
      <text
        x={x - 8}
        y={y + BAND_H / 2 - 1}
        textAnchor="end"
        className="network-band-label"
        fill={labelColor}
      >
        {label.toUpperCase()}
      </text>
      <text
        x={x - 8}
        y={y + BAND_H / 2 + 11}
        textAnchor="end"
        className="label"
        fill="var(--muted)"
      >
        {spec}
      </text>
    </g>
  );
}
