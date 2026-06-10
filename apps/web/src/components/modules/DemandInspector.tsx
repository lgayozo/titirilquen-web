import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { UtilityBreakdown } from "@/components/viz/UtilityBreakdown";
import type { IterationSnapshot, SimulationConfig, StratumId } from "@/lib/types";
import { calcularUtilidades } from "@/lib/utility";

interface DemandInspectorProps {
  config: SimulationConfig;
  lastIter?: IterationSnapshot;
}

/**
 * Inspector de utilidad — controles en una sola fila: estrato · origen · auto.
 * Slider ocupa el espacio sobrante. Breakdown compacto debajo.
 */
export function DemandInspector({ config, lastIter }: DemandInspectorProps) {
  const { t } = useTranslation("simulator");

  const cbdIdx = Math.floor(config.city.n_celdas / 2);
  const [celda, setCelda] = useState(
    Math.max(0, cbdIdx - Math.floor(config.city.n_celdas / 4))
  );
  const [estrato, setEstrato] = useState<StratumId>(2);
  const [tieneAuto, setTieneAuto] = useState(true);

  // Clamp por si la grilla se achicó después de elegir la celda.
  const celdaEff = Math.min(celda, config.city.n_celdas - 1);

  const cellKm = config.city.largo_ciudad_km / config.city.n_celdas;
  const distKm = Math.abs(cbdIdx - celdaEff) * cellKm;
  const posKm = (celdaEff + 0.5) * cellKm;

  const tiempos = useMemo(() => {
    if (!lastIter) return null;
    return {
      auto_total: lastIter.t_auto[celdaEff] ?? 0,
      bici_total: lastIter.t_bici[celdaEff] ?? 0,
      tren_acceso: lastIter.t_tren_acceso[celdaEff] ?? 0,
      tren_espera: lastIter.t_tren_espera[celdaEff] ?? 0,
      tren_viaje: lastIter.t_tren_viaje[celdaEff] ?? 0,
    };
  }, [lastIter, celdaEff]);

  const utilities = useMemo(
    () =>
      calcularUtilidades({
        estrato,
        distKm,
        tieneAuto,
        config: config.demand,
        tiempos,
      }),
    [estrato, distKm, tieneAuto, config.demand, tiempos]
  );

  return (
    <div className="flex w-full flex-col gap-3">
      {/* Controles en una sola fila — select estrato, slider origen, checkbox auto */}
      <div
        className="grid items-end gap-4 border-b pb-3"
        style={{
          gridTemplateColumns: "minmax(140px, 170px) 1fr auto",
          borderColor: "var(--rule)",
        }}
      >
        <label className="flex flex-col gap-1">
          <span className="font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
            {t("demand_inspector.stratum")}
          </span>
          <select
            value={estrato}
            onChange={(e) => setEstrato(Number(e.target.value) as StratumId)}
            style={{
              background: "var(--paper)",
              border: "1px solid var(--rule)",
              padding: "6px 8px",
              color: "var(--ink)",
              fontFamily: "var(--font-body)",
              fontSize: 12,
            }}
          >
            <option value={1}>{t("demand_inspector.stratum_label_1")}</option>
            <option value={2}>{t("demand_inspector.stratum_label_2")}</option>
            <option value={3}>{t("demand_inspector.stratum_label_3")}</option>
          </select>
        </label>

        <label className="slider-row m-0 flex flex-col gap-1">
          <div className="srow-top">
            <span className="font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
              {t("demand_inspector.origin_km")}
            </span>
            <span className="srow-val tabular-nums" aria-hidden>
              {t("demand_inspector.position_value", {
                pos: posKm.toFixed(1),
                dist: distKm.toFixed(1),
              })}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={config.city.n_celdas - 1}
            step={1}
            value={celdaEff}
            onChange={(e) => setCelda(Number(e.target.value))}
            className="w-full"
          />
          {/* Escala: el slider recorre la ciudad de oeste a este; el CBD (el
              destino) está al CENTRO, no al inicio — por eso la distancia baja
              y vuelve a subir. */}
          <div className="flex justify-between font-fig text-[9px] uppercase tracking-[0.06em] text-muted">
            <span>0 km</span>
            <span style={{ color: "var(--accent)" }}>
              {t("demand_inspector.cbd_center", {
                km: (config.city.largo_ciudad_km / 2).toFixed(0),
              })}
            </span>
            <span>{config.city.largo_ciudad_km} km</span>
          </div>
        </label>

        <label
          className="flex cursor-pointer select-none items-center gap-2 whitespace-nowrap"
          style={{ paddingBottom: 6 }}
        >
          <input
            type="checkbox"
            checked={tieneAuto}
            onChange={(e) => setTieneAuto(e.target.checked)}
            className="h-3.5 w-3.5"
            style={{ accentColor: "var(--ink)" }}
          />
          <span className="font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
            {t("demand_inspector.has_car")}
          </span>
        </label>
      </div>

      <UtilityBreakdown utilities={utilities} />

      <p className="font-fig text-[10px] uppercase tracking-[0.06em] text-muted">
        {lastIter ? t("demand_inspector.hint_with_sim") : t("demand_inspector.hint_no_sim")}
      </p>
      <p className="text-[11px] leading-snug text-muted" style={{ marginTop: -6 }}>
        {t("demand_inspector.interpretation")}
      </p>
    </div>
  );
}
