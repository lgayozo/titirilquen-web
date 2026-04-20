import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Plus } from "lucide-react";

import { KPITable } from "@/components/compare/KPITable";
import { ScenarioCard } from "@/components/compare/ScenarioCard";
import { ScenarioFlowComparison } from "@/components/compare/ScenarioFlowComparison";
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
        config: s.config ? { city: { n_celdas: s.config.city.n_celdas, largo_ciudad_km: s.config.city.largo_ciudad_km } } : null,
      })),
    [scenarios]
  );

  const doneCount = scenarios.filter((s) => s.status === "done").length;
  const baseId = scenarios.find((s) => s.status === "done")?.id;

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-xl font-semibold">{t("compare.title")}</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {t("compare.subtitle")}
        </p>
      </header>

      <div className="grid gap-3 md:grid-cols-2">
        {scenarios.map((s, i) => (
          <ScenarioCard
            key={s.id}
            scenario={s}
            onRun={() => void runOne(s.id)}
            removable={i >= 2}
          />
        ))}
        {scenarios.length < 4 && (
          <button
            type="button"
            onClick={addScenario}
            className="flex min-h-[100px] items-center justify-center gap-1 rounded-lg border-2 border-dashed border-slate-300 text-sm text-slate-500 hover:border-slate-400 hover:text-slate-700 dark:border-slate-700 dark:text-slate-500 dark:hover:border-slate-600 dark:hover:text-slate-300"
          >
            <Plus className="h-4 w-4" aria-hidden />
            {t("compare.add_scenario")}
          </button>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => void runAll()}
          disabled={!scenarios.some((s) => s.config)}
          className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900"
        >
          ▶ {tC("actions.run_all")}
        </button>
        {doneCount > 0 && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {t("compare.ready_count", { done: doneCount, total: scenarios.length })}
          </span>
        )}
      </div>

      {doneCount > 0 && (
        <>
          <section>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
              {t("compare.kpis")}
            </h3>
            <KPITable scenarios={rows} baseId={baseId} />
          </section>

          <section>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {t("compare.flow_profile")}
              </h3>
              <div className="flex items-center gap-1 text-[11px]">
                {(["Auto", "Metro", "Bici"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={
                      mode === m
                        ? "rounded bg-slate-900 px-2 py-1 text-white dark:bg-slate-100 dark:text-slate-900"
                        : "rounded px-2 py-1 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
                    }
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
            <ScenarioFlowComparison scenarios={flowRows} mode={mode} />
          </section>
        </>
      )}
    </div>
  );
}
