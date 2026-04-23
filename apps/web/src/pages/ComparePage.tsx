import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus } from "lucide-react";

import { KPITable } from "@/components/compare/KPITable";
import { ScenarioCard } from "@/components/compare/ScenarioCard";
import { ScenarioFlowComparison } from "@/components/compare/ScenarioFlowComparison";
import { Panel } from "@/components/ui/Panel";
import { runSimulation } from "@/lib/api";
import { computeKPIs } from "@/lib/kpis";
import type { Modo } from "@/lib/types";
import { useCompareStore } from "@/store/compareStore";

export function ComparePage() {
  const { t } = useTranslation("simulator");
  const { t: tC } = useTranslation("common");
  const scenarios = useCompareStore((s) => s.scenarios);
  const setStatus = useCompareStore((s) => s.setStatus);
  const setResult = useCompareStore((s) => s.setResult);
  const setError = useCompareStore((s) => s.setError);
  const addScenario = useCompareStore((s) => s.addScenario);
  const [mode, setMode] = useState<Modo>("Auto");

  const runOne = async (id: string) => {
    const sc = useCompareStore.getState().scenarios.find((s) => s.id === id);
    if (!sc?.config) return;
    setStatus(id, "running");
    try {
      const result = await runSimulation(sc.config);
      setResult(id, result);
    } catch (e) {
      setError(id, e instanceof Error ? e.message : String(e));
    }
  };

  const runAll = async () => {
    await Promise.all(
      useCompareStore
        .getState()
        .scenarios.filter((s) => s.config && s.status !== "running")
        .map((s) => runOne(s.id))
    );
  };

  const rows = useMemo(
    () =>
      scenarios.map((s) => ({
        id: s.id,
        name: s.name,
        kpis:
          s.result && s.config
            ? computeKPIs(s.result, s.config.city.largo_ciudad_km, s.config.city.n_celdas)
            : null,
      })),
    [scenarios]
  );

  const flowRows = useMemo(
    () =>
      scenarios.map((s) => ({
        id: s.id,
        name: s.name,
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
    [scenarios]
  );

  const doneCount = scenarios.filter((s) => s.status === "done").length;
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
        {doneCount > 0 && (
          <span className="font-fig text-[11px] uppercase tracking-[0.08em] text-muted">
            {t("compare.ready_count", { done: doneCount, total: scenarios.length })}
          </span>
        )}
      </div>

      {doneCount > 0 && (
        <div className="panel-grid">
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
    </div>
  );
}
