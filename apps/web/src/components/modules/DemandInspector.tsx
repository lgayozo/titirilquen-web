import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { Section } from "@/components/ui/Section";
import { UtilityBreakdown } from "@/components/viz/UtilityBreakdown";
import type { IterationSnapshot, SimulationConfig, StratumId } from "@/lib/types";
import { calcularUtilidades } from "@/lib/utility";

interface DemandInspectorProps {
  config: SimulationConfig;
  lastIter?: IterationSnapshot;
}

/**
 * Permite al estudiante seleccionar (estrato, celda, tenencia de auto) y ver la
 * utilidad por modo descompuesta. Usa los tiempos de la última iteración si
 * está disponible; si no, flujo libre.
 */
export function DemandInspector({ config, lastIter }: DemandInspectorProps) {
  const { t } = useTranslation("simulator");

  const cbdIdx = Math.floor(config.city.n_celdas / 2);
  const [celda, setCelda] = useState(Math.max(0, cbdIdx - Math.floor(config.city.n_celdas / 4)));
  const [estrato, setEstrato] = useState<StratumId>(2);
  const [tieneAuto, setTieneAuto] = useState(true);

  const distKm = Math.abs(cbdIdx - celda) * (config.city.largo_ciudad_km / config.city.n_celdas);

  const tiempos = useMemo(() => {
    if (!lastIter) return null;
    return {
      auto_total: lastIter.t_auto[celda] ?? 0,
      bici_total: lastIter.t_bici[celda] ?? 0,
      tren_acceso: lastIter.t_tren_acceso[celda] ?? 0,
      tren_espera: lastIter.t_tren_espera[celda] ?? 0,
      tren_viaje: lastIter.t_tren_viaje[celda] ?? 0,
    };
  }, [lastIter, celda]);

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
    <Section title={t("sections.demand")} subtitle={t("demand_inspector.title")}>
      <div className="grid grid-cols-3 gap-3">
        <label className="text-xs">
          <span className="text-slate-600 dark:text-slate-300">
            {t("demand_inspector.stratum")}
          </span>
          <select
            value={estrato}
            onChange={(e) => setEstrato(Number(e.target.value) as StratumId)}
            className="mt-1 block w-full rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option value={1}>{t("demand_inspector.stratum_label_1")}</option>
            <option value={2}>{t("demand_inspector.stratum_label_2")}</option>
            <option value={3}>{t("demand_inspector.stratum_label_3")}</option>
          </select>
        </label>

        <label className="text-xs">
          <div className="flex items-baseline justify-between">
            <span className="text-slate-600 dark:text-slate-300">
              {t("demand_inspector.origin_km")}
            </span>
            <span className="font-mono text-xs tabular-nums">{distKm.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min={0}
            max={config.city.n_celdas - 1}
            step={1}
            value={celda}
            onChange={(e) => setCelda(Number(e.target.value))}
            className="mt-1 w-full accent-slate-900 dark:accent-slate-200"
          />
        </label>

        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={tieneAuto}
            onChange={(e) => setTieneAuto(e.target.checked)}
            className="h-3.5 w-3.5"
          />
          <span className="text-slate-600 dark:text-slate-300">
            {t("demand_inspector.has_car")}
          </span>
        </label>
      </div>

      <div className="mt-3 rounded bg-slate-50 p-3 dark:bg-slate-900">
        <UtilityBreakdown utilities={utilities} />
      </div>

      <p className="mt-2 text-[10px] text-slate-400 dark:text-slate-500">
        {lastIter ? t("demand_inspector.hint_with_sim") : t("demand_inspector.hint_no_sim")}
      </p>
    </Section>
  );
}
