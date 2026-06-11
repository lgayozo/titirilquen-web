import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus } from "lucide-react";

import { ComparisonHighlights } from "@/components/compare/ComparisonHighlights";
import { KPITable } from "@/components/compare/KPITable";
import {
  MetricCompareTable,
  type MetricCol,
  type MetricRow,
} from "@/components/compare/MetricCompareTable";
import { ScenarioCard } from "@/components/compare/ScenarioCard";
import { ScenarioFlowComparison } from "@/components/compare/ScenarioFlowComparison";
import { Panel } from "@/components/ui/Panel";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import { runSimulation } from "@/lib/api";
import { defaultLandUseConfig, solveCoupled, solveLandUse } from "@/lib/api-v2";
import { computeKPIs } from "@/lib/kpis";
import { theilSegregation } from "@/lib/metrics";
import { pyodideEngine } from "@/lib/pyodide-engine";
import type { Modo } from "@/lib/types";
import type { LandUseConfig, LandUseSolveResponse } from "@/lib/types-v2";
import {
  useCompareStore,
  type CompareKind,
  type Scenario,
} from "@/store/compareStore";
import { useSimulationStore } from "@/store/simulationStore";

const KINDS: CompareKind[] = ["transport", "land_use", "coupled"];

/** Iteraciones exteriores del acoplado en modo comparación: acotadas para que
 * 4 escenarios sigan siendo interactivos (tol 1 min suele cortar antes). */
const COMPARE_OUTER_MAX = 8;

function scaledLandUse(lu: LandUseConfig, poblacion: number): LandUseConfig {
  const sum = lu.H_por_estrato.reduce((a, b) => a + b, 0) || 1;
  const H = lu.H_por_estrato.map((h) =>
    Math.max(1, Math.round((poblacion * h) / sum)),
  ) as [number, number, number];
  return { ...lu, H_por_estrato: H };
}

/** Métricas comparables del equilibrio de suelo (mismas que LandUsePage). */
function landUseValues(
  r: LandUseSolveResponse,
  largoKm: number,
): Record<string, number> {
  const kmPerCell = largoKm / Math.max(r.L, 1);
  const sum = [0, 0, 0];
  const cnt = [0, 0, 0];
  for (let i = 0; i < r.parcelas.length; i++) {
    const dkm = Math.abs(i - r.CBD) * kmPerCell;
    for (const h of r.parcelas[i] ?? []) {
      const k = h - 1;
      if (k >= 0 && k < 3) {
        sum[k]! += dkm;
        cnt[k]! += 1;
      }
    }
  }
  const dist = (k: number) => (cnt[k]! > 0 ? sum[k]! / cnt[k]! : 0);
  return {
    theil: theilSegregation(r.result.Q),
    dist_alto: dist(0),
    dist_medio: dist(1),
    dist_bajo: dist(2),
  };
}

/** Métricas comparables del equilibrio acoplado (desde el reporte final). */
function coupledValues(sc: Scenario): Record<string, number | null> | null {
  const cr = sc.coupledResult;
  if (!cr) return null;
  const sis = cr.last.sistema;
  const bajo = cr.last.por_estrato[cr.last.por_estrato.length - 1];
  return {
    theil: sis.segregacion_theil,
    t_medio: sis.tiempo_medio_min,
    auto: (sis.reparto_modal.Auto ?? 0) * 100,
    carga_bajo: (bajo?.carga_costo_ingreso ?? 0) * 100,
    ratio_carga: sis.ratio_carga_bajo_alto,
    bienestar: sis.delta_bienestar_total_clp,
    emisiones: sis.emisiones_total_kg,
    iteraciones: cr.iterations,
  };
}

export function ComparePage() {
  const { t } = useTranslation("simulator");
  const { t: tC } = useTranslation("common");
  const kind = useCompareStore((s) => s.kind);
  const setKind = useCompareStore((s) => s.setKind);
  const scenarios = useCompareStore((s) => s.scenarios);
  const setStatus = useCompareStore((s) => s.setStatus);
  const setTransportResult = useCompareStore((s) => s.setTransportResult);
  const setLuResult = useCompareStore((s) => s.setLuResult);
  const setCoupledResult = useCompareStore((s) => s.setCoupledResult);
  const setError = useCompareStore((s) => s.setError);
  const addScenario = useCompareStore((s) => s.addScenario);
  const [mode, setMode] = useState<Modo>("Auto");

  const untitled = (id: string) => t("compare.scenario_card.untitled", { id });

  const runOne = async (id: string) => {
    const st = useCompareStore.getState();
    const sc = st.scenarios.find((s) => s.id === id);
    if (!sc?.config) return;
    const k = st.kind;
    setStatus(id, "running");
    try {
      if (k === "transport") {
        const engine = useSimulationStore.getState().engine;
        const result =
          engine === "api"
            ? await runSimulation(sc.config)
            : await pyodideEngine.simulate(sc.config);
        setTransportResult(id, result);
      } else if (k === "land_use") {
        const L = sc.config.city.n_celdas;
        const r = await solveLandUse({
          L,
          CBD: Math.floor(L / 2),
          largo_km: sc.config.city.largo_ciudad_km,
          land_use: sc.landUse ?? defaultLandUseConfig,
        });
        setLuResult(id, r);
      } else {
        const lu = scaledLandUse(sc.landUse ?? defaultLandUseConfig, sc.poblacion);
        const res = await solveCoupled({
          sim: sc.config,
          land_use: lu,
          outer_max_iter: COMPARE_OUTER_MAX,
          outer_tol: 1.0,
        });
        const its = res.iterations;
        if (!its.length) throw new Error("coupled: sin iteraciones");
        setCoupledResult(id, {
          first: its[0]!.metrics,
          last: its[its.length - 1]!.metrics,
          iterations: its.length,
          converged: res.converged,
        });
      }
    } catch (e) {
      setError(id, e instanceof Error ? e.message : String(e));
    }
  };

  const runAll = async () => {
    await Promise.all(
      useCompareStore
        .getState()
        .scenarios.filter((s) => s.config && s.status !== "running")
        .map((s) => runOne(s.id)),
    );
  };

  // ---- Transporte (la comparación original) ----
  const rows = useMemo(
    () =>
      scenarios.map((s) => ({
        id: s.id,
        name: s.name || untitled(s.id),
        kpis:
          s.result && s.config
            ? computeKPIs(
                s.result,
                s.config.city.largo_ciudad_km,
                s.config.city.n_celdas,
                s.config.demand.globales.v_caminata,
              )
            : null,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scenarios, t],
  );

  const flowRows = useMemo(
    () =>
      scenarios.map((s) => ({
        id: s.id,
        name: s.name || untitled(s.id),
        result: s.result,
        config: s.config
          ? {
              city: {
                n_celdas: s.config.city.n_celdas,
                largo_ciudad_km: s.config.city.largo_ciudad_km,
              },
            }
          : null,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scenarios, t],
  );

  // ---- Suelo ----
  const luCols = useMemo<MetricCol[]>(
    () =>
      scenarios.map((s) => ({
        id: s.id,
        name: s.name || untitled(s.id),
        values:
          s.luResult && s.config
            ? landUseValues(s.luResult, s.config.city.largo_ciudad_km)
            : null,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scenarios, t],
  );

  const luRows = useMemo<MetricRow[]>(
    () => [
      { key: "theil", label: t("compare.lu.theil"), fmt: (v) => v.toFixed(3), betterWhen: "down" },
      { key: "dist_alto", label: t("compare.lu.dist_alto"), fmt: (v) => `${v.toFixed(2)} km` },
      { key: "dist_medio", label: t("compare.lu.dist_medio"), fmt: (v) => `${v.toFixed(2)} km` },
      { key: "dist_bajo", label: t("compare.lu.dist_bajo"), fmt: (v) => `${v.toFixed(2)} km` },
    ],
    [t],
  );

  // ---- Ciudad en equilibrio ----
  const cpCols = useMemo<MetricCol[]>(
    () =>
      scenarios.map((s) => ({
        id: s.id,
        name:
          (s.name || untitled(s.id)) +
          (s.coupledResult && !s.coupledResult.converged
            ? ` ${t("compare.not_converged")}`
            : ""),
        values: coupledValues(s),
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scenarios, t],
  );

  const fmtInt = (v: number) => Math.round(v).toLocaleString("es-CL");
  const cpRows = useMemo<MetricRow[]>(
    () => [
      { key: "theil", label: t("compare.cp.theil"), fmt: (v) => v.toFixed(3), betterWhen: "down" },
      { key: "t_medio", label: t("compare.cp.t_medio"), fmt: (v) => `${v.toFixed(1)} min`, betterWhen: "down" },
      { key: "auto", label: t("compare.cp.auto"), fmt: (v) => `${v.toFixed(1)}%` },
      { key: "carga_bajo", label: t("compare.cp.carga_bajo"), fmt: (v) => `${v.toFixed(1)}%`, betterWhen: "down" },
      { key: "ratio_carga", label: t("compare.cp.ratio_carga"), fmt: (v) => `${v.toFixed(2)}×`, betterWhen: "down" },
      { key: "bienestar", label: t("compare.cp.bienestar"), fmt: (v) => `$${fmtInt(v)}`, betterWhen: "up" },
      { key: "emisiones", label: t("compare.cp.emisiones"), fmt: (v) => `${fmtInt(v)} kg/h`, betterWhen: "down" },
      { key: "iteraciones", label: t("compare.cp.iteraciones"), fmt: (v) => `${Math.round(v)}` },
    ],
    [t],
  );

  const doneCount = scenarios.filter((s) => s.status === "done").length;
  const runningCount = scenarios.filter((s) => s.status === "running").length;
  const baseId = scenarios.find((s) => s.status === "done")?.id;

  return (
    <div className="main" style={{ padding: "var(--pad)", maxWidth: 1600, margin: "0 auto" }}>
      <div className="hero">
        <div className="hero-head">
          <h1 className="hero-title">{t("compare.title")}</h1>
          <div className="hero-sub">
            <span className="dot">●</span> {t("compare.subtitle")}
          </div>
        </div>

        {/* Lente de comparación: qué solver corre sobre los mismos escenarios. */}
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className="font-fig text-[10px] uppercase tracking-[0.1em] text-muted">
            {t("compare.kind_label")}
          </span>
          <div className="seg">
            {KINDS.map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={kind === k ? "active" : ""}
              >
                {t(`compare.kind.${k}`)}
              </button>
            ))}
          </div>
          {kind === "coupled" && (
            <span className="text-[11px] text-muted">{t("compare.coupled_hint")}</span>
          )}
        </div>
      </div>

      <div className="panel-grid" style={{ marginBottom: "var(--gap)" }}>
        {scenarios.map((s, i) => (
          <div key={s.id} className="col-6">
            <ScenarioCard scenario={s} onRun={() => void runOne(s.id)} removable={i >= 2} />
          </div>
        ))}
        {scenarios.length < 4 && (
          <div className="col-6">
            <button
              type="button"
              onClick={addScenario}
              className="flex min-h-[120px] w-full items-center justify-center gap-2"
              style={{
                border: "1px dashed var(--rule)",
                background: "var(--paper)",
                fontFamily: "var(--font-fig)",
                fontSize: 11,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--muted)",
                cursor: "pointer",
              }}
            >
              <Plus className="h-4 w-4" aria-hidden />
              {t("compare.add_scenario")}
            </button>
          </div>
        )}
      </div>

      <div className="mb-4 flex items-center gap-3">
        <button
          type="button"
          onClick={() => void runAll()}
          disabled={!scenarios.some((s) => s.config)}
          className="btn primary"
        >
          ▶ {tC("actions.run_all")}
        </button>
        {runningCount > 0 && (
          <span
            className="flex items-center gap-2 font-fig text-[11px] uppercase tracking-[0.08em] text-muted"
            role="status"
          >
            <span className="pulse-dot" aria-hidden />
            {t("compare.processing", { count: runningCount })}
          </span>
        )}
        {doneCount > 0 && (
          <span className="font-fig text-[11px] uppercase tracking-[0.08em] text-muted">
            {t("compare.ready_count", { done: doneCount, total: scenarios.length })}
          </span>
        )}
      </div>

      {doneCount > 0 && kind === "transport" && (
        <div className="panel-grid">
          <Panel n="00" title={t("compare.highlights")} meta="auto · diff" cls="col-12">
            <ComparisonHighlights scenarios={rows} baseId={baseId} />
          </Panel>

          <Panel n="01" title={t("compare.kpis")} meta="delta vs base" cls="col-12">
            <KPITable scenarios={rows} baseId={baseId} />
          </Panel>

          <Panel
            n="02"
            title={t("compare.flow_profile")}
            meta={
              <div className="seg">
                {(["Auto", "Metro", "Bici"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={mode === m ? "active" : ""}
                  >
                    {t(`modes.${m.toLowerCase()}`)}
                  </button>
                ))}
              </div>
            }
            cls="col-12"
          >
            <ScenarioFlowComparison scenarios={flowRows} mode={mode} />
          </Panel>
        </div>
      )}

      {doneCount > 0 && kind === "land_use" && (
        <div className="panel-grid">
          <Panel n="00" title={t("compare.lu.table_title")} meta="delta vs base" cls="col-12">
            <MetricCompareTable cols={luCols} rows={luRows} baseId={baseId} />
          </Panel>
          {scenarios
            .filter((s) => s.luResult)
            .map((s) => (
              <Panel
                key={s.id}
                n={s.id}
                title={`${t("compare.lu.dist_title")} · ${s.name || untitled(s.id)}`}
                meta="bid-rent"
                cls="col-6"
              >
                <StratumDistribution parcelas={s.luResult!.parcelas} />
              </Panel>
            ))}
        </div>
      )}

      {doneCount > 0 && kind === "coupled" && (
        <div className="panel-grid">
          <Panel n="00" title={t("compare.cp.table_title")} meta="delta vs base" cls="col-12">
            <MetricCompareTable cols={cpCols} rows={cpRows} baseId={baseId} />
            <p className="kpi-caption" style={{ marginTop: 8 }}>
              {t("compare.cp.caption")}
            </p>
          </Panel>
        </div>
      )}
    </div>
  );
}
