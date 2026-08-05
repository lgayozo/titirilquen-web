import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { CityStrip } from "@/components/CityStrip";
import { CalibrationPanel } from "@/components/modules/CalibrationPanel";
import { EconomyBuilder } from "@/components/modules/EconomyBuilder";
import { PresetGallery } from "@/components/modules/PresetGallery";
import { SupplyBuilder } from "@/components/modules/SupplyBuilder";
import { RunStatus } from "@/components/RunStatus";
import { SimulationSkeleton } from "@/components/SimulationSkeleton";
import { DemandInspector } from "@/components/modules/DemandInspector";
import { ExportableFigure } from "@/components/ui/ExportableFigure";
import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { Panel } from "@/components/ui/Panel";
import { SidebarSection } from "@/components/ui/SidebarSection";
import { CityPreview } from "@/components/viz/CityPreview";
import { ConvergenceTrace } from "@/components/viz/ConvergenceTrace";
import { FlowProfile } from "@/components/viz/FlowProfile";
import { ModeShareBars, type AgentGroup } from "@/components/viz/ModeShareBars";
import { ModeShareByLocation } from "@/components/viz/ModeShareByLocation";
import { NetworkDiagram } from "@/components/viz/NetworkDiagram";
import { ReferenceComparison } from "@/components/viz/ReferenceComparison";
import type { StatBar } from "@/components/viz/StatBars";
import { StratumDistribution } from "@/components/viz/StratumDistribution";
import {
  TransportMetricsTable,
  type TransportMetricsData,
} from "@/components/viz/TransportMetricsTable";
import { expectedComposition, smoothSupply } from "@/lib/citySupply";
import { pyodideEngine } from "@/lib/pyodide-engine";
import type { Modo } from "@/lib/types";
import { useLandUseStore } from "@/store/landUseStore";
import { isResultStale, useSimulationStore } from "@/store/simulationStore";

type HeatMode =
  | "auto"
  | "metro"
  | "bici"
  | "caminata"
  | "todos"
  | "espera"
  | "plano"
  | "suelo";

/** Opciones del toggle de la Figura 1, en orden. "plano" vuelve a la vista de
 *  infraestructura (CityPreview) sin perder los resultados. */
const VIEW_OPTIONS: readonly HeatMode[] = [
  "auto",
  "metro",
  "bici",
  "caminata",
  "todos",
  "espera",
  "plano",
  "suelo",
];

/** Umbral de factibilidad por modo (min): sobre él el modo deja de ser
 *  elegible. Ver demand/utility.py — caminata > 30, bici > 45. */
/** Modos del panel de flujos por celda (FIG. 02), en orden. */
type FlowMode = "auto" | "bici" | "metro" | "caminata";
const FLOW_MODES: readonly FlowMode[] = ["auto", "bici", "metro", "caminata"];

const MODE_CUTOFF: Partial<Record<HeatMode, number>> = {
  caminata: 30,
  bici: 45,
};

export function SandboxPage() {
  const { t } = useTranslation("simulator");
  const { t: tCommon } = useTranslation("common");
  const config = useSimulationStore((s) => s.config);
  const running = useSimulationStore((s) => s.running);
  const stage = useSimulationStore((s) => s.stage);
  const progress = useSimulationStore((s) => s.progress);
  const result = useSimulationStore((s) => s.result);
  const liveIterations = useSimulationStore((s) => s.liveIterations);
  const error = useSimulationStore((s) => s.error);
  const setConfig = useSimulationStore((s) => s.setConfig);
  const startRun = useSimulationStore((s) => s.startRun);
  const finishRun = useSimulationStore((s) => s.finishRun);
  const failRun = useSimulationStore((s) => s.failRun);
  const pushIteration = useSimulationStore((s) => s.pushIteration);
  const reset = useSimulationStore((s) => s.reset);
  const configUsed = useSimulationStore((s) => s.configUsed);
  const cancelRun = useSimulationStore((s) => s.cancelRun);
  const reference = useSimulationStore((s) => s.reference);
  const pinReference = useSimulationStore((s) => s.pinReference);
  const clearReference = useSimulationStore((s) => s.clearReference);

  // Opción A: la población del transporte se deriva del uso de suelo (densidad
  // por estrato → por celda). La config de suelo vive en su propio store y la
  // definen en la pestaña Uso de Suelo.
  const landUseConfig = useLandUseStore((s) => s.config);
  const landUseResult = useLandUseStore((s) => s.result);

  // Config de la corrida visible: el snapshot usado por el resultado, no la
  // viva — así las figuras no mezclan geometrías si el usuario mueve sliders.
  const cfgRes = configUsed ?? config;
  const stale = useMemo(
    () => isResultStale({ stage, config, configUsed }),
    [stage, config, configUsed],
  );

  const [heatMode, setHeatMode] = useState<HeatMode>("auto");
  const [flowMode, setFlowMode] = useState<FlowMode>("auto");

  const viewLabel = (m: HeatMode) =>
    m === "todos"
      ? t("sandbox.view_all")
      : m === "espera"
        ? t("sandbox.view_wait")
        : m === "plano"
          ? t("preview.tab")
          : m === "suelo"
            ? t("sandbox.view_land_use")
            : t(`modes.${m}`);

  const lastIter = liveIterations.at(-1) ?? result?.iteraciones.at(-1);
  // Antes de la primera iteración no hay perfil de tiempos: el hero muestra el
  // "plano" (CityPreview) en vez de la cinta de tiempos (CityStrip). Con
  // resultados, la pestaña "plano" del toggle vuelve a esa misma vista.
  const hasData = lastIter != null;
  // La ciudad como la define Uso de Suelo: se muestra antes de simular y,
  // después, cuando el toggle está en "suelo" (así la ciudad-input no
  // desaparece). "plano" vuelve a la vista de infraestructura.
  const showLandUseCity = !hasData || heatMode === "suelo";
  const showInfraPlano = hasData && heatMode === "plano";

  // Composición de estratos por celda para la imagen inicial de la ciudad,
  // derivada de Uso de Suelo: si hay un resultado de suelo con geometría
  // concordante, la composición de equilibrio (S·Q); si no, el estado inicial
  // (π_h = H_h/ΣH sobre la forma de la ciudad). Misma envolvente que las figuras
  // de Uso de Suelo (smoothSupply), así se lee como la misma ciudad.
  const landUseCity = useMemo(() => {
    const L = config.city.n_celdas;
    const CBD = Math.floor(L / 2);
    const lu = landUseConfig;
    const N = lu.H_por_estrato.reduce((a, b) => a + b, 0);
    if (N <= 0) return { comp: null as number[][] | null, isPost: false };
    const S = smoothSupply(
      lu.forma,
      L,
      CBD,
      lu.oferta_sigma_frac,
      lu.forma_param,
      N,
    );
    if (
      landUseResult &&
      landUseResult.L === L &&
      landUseResult.result?.Q?.length
    ) {
      return {
        comp: expectedComposition(landUseResult.result.Q, S),
        isPost: true,
      };
    }
    const pi = lu.H_por_estrato.map((h) => h / N);
    return {
      comp: S.map((s) => [s * pi[0]!, s * pi[1]!, s * pi[2]!]),
      isPost: false,
    };
  }, [config.city.n_celdas, landUseConfig, landUseResult]);

  const cellKm = cfgRes.city.largo_ciudad_km / cfgRes.city.n_celdas;
  const cbdIdx = Math.floor(cfgRes.city.n_celdas / 2);
  const vCaminata = cfgRes.demand.globales.v_caminata || 4.8;
  const profile = lastIter
    ? lastIter.t_auto.map((t_auto, i) => ({
        t_auto,
        t_metro:
          lastIter.t_tren_viaje[i]! +
          lastIter.t_tren_acceso[i]! +
          lastIter.t_tren_espera[i]!,
        t_bici: lastIter.t_bici[i]!,
        // Caminata: tiempo puramente geométrico (sin congestión), mismo
        // criterio que demand/utility.py → dist/v_caminata · 60.
        t_caminata: ((Math.abs(cbdIdx - i) * cellKm) / vCaminata) * 60,
        // Espera del metro (escalonada por estación; centro ≈ 0).
        t_espera: lastIter.t_tren_espera[i]!,
      }))
    : undefined;

  // Datos del panel de flujos. La escala Y es el máximo GLOBAL entre modos:
  // cambiar de modo no debe reescalar el eje o la comparación visual engaña.
  const flowData = useMemo(() => {
    if (!lastIter || !result) return null;
    const globalMax = Math.max(
      ...lastIter.demanda_auto,
      ...lastIter.demanda_bici,
      ...lastIter.demanda_metro,
      ...lastIter.demanda_caminata,
      1,
    );
    const porModo: Record<
      FlowMode,
      { flows: number[]; color: string; cap?: string }
    > = {
      auto: {
        flows: lastIter.demanda_auto,
        color: "var(--auto)",
        cap: `${Math.round(result.capacidad_auto)} veh/h corredor`,
      },
      bici: {
        flows: lastIter.demanda_bici,
        color: "var(--bici)",
        cap: `${cfgRes.supply.bike.capacidad_pista} bici/h`,
      },
      metro: {
        flows: lastIter.demanda_metro,
        color: "var(--metro)",
        cap: `${cfgRes.supply.train.capacidad_tren} pax/tren`,
      },
      caminata: { flows: lastIter.demanda_caminata, color: "var(--walk)" },
    };
    return { ...porModo[flowMode], globalMax };
  }, [lastIter, result, cfgRes, flowMode]);

  // v/c del equilibrio = flujo máximo ACUMULADO del corredor / capacidad.
  // La demanda originada por celda (demanda_auto[i]) NO sirve de numerador:
  // subestima el v/c ~60× porque ignora el cumsum hacia el CBD.
  const operatingRatios = {
    car:
      result?.flujos_auto_veh_h?.length && result.capacidad_auto > 0
        ? Math.max(...result.flujos_auto_veh_h) / result.capacidad_auto
        : null,
    bike: result?.flujos_bici_veh_h?.length
      ? Math.max(...result.flujos_bici_veh_h) /
        cfgRes.supply.bike.capacidad_pista
      : null,
    // Metro: carga máxima del tramo / capacidad OPERATIVA (f_op · K). Es el
    // análogo del v/c y faltaba — se mostraban solo dos de los tres modos con
    // oferta congestionable. Ojo: el core calcula la ρ del andén contra
    // frec_max (capacidad potencial), no contra f_op; acá interesa la que
    // realmente circula.
    metro:
      result?.carga_metro?.length && lastIter && lastIter.frecuencia_metro > 0
        ? Math.max(...result.carga_metro) /
          (lastIter.frecuencia_metro * cfgRes.supply.train.capacidad_tren)
        : null,
  };

  const abortRef = useRef<AbortController | null>(null);

  const handleRun = async () => {
    // Si el toggle quedó en una vista estática ("plano"/"suelo"), volver a una
    // vista de resultados para no tapar la convergencia en vivo.
    if (heatMode === "plano" || heatMode === "suelo") setHeatMode("auto");
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    startRun(config.max_iter);
    try {
      // Localización de estratos: si el equilibrio de pujas se corrió (hay
      // resultado de Uso de Suelo con geometría concordante), la población usa
      // esa localización de equilibrio; si no, la original (mezcla uniforme).
      // Mismo criterio que la imagen inicial (landUseCity.isPost).
      const final = await pyodideEngine.simulateStream(
        config,
        (snap) => pushIteration(snap),
        ctrl.signal,
        landUseConfig,
        landUseCity.isPost ? "equilibrio" : "original",
      );
      finishRun(final);
    } catch (e) {
      if (ctrl.signal.aborted) return; // cancelado por el usuario
      failRun(e instanceof Error ? e.message : String(e));
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    cancelRun();
  };

  const totalAgents = lastIter
    ? (Object.values(lastIter.modal_split) as number[]).reduce(
        (s, n) => s + n,
        0,
      )
    : 0;

  const kpis = useMemo<KPI[]>(() => {
    if (!result || !lastIter) {
      return [
        { label: t("kpi.trips"), value: "—" },
        { label: t("kpi.auto_pct"), value: "—" },
        { label: t("kpi.metro_pct"), value: "—" },
        { label: t("kpi.bici_pct"), value: "—" },
        { label: t("kpi.walk_pct"), value: "—" },
        { label: t("kpi.tele_pct"), value: "—" },
        { label: t("kpi.frequency"), value: "—" },
        { label: t("kpi.residual"), value: "—" },
        { label: t("kpi.co2"), value: "—" },
      ];
    }
    const modal = lastIter.modal_split;
    const total = (Object.values(modal) as number[]).reduce((s, n) => s + n, 0);
    const tot = total > 0 ? total : 1;
    const pct = (m: Modo) => `${(((modal[m] ?? 0) / tot) * 100).toFixed(1)}%`;
    const count = (m: Modo) =>
      t("kpi.trips_subline", { n: Math.round(modal[m] ?? 0).toLocaleString() });
    return [
      {
        label: t("kpi.trips"),
        value: Math.round(total - (modal.Teletrabajo ?? 0)).toLocaleString(),
      },
      {
        label: t("kpi.auto_pct"),
        value: pct("Auto"),
        color: "var(--auto)",
        delta: count("Auto"),
      },
      {
        label: t("kpi.metro_pct"),
        value: pct("Metro"),
        color: "var(--metro)",
        delta: count("Metro"),
      },
      {
        label: t("kpi.bici_pct"),
        value: pct("Bici"),
        color: "var(--bici)",
        delta: count("Bici"),
      },
      {
        label: t("kpi.walk_pct"),
        value: pct("Caminata"),
        color: "var(--walk)",
        delta: count("Caminata"),
      },
      {
        label: t("kpi.tele_pct"),
        value: pct("Teletrabajo"),
        color: "var(--tele)",
        delta: t("kpi.tele_subline", {
          n: Math.round(modal.Teletrabajo ?? 0).toLocaleString(),
        }),
      },
      {
        label: t("kpi.frequency"),
        value: lastIter.frecuencia_metro.toFixed(1),
        unit: "tph",
        // Si la teórica (carga/K) difiere de la operativa, un tope está
        // mordiendo: sin ese dato el usuario no distingue «subí el tope y no
        // pasó nada» de «el tope no estaba activo» (AT-08).
        delta:
          Math.abs(
            lastIter.frecuencia_teorica_metro - lastIter.frecuencia_metro,
          ) > 0.05
            ? t("kpi.frequency_capped", {
                teo: lastIter.frecuencia_teorica_metro.toFixed(1),
              })
            : undefined,
      },
      {
        label: t("kpi.residual"),
        value:
          lastIter.residuo == null || !isFinite(lastIter.residuo)
            ? "—"
            : lastIter.residuo.toFixed(3),
        unit: "min",
      },
      {
        label: t("kpi.co2"),
        value:
          result.emisiones_total_kg >= 100
            ? Math.round(result.emisiones_total_kg).toLocaleString()
            : result.emisiones_total_kg.toFixed(1),
        unit: "kg/h",
        color: "var(--ink)",
        delta: t("kpi.co2_split", {
          auto: Math.round(result.emisiones_auto_kg).toLocaleString(),
          metro: Math.round(result.emisiones_metro_kg).toLocaleString(),
        }),
      },
    ];
  }, [result, lastIter, t]);

  const kpiCaption = useMemo(() => {
    if (!result || !lastIter) return null;
    const totalIters = result.iteraciones.length;
    const base = t("kpi.last_iteration", {
      n: lastIter.iter + 1,
      total: totalIters,
    });
    const status = result.converged ? t("kpi.converged") : t("kpi.maxiter");
    return `${base} · ${status}`;
  }, [result, lastIter, t]);

  // Grupos de agentes para las figuras de reparto por estrato y tenencia.
  const STRATUM_KEY = ["alto", "medio", "bajo"] as const;
  const stratumGroups = useMemo<AgentGroup[]>(() => {
    const agents = result?.agentes;
    if (!agents) return [];
    return [1, 2, 3].map((s) => ({
      label: t(`sandbox.stratum_${STRATUM_KEY[s - 1]}`),
      agents: agents.filter((a) => a.estrato === s),
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, t]);

  // Estadísticas agregadas: el tiempo de viaje no está por agente, así que se
  // reconstruye combinando el snapshot final (tiempos por celda y modo) con la
  // celda/modo de cada agente. Teletrabajo se excluye (no viaja).
  const avgStats = useMemo(() => {
    const agents = result?.agentes;
    if (!agents || !lastIter) return null;
    const MODE_C: Record<string, string> = {
      Auto: "var(--auto)",
      Metro: "var(--metro)",
      Bici: "var(--bici)",
      Caminata: "var(--walk)",
    };
    const STR_C: Record<number, string> = {
      1: "var(--s1)",
      2: "var(--s2)",
      3: "var(--s3)",
    };
    const timeOf = (a: (typeof agents)[number]): number | null => {
      const c = a.celda_origen;
      switch (a.modo_elegido) {
        case "Auto":
          return lastIter.t_auto[c] ?? 0;
        case "Bici":
          return lastIter.t_bici[c] ?? 0;
        case "Metro":
          return (
            (lastIter.t_tren_acceso[c] ?? 0) +
            (lastIter.t_tren_espera[c] ?? 0) +
            (lastIter.t_tren_viaje[c] ?? 0)
          );
        case "Caminata":
          return ((Math.abs(cbdIdx - c) * cellKm) / vCaminata) * 60;
        default:
          return null; // Teletrabajo / sin modo
      }
    };
    const modeAgg: Record<string, [number, number]> = {
      Auto: [0, 0],
      Metro: [0, 0],
      Bici: [0, 0],
      Caminata: [0, 0],
    };
    const strTime: Record<number, [number, number]> = {
      1: [0, 0],
      2: [0, 0],
      3: [0, 0],
    };
    const strUtil: Record<number, [number, number]> = {
      1: [0, 0],
      2: [0, 0],
      3: [0, 0],
    };
    for (const a of agents) {
      const tt = timeOf(a);
      if (tt != null) {
        const e = a.modo_elegido ? modeAgg[a.modo_elegido] : undefined;
        if (e) {
          e[0] += tt;
          e[1] += 1;
        }
        const st = strTime[a.estrato];
        if (st) {
          st[0] += tt;
          st[1] += 1;
        }
      }
      if (a.modo_elegido && a.modo_elegido !== "Teletrabajo") {
        const su = strUtil[a.estrato];
        if (su) {
          su[0] += a.utilidad_elegida;
          su[1] += 1;
        }
      }
    }
    const mean = (p: [number, number]) => (p[1] > 0 ? p[0] / p[1] : 0);
    const strLabel = (s: number) => t(`sandbox.stratum_${STRATUM_KEY[s - 1]}`);
    const timeByMode: StatBar[] = (
      ["Auto", "Metro", "Bici", "Caminata"] as const
    ).map((m) => ({
      label: t(`modes.${m.toLowerCase()}`),
      value: mean(modeAgg[m]!),
      color: MODE_C[m]!,
    }));
    const timeByStratum: StatBar[] = [1, 2, 3].map((s) => ({
      label: strLabel(s),
      value: mean(strTime[s]!),
      color: STR_C[s]!,
    }));
    const utilByStratum: StatBar[] = [1, 2, 3].map((s) => ({
      label: strLabel(s),
      value: mean(strUtil[s]!),
      color: STR_C[s]!,
    }));
    return { timeByMode, timeByStratum, utilByStratum };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, lastIter, t]);

  // Teletrabajo por celda de origen (determinista: no viaja, no está en las
  // demandas de modo). Alimenta la Fig. 9 junto con el flujo esperado por celda.
  const teleByCell = useMemo(() => {
    const arr = new Array<number>(cfgRes.city.n_celdas).fill(0);
    for (const a of result?.agentes ?? []) {
      if (a.modo_elegido === "Teletrabajo") {
        arr[a.celda_origen] = (arr[a.celda_origen] ?? 0) + 1;
      }
    }
    return arr;
  }, [result, cfgRes.city.n_celdas]);

  // Reparto modal espacial POR ESTRATO: la demanda esperada por estrato·modo·celda
  // (del core) + teletrabajo por estrato·celda (de los agentes, determinista).
  // Alimenta los 3 minigráficos (alto/medio/bajo).
  const modeShareByStratum = useMemo(() => {
    const de = result?.demanda_estrato;
    if (!de || de.length < 3) return null;
    const n = cfgRes.city.n_celdas;
    const tele: number[][] = [
      new Array<number>(n).fill(0),
      new Array<number>(n).fill(0),
      new Array<number>(n).fill(0),
    ];
    for (const a of result?.agentes ?? []) {
      if (a.modo_elegido === "Teletrabajo") {
        const e = a.estrato - 1;
        if (e >= 0 && e < 3) {
          tele[e]![a.celda_origen] = (tele[e]![a.celda_origen] ?? 0) + 1;
        }
      }
    }
    // de[estrato][modo][celda], modos en orden Auto·Metro·Bici·Caminata.
    return [1, 2, 3].map((s, idx) => ({
      key: `s${s}`,
      label: t(`sandbox.stratum_${STRATUM_KEY[idx]}`),
      color: `var(--s${s})`,
      demandByCell: {
        Auto: de[idx]![0]!,
        Metro: de[idx]![1]!,
        Bici: de[idx]![2]!,
        Caminata: de[idx]![3]!,
      },
      teleByCell: tele[idx]!,
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, cfgRes.city.n_celdas, t]);

  // Consolidado de métricas para la tabla final (sistema · reparto · estrato ·
  // modo). Reutiliza lo ya agregado (modal_split, avgStats, operatingRatios).
  const transportMetrics = useMemo<TransportMetricsData | null>(() => {
    if (!result || !lastIter || !avgStats) return null;
    const modal = lastIter.modal_split;
    const totalAll =
      (Object.values(modal) as number[]).reduce((s, n) => s + n, 0) || 1;
    const MODE_ORDER: Modo[] = [
      "Auto",
      "Metro",
      "Bici",
      "Caminata",
      "Teletrabajo",
    ];
    const MODE_COLOR: Record<string, string> = {
      Auto: "var(--auto)",
      Metro: "var(--metro)",
      Bici: "var(--bici)",
      Caminata: "var(--walk)",
      Teletrabajo: "var(--tele)",
    };
    const reparto = MODE_ORDER.map((m) => ({
      modo: m,
      label: t(`modes.${m.toLowerCase()}`),
      count: modal[m] ?? 0,
      pct: ((modal[m] ?? 0) / totalAll) * 100,
      color: MODE_COLOR[m]!,
    }));
    // avgStats.timeByMode está en orden Auto · Metro · Bici · Caminata.
    const MODE4: Modo[] = ["Auto", "Metro", "Bici", "Caminata"];
    const tiempoPorModo = avgStats.timeByMode.map((b, i) => ({
      modo: MODE4[i]!,
      label: b.label,
      min: b.value,
      color: b.color,
    }));
    // Tiempo medio del sistema = promedio por modo ponderado por su conteo
    // (cada agente cuenta una vez bajo su modo; teletrabajo no viaja).
    let twSum = 0;
    let wSum = 0;
    for (const tm of tiempoPorModo) {
      const c = modal[tm.modo as Modo] ?? 0;
      twSum += tm.min * c;
      wSum += c;
    }
    const agents = result.agentes;
    const porEstrato = [1, 2, 3].map((sNum, idx) => {
      const stratAgents = agents.filter((a) => a.estrato === sNum);
      const totalS = stratAgents.length || 1;
      const repartoS = MODE_ORDER.map((m) => ({
        modo: m,
        pct:
          (stratAgents.filter((a) => a.modo_elegido === m).length / totalS) *
          100,
      }));
      return {
        key: `s${sNum}`,
        label: t(`sandbox.stratum_${STRATUM_KEY[idx]}`),
        color: `var(--s${sNum})`,
        nHogares: stratAgents.length,
        tiempoMin: avgStats.timeByStratum[idx]?.value ?? 0,
        utilidad: avgStats.utilByStratum[idx]?.value ?? 0,
        reparto: repartoS,
      };
    });
    return {
      viajesFisicos: Math.round(totalAll - (modal.Teletrabajo ?? 0)),
      reparto,
      tiempoSistemaMin: wSum > 0 ? twSum / wSum : 0,
      frecuenciaMetro: lastIter.frecuencia_metro,
      residuoMin:
        lastIter.residuo == null || !isFinite(lastIter.residuo)
          ? null
          : lastIter.residuo,
      co2Total: result.emisiones_total_kg,
      co2Auto: result.emisiones_auto_kg,
      co2Metro: result.emisiones_metro_kg,
      iteraciones: lastIter.iter + 1,
      totalIteraciones: result.iteraciones.length,
      converged: result.converged,
      capacidadAuto: result.capacidad_auto,
      vcAuto: operatingRatios.car,
      vcBici: operatingRatios.bike,
      vcMetro: operatingRatios.metro,
      tiempoPorModo,
      porEstrato,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, lastIter, avgStats, t]);

  return (
    <div className="page">
      <aside className="sidebar">
        {/* F-01: escenarios con nombre (ciudad × política) como punto de
            partida, en vez de mover sliders a ciegas desde los defaults. */}
        <PresetGallery variant="policy" />
        {/* La ciudad (largo, celdas, pendiente, teletrabajo, densidad y estratos)
            se define en Uso de Suelo y alimenta esta simulación. */}
        <SidebarSection
          title={t("sections.city")}
          meta={t("city_params.meta", {
            km: config.city.largo_ciudad_km,
            n: config.city.n_celdas,
          })}
        >
          <p className="text-[11px] leading-snug text-muted">
            {t("city_params.defined_in_land_use")}
          </p>
        </SidebarSection>
        <SupplyBuilder
          config={config}
          onChange={setConfig}
          operatingRatios={operatingRatios}
          metroFreq={
            lastIter
              ? {
                  operativa: lastIter.frecuencia_metro,
                  teorica: lastIter.frecuencia_teorica_metro,
                }
              : undefined
          }
        />
        <EconomyBuilder config={config} onChange={setConfig} />
        {/* Después de las palancas y antes del solver: los betas no son
            política, pero son lo que traduce cualquier política en reparto
            modal. Hasta ahora no eran visibles en ninguna parte. */}
        <CalibrationPanel config={config} onChange={setConfig} />

        <SidebarSection
          title={t("sections.equilibrium")}
          meta={`${config.max_iter} iter`}
          defaultOpen={false}
        >
          <label className="slider-row block">
            <div className="srow-top">
              <span className="srow-label">{t("equilibrium.max_iter")}</span>
              <span className="srow-val" aria-hidden>
                {config.max_iter}
              </span>
            </div>
            <input
              type="range"
              min={3}
              max={50}
              step={1}
              value={config.max_iter}
              onChange={(e) =>
                setConfig((c) => ({ ...c, max_iter: Number(e.target.value) }))
              }
              aria-label={t("equilibrium.max_iter")}
            />
          </label>

          <label className="slider-row block">
            <div className="srow-top">
              <span className="srow-label">{t("equilibrium.tolerance")}</span>
              <span className="srow-val" aria-hidden>
                {config.tolerance > 0
                  ? `${config.tolerance.toFixed(2)} min`
                  : t("equilibrium.tol_off")}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={config.tolerance}
              onChange={(e) =>
                setConfig((c) => ({ ...c, tolerance: Number(e.target.value) }))
              }
              aria-label={t("equilibrium.tolerance")}
            />
          </label>

          <div className="mt-2">
            <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
              {t("equilibrium.assignment")}
            </div>
            <div className="seg" style={{ width: "100%" }}>
              {(["montecarlo", "expected", "wardrop"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={config.assignment === m ? "active" : ""}
                  onClick={() => setConfig((c) => ({ ...c, assignment: m }))}
                  style={{ flex: 1 }}
                >
                  {t(`equilibrium.assignment_${m}`)}
                </button>
              ))}
            </div>
            <p className="mt-1 text-[11px] text-muted">
              {t(`equilibrium.assignment_hint_${config.assignment}`)}
            </p>
          </div>

          <div className="mt-3">
            <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
              {t("equilibrium.modos")}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(["Auto", "Metro", "Bici", "Caminata"] as const).map((m) => {
                const on = config.modos_habilitados.includes(m);
                const last = on && config.modos_habilitados.length === 1;
                return (
                  <button
                    key={m}
                    type="button"
                    disabled={last}
                    className={`chip-toggle${on ? " active" : ""}`}
                    onClick={() =>
                      setConfig((c) => ({
                        ...c,
                        modos_habilitados: on
                          ? c.modos_habilitados.filter((x) => x !== m)
                          : [...c.modos_habilitados, m],
                      }))
                    }
                    title={last ? t("equilibrium.modos_min") : undefined}
                  >
                    {t(`equilibrium.modo_${m.toLowerCase()}`)}
                  </button>
                );
              })}
            </div>
            <p className="mt-1 text-[11px] text-muted">
              {t("equilibrium.modos_hint")}
            </p>
          </div>
        </SidebarSection>

        {(stage === "done" || stage === "error") && (
          <button
            type="button"
            className="reset-btn"
            onClick={reset}
            title={tCommon("actions.new_run")}
          >
            {`↺ ${tCommon("actions.new_run")}`}
          </button>
        )}

        <button
          type="button"
          className="run-btn"
          disabled={running}
          onClick={handleRun}
        >
          {running
            ? `◜ ${t("equilibrium.iteration", {
                n: progress?.current ?? 0,
                total: progress?.total ?? 0,
              })}`
            : `▶ ${tCommon("actions.run")}`}
        </button>

        {running && (
          <button type="button" className="reset-btn" onClick={handleCancel}>
            {`✕ ${tCommon("actions.cancel")}`}
          </button>
        )}

        {error && (
          <div
            className="callout"
            style={{ borderLeftColor: "var(--metro)", marginTop: 12 }}
          >
            {error}
          </div>
        )}
      </aside>

      <section className="main">
        {stale && (
          <div className="stale-banner" role="status">
            <span>{t("stale.banner")}</span>
            <button type="button" onClick={() => void handleRun()}>
              {`▶ ${t("stale.rerun")}`}
            </button>
          </div>
        )}

        {/* HERO */}
        <div className="hero">
          <div className="hero-head">
            <h1 className="hero-title">{t("hero.title")}</h1>
            <div className="hero-sub">
              <span className="dot">●</span>{" "}
              {stage === "running" || stage === "booting"
                ? t("hero.status_running")
                : stage === "done"
                  ? t("hero.status_done")
                  : t("hero.status_ready")}
            </div>
          </div>

          <div className="ribbon-wrap">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
                {showLandUseCity
                  ? t("sandbox.land_use_city_heading")
                  : showInfraPlano
                    ? t("preview.heading")
                    : t("sandbox.city_heading")}
              </span>
              {hasData ? (
                <div className="seg">
                  {VIEW_OPTIONS.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setHeatMode(m)}
                      className={heatMode === m ? "active" : ""}
                    >
                      {viewLabel(m)}
                    </button>
                  ))}
                </div>
              ) : (
                <span className="font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
                  {t("preview.meta")}
                </span>
              )}
            </div>

            {showLandUseCity ? (
              <>
                <ExportableFigure
                  name="ciudad-uso-suelo"
                  title={t("sandbox.land_use_city_heading")}
                  description={t("sandbox.land_use_city_desc", {
                    length: config.city.largo_ciudad_km,
                    cells: config.city.n_celdas,
                  })}
                  exportSize={{ width: 1200, height: 320 }}
                >
                  {landUseCity.comp ? (
                    <StratumDistribution
                      composition={landUseCity.comp}
                      height={230}
                    />
                  ) : (
                    <CityPreview config={config} />
                  )}
                </ExportableFigure>
                <p className="kpi-caption" style={{ marginTop: 6 }}>
                  {landUseCity.comp
                    ? landUseCity.isPost
                      ? t("sandbox.land_use_city_caption_post")
                      : t("sandbox.land_use_city_caption_pre")
                    : t("sandbox.land_use_city_caption_none")}
                </p>
              </>
            ) : heatMode === "plano" ? (
              <ExportableFigure
                name="plano-ciudad"
                title={t("preview.heading")}
                description={t("preview.export_desc")}
                exportSize={{ width: 1200, height: 360 }}
              >
                <CityPreview config={config} />
              </ExportableFigure>
            ) : (
              <ExportableFigure
                name={`ciudad-${heatMode}`}
                title={`${t("sandbox.city_heading")} — ${viewLabel(heatMode)}`}
                description={t("sandbox.city_figure_desc", {
                  length: cfgRes.city.largo_ciudad_km,
                  cells: cfgRes.city.n_celdas,
                  mode: viewLabel(heatMode),
                })}
                exportSize={{ width: 1200, height: 200 }}
              >
                <CityStrip
                  nCeldas={cfgRes.city.n_celdas}
                  largoKm={cfgRes.city.largo_ciudad_km}
                  pendientePct={cfgRes.city.pendiente_porcentaje}
                  modeProfile={profile}
                  heatMode={heatMode}
                  cutoffMin={MODE_CUTOFF[heatMode]}
                  cutoffLabel={
                    MODE_CUTOFF[heatMode] != null
                      ? t("sandbox.cutoff_label", {
                          min: MODE_CUTOFF[heatMode],
                        })
                      : undefined
                  }
                  estacionesKm={result?.estaciones_km ?? undefined}
                  shareEstratos={cfgRes.city.share_estratos}
                  iterationToken={lastIter?.iter ?? -1}
                />
              </ExportableFigure>
            )}

            <div className="ribbon-legend">
              {(
                [
                  { m: "auto", c: "var(--auto)" },
                  { m: "metro", c: "var(--metro)" },
                  { m: "bici", c: "var(--bici)" },
                  { m: "caminata", c: "var(--walk)" },
                ] as const
              ).map(({ m, c }) => (
                <span
                  key={m}
                  className="sw"
                  style={
                    {
                      "--c": c,
                      opacity:
                        heatMode === "todos" ||
                        heatMode === m ||
                        (heatMode === "espera" && m === "metro")
                          ? 1
                          : 0.4,
                    } as React.CSSProperties
                  }
                >
                  {t(`modes.${m}`)}
                </span>
              ))}
              <span style={{ marginLeft: "auto", textTransform: "none" }}>
                {t("hero.stats_line", {
                  total: totalAgents > 0 ? totalAgents.toLocaleString() : "—",
                  length: cfgRes.city.largo_ciudad_km,
                  stations: cfgRes.supply.train.num_estaciones,
                  lanes: cfgRes.supply.car.num_pistas,
                })}
              </span>
            </div>
          </div>
        </div>

        {/* KPIs */}
        {kpiCaption && <div className="kpi-caption">{kpiCaption}</div>}
        <KPIStrip items={kpis} />

        {/* Hint row — guía pedagógica (solo antes de la primera corrida: tras
            simular, los resultados mandan y los hints serían ruido) */}
        {!hasData && (
          <div className="hint-row">
            <div className="hint">
              <strong>{t("hints.demand_title")}</strong>
              {t("hints.demand_body")}
            </div>
            <div className="hint">
              <strong>{t("hints.supply_title")}</strong>
              {t("hints.supply_body")}
            </div>
            <div className="hint">
              <strong>{t("hints.equilibrium_title")}</strong>
              {t("hints.equilibrium_body")}
            </div>
          </div>
        )}

        {/* Estado de corrida (mantiene animaciones) */}
        {(stage === "booting" || stage === "running") && progress && (
          <div style={{ marginBottom: "var(--gap)" }}>
            <RunStatus
              current={progress.current}
              total={progress.total}
              lastIter={lastIter}
              stage={stage}
              engine="local"
            />
          </div>
        )}

        {(stage === "booting" ||
          (stage === "running" && liveIterations.length === 0)) && (
          <div style={{ marginBottom: "var(--gap)" }}>
            <SimulationSkeleton nCeldas={cfgRes.city.n_celdas} />
          </div>
        )}

        {/* Grid de paneles FIG. NN */}
        {liveIterations.length > 0 && (
          <div className="panel-grid">
            {lastIter && result && (
              <Panel
                n="00"
                title={t("network.title")}
                meta={t("panel_meta.modes_all")}
                cls="col-12"
              >
                <NetworkDiagram
                  snapshot={lastIter}
                  result={result}
                  config={config}
                />
              </Panel>
            )}

            <Panel
              n="01"
              title={t("equilibrium.converged")}
              meta="MSA"
              cls="col-12"
            >
              <ConvergenceTrace iterations={liveIterations} />
            </Panel>

            {/* La tabla va inmediatamente después de la convergencia: es el
                RESULTADO del equilibrio. Los gráficos que lo desagregan vienen
                después. Antes cerraba la página, así que había que recorrer 13
                figuras para llegar al número.

                SIN `n`: no es una figura, es el resultado. Numerarla corría toda
                la secuencia de figuras en uno (los flujos quedaban en 03-06). */}
            {transportMetrics && (
              <Panel
                title={t("metrics_table.title")}
                meta={t("metrics_table.meta")}
                cls="col-12"
              >
                <TransportMetricsTable data={transportMetrics} />
              </Panel>
            )}

            {/* Agregados de ciudad completa + delta contra la corrida fijada.
                Permite comparar dos escenarios sin salir del módulo. */}
            {result && configUsed && (
              <Panel
                title={t("agg.title")}
                meta={reference ? t("agg.pinned") : t("agg.meta")}
                cls="col-12"
              >
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={pinReference}
                    className="btn"
                    disabled={stale}
                  >
                    {t("agg.pin")}
                  </button>
                  {reference && (
                    <button
                      type="button"
                      onClick={clearReference}
                      className="btn"
                    >
                      {t("agg.unpin")}
                    </button>
                  )}
                </div>
                <ReferenceComparison
                  config={configUsed}
                  result={result}
                  reference={reference}
                />
              </Panel>
            )}

            {/* UN panel de flujos con selector de modo, en vez de cuatro paneles
                que repetían la misma forma. El profesor reportó que tanto
                gráfico marea; cuatro figuras para una sola lectura es
                justamente el caso. La escala Y sigue siendo la global para que
                cambiar de modo no engañe con auto-scale. */}
            {lastIter && result && flowData && (
              <Panel
                n="02"
                title={t("sandbox.flow_per_cell", {
                  mode: t(`modes.${flowMode}`),
                })}
                meta={
                  <div className="flex flex-wrap gap-1">
                    {FLOW_MODES.map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setFlowMode(m)}
                        className="tab"
                        aria-pressed={flowMode === m}
                        style={{
                          color: flowMode === m ? "var(--paper)" : undefined,
                          background: flowMode === m ? "var(--ink)" : undefined,
                        }}
                      >
                        {t(`modes.${m}`)}
                      </button>
                    ))}
                  </div>
                }
                cls="col-12"
              >
                <ExportableFigure
                  name={`flujo-${flowMode}`}
                  title={t("sandbox.flow_per_cell", {
                    mode: t(`modes.${flowMode}`),
                  })}
                  exportSize={{ width: 1000, height: 200 }}
                >
                  <FlowProfile
                    flows={flowData.flows}
                    largoKm={cfgRes.city.largo_ciudad_km}
                    color={flowData.color}
                    yMax={flowData.globalMax}
                    capacityHint={flowData.cap}
                  />
                </ExportableFigure>
              </Panel>
            )}

            {result && result.emisiones_perfil_kg && (
              <Panel
                n="03"
                title={t("sandbox.co2_profile")}
                meta={t("panel_meta.co2")}
                cls="col-12"
              >
                <ExportableFigure
                  name="co2-por-ubicacion"
                  title={t("sandbox.co2_profile")}
                  exportSize={{ width: 1000, height: 200 }}
                >
                  <FlowProfile
                    flows={result.emisiones_perfil_kg}
                    largoKm={cfgRes.city.largo_ciudad_km}
                    color="var(--co2)"
                    label="kg/h"
                    valueFmt={(v) => v.toFixed(1)}
                    height={130}
                  />
                </ExportableFigure>
              </Panel>
            )}

            {result && result.agentes.length > 0 && (
              <>
                <Panel
                  n="04"
                  title={t("sandbox.trips_by_stratum")}
                  meta={t("panel_meta.share_stratum")}
                  cls="col-6"
                >
                  <ExportableFigure
                    name="reparto-por-estrato"
                    title={t("sandbox.trips_by_stratum")}
                    exportSize={{ width: 700, height: 240 }}
                  >
                    <ModeShareBars groups={stratumGroups} />
                  </ExportableFigure>
                </Panel>

                <Panel
                  n="05"
                  title={t("sandbox.mode_share_by_location")}
                  meta="stacked · 100%"
                  cls="col-5"
                >
                  <ExportableFigure
                    name="reparto-modal-por-ubicacion"
                    title={t("sandbox.mode_share_by_location")}
                    exportSize={{ width: 800, height: 280 }}
                  >
                    {lastIter && (
                      <ModeShareByLocation
                        demandByCell={{
                          Auto: lastIter.demanda_auto,
                          Metro: lastIter.demanda_metro,
                          Bici: lastIter.demanda_bici,
                          Caminata: lastIter.demanda_caminata,
                        }}
                        teleByCell={teleByCell}
                        largoKm={cfgRes.city.largo_ciudad_km}
                      />
                    )}
                  </ExportableFigure>
                </Panel>

                {modeShareByStratum && (
                  <Panel
                    n="06"
                    title={t("sandbox.mode_share_by_location_stratum")}
                    meta={t("sandbox.mode_share_stratum_meta")}
                    cls="col-12"
                  >
                    <div style={{ display: "grid", gap: "var(--gap)" }}>
                      {modeShareByStratum.map((s) => (
                        <div key={s.key}>
                          <div
                            className="mb-1 flex items-center gap-1.5 font-fig text-[10px] uppercase tracking-[0.08em]"
                            style={{ color: "var(--muted)" }}
                          >
                            <span
                              style={{
                                width: 9,
                                height: 9,
                                background: s.color,
                                display: "inline-block",
                              }}
                            />
                            {s.label}
                          </div>
                          <ExportableFigure
                            name={`reparto-ubicacion-${s.key}`}
                            title={`${t("sandbox.mode_share_by_location_stratum")} — ${s.label}`}
                            exportSize={{ width: 800, height: 180 }}
                          >
                            <ModeShareByLocation
                              demandByCell={s.demandByCell}
                              teleByCell={s.teleByCell}
                              largoKm={cfgRes.city.largo_ciudad_km}
                              height={130}
                              normalize={false}
                            />
                          </ExportableFigure>
                        </div>
                      ))}
                    </div>
                  </Panel>
                )}
              </>
            )}
          </div>
        )}

        {/* Inspector de utilidad — descomposición del logit para una celda/
            estrato; lo referencia el tutorial de demanda. Antes de correr usa
            tiempos de flujo libre; después, los de la última iteración. */}
        <div className="panel-grid" style={{ marginTop: "var(--gap)" }}>
          <Panel
            n="07"
            title={t("demand_inspector.title")}
            meta={
              lastIter
                ? t("demand_inspector.hint_with_sim")
                : t("demand_inspector.hint_no_sim")
            }
            cls="col-12"
          >
            <DemandInspector config={cfgRes} lastIter={lastIter} />
          </Panel>
        </div>
      </section>
    </div>
  );
}
