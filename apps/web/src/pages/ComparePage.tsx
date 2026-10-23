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
import { ScenarioDiffTable } from "@/components/compare/ScenarioDiffTable";
import { ScenarioFlowComparison } from "@/components/compare/ScenarioFlowComparison";
import { Panel } from "@/components/ui/Panel";
import { PorQue } from "@/components/ui/PorQue";
import { StratumDistribution } from "@/components/viz/StratumDistribution";

import {
  resolverAcoplado,
  resolverUsoDeSuelo,
  simularTransporte,
} from "@/lib/api";
import {
  agregadosDe,
  bienestarComparable,
  type CorridaBienestar,
  type RazonIncomparable,
} from "@/lib/agregados";
import { defaultLandUseConfig } from "@/lib/defaults";
import { expectedComposition } from "@/lib/citySupply";
import { downloadCsv } from "@/lib/csv";
import { VUELTAS_ACOPLADO_MAX } from "@/lib/gen/constantes.gen";
import { computeKPIs, type ScenarioKPIs } from "@/lib/kpis";
import type { Modo } from "@/lib/types";
import type { LandUseSolveResponse } from "@/lib/types-v2";
import {
  useCompareStore,
  type CompareKind,
  type Scenario,
} from "@/store/compareStore";
import { fmtDecimal, fmtEntero, fmtPct, fmtPesos } from "@/lib/modos";

const KINDS: CompareKind[] = ["transport", "land_use", "coupled"];

/** Métricas comparables del equilibrio de suelo (mismas que LandUsePage). */
function landUseValues(r: LandUseSolveResponse): Record<string, number> {
  // Distancias esperadas (S·Q) y Theil poblacional vienen del núcleo (D-38/D-44).
  return {
    theil: r.theil,
    dist_alto: r.dist_media_km[0] ?? 0,
    dist_medio: r.dist_media_km[1] ?? 0,
    dist_bajo: r.dist_media_km[2] ?? 0,
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
    bienestar: sis.delta_bienestar_total_mes_clp,
    emisiones: sis.emisiones_total_kg,
    iteraciones: cr.iterations,
  };
}

/** Niveles de bienestar de una corrida y lo que decide si se restan. */
interface NivelesBienestar {
  corrida: CorridaBienestar;
  niveles: Record<string, number>;
}

/** Δ de bienestar de cada escenario contra la base, por nivel. */
type DeltasBienestar = Map<
  string,
  { d: Record<string, number | null>; razon: RazonIncomparable | null }
>;

/** Lente Transporte: los agregados de hora punta del núcleo (`bienestar.py`).
 *  El excedente es el de la medida emparejada con el método de asignación. */
function nivelesTransporte(s: Scenario): NivelesBienestar | null {
  const agg = s.result ? agregadosDe(s.result) : null;
  if (!agg || !s.config) return null;
  const max = agg.medida_bienestar === "utilidad_maxima";
  return {
    corrida: {
      config: s.config,
      landUse: s.landUse ?? null,
      medida: agg.medida_bienestar,
    },
    niveles: {
      excedente: max ? agg.excedente_max_total_clp : agg.excedente_total_clp,
      bienestar: agg.bienestar_social_clp,
      excedente_social: agg.excedente_social_total_clp,
    },
  };
}

/** Lente Ciudad en equilibrio: el NIVEL del excedente mensual, no el Δ contra
 *  la red vacía. Ese Δ compara cada escenario consigo mismo, y como la red
 *  vacía fija sólo los tiempos, un peaje entra igual en los dos logsum y casi
 *  se cancela: restarlo entre escenarios no ve los precios. */
function nivelesAcoplado(s: Scenario): NivelesBienestar | null {
  const sis = s.coupledResult?.last.sistema;
  // Un wheel anterior a 9eeef4c no trae el nivel.
  if (!sis || !s.config || !Number.isFinite(sis.excedente_total_mes_clp))
    return null;
  return {
    corrida: {
      config: s.config,
      landUse: s.landUse ?? null,
      medida: sis.medida_bienestar,
    },
    niveles: { excedente: sis.excedente_total_mes_clp },
  };
}

/**
 * Δ de bienestar contra la base. El nivel del excedente no se lee —su cero lo
 * fijan las ASC—; la resta sí, pero sólo entre corridas que comparten ese cero
 * (`bienestarComparable`). La base no entra; una incomparable entra con la
 * razón y sin Δ.
 */
function deltasBienestar(
  scenarios: Scenario[],
  baseId: string | undefined,
  nivelesDe: (s: Scenario) => NivelesBienestar | null,
): DeltasBienestar {
  const out: DeltasBienestar = new Map();
  const base = scenarios.find((s) => s.id === baseId);
  const nb = base ? nivelesDe(base) : null;
  if (!nb) return out;
  for (const s of scenarios) {
    const n = s.id === baseId ? null : nivelesDe(s);
    if (!n) continue;
    const razon = bienestarComparable(n.corrida, nb.corrida);
    const d = Object.fromEntries(
      Object.entries(nb.niveles).map(([k, vb]) => {
        const v = n.niveles[k];
        return [k, razon || v == null ? null : v - vb];
      }),
    );
    out.set(s.id, { d, razon });
  }
  return out;
}

/** Agrega los Δ a las columnas como `d_<nivel>`, para filas `soloDelta`. */
function conDeltas(
  cols: MetricCol[],
  deltas: DeltasBienestar,
  noComparable: string,
): MetricCol[] {
  return cols.map((c) => {
    const x = deltas.get(c.id);
    if (!c.values || !x) return c;
    const claves = Object.keys(x.d);
    return {
      ...c,
      values: {
        ...c.values,
        ...Object.fromEntries(claves.map((k) => [`d_${k}`, x.d[k] ?? null])),
      },
      texto: x.razon
        ? Object.fromEntries(claves.map((k) => [`d_${k}`, noComparable]))
        : undefined,
    };
  });
}

/** Por qué cada escenario incomparable no tiene Δ de bienestar. */
function AvisosBienestar({
  deltas,
  cols,
}: {
  deltas: DeltasBienestar;
  cols: MetricCol[];
}) {
  const { t } = useTranslation("simulator");
  return (
    <>
      {cols.map((c) => {
        const r = deltas.get(c.id)?.razon;
        return r ? (
          <p
            key={c.id}
            className="kpi-caption"
            style={{ marginTop: 4, color: "var(--alerta)" }}
          >
            {t("compare.bien.incomparable", {
              nombre: c.name,
              razon: t(`agg.razon.${r}`),
            })}
          </p>
        ) : null;
      })}
    </>
  );
}

/** Localización de la tarjeta en la lente Transporte (C-02): el snapshot
 *  capturado por «Usar Transporte actual» o, si vino de archivo,
 *  «equilibrio» sólo si la tarjeta ya corrió la lente de suelo. */
function localizacionDe(sc: Scenario): "equilibrio" | "original" {
  return (
    sc.localizacion ??
    (sc.luResult != null &&
    sc.luResult.L === sc.config?.city.n_celdas &&
    (sc.luResult.result?.Q?.length ?? 0) > 0
      ? "equilibrio"
      : "original")
  );
}

/** ¿Misma ciudad que la base? Misma geometría y misma oferta de suelo: sólo
 *  entonces congelar la `Q` de la base es «la misma gente en el mismo lugar»
 *  (D11c). Sobre otra oferta `S` la misma `Q` sería otra población. */
function mismaCiudad(a: Scenario, b: Scenario): boolean {
  const clave = (s: Scenario) => {
    const lu = s.landUse ?? defaultLandUseConfig;
    return JSON.stringify([
      s.config?.city.n_celdas,
      s.config?.city.largo_ciudad_km,
      lu.H_por_estrato,
      lu.forma,
      lu.oferta_sigma_frac,
      lu.forma_param,
    ]);
  };
  return clave(a) === clave(b);
}

/** La base de INPUTS: la elegida si tiene config; si no, la primera con config. */
function baseDeInputs(
  scenarios: Scenario[],
  baseIdSel: string | null,
): string | undefined {
  return (
    (baseIdSel && scenarios.some((s) => s.id === baseIdSel && s.config)
      ? baseIdSel
      : undefined) ?? scenarios.find((s) => s.config)?.id
  );
}

/** Resuelve cuando la tarjeta deja de correr. */
function terminaDeCorrer(id: string): Promise<void> {
  const listo = () =>
    useCompareStore.getState().scenarios.find((s) => s.id === id)?.status !==
    "running";
  return new Promise((resolve) => {
    if (listo()) return resolve();
    const unsub = useCompareStore.subscribe(() => {
      if (!listo()) return;
      unsub();
      resolve();
    });
  });
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
  const baseIdSel = useCompareStore((s) => s.baseId);
  const setBaseId = useCompareStore((s) => s.setBaseId);
  const [mode, setMode] = useState<Modo>("Auto");

  const untitled = (id: string) => t("compare.scenario_card.untitled", { id });

  const runOne = async (id: string) => {
    const st = useCompareStore.getState();
    const sc = st.scenarios.find((s) => s.id === id);
    if (!sc?.config || sc.status === "running") return;
    const k = st.kind;
    setStatus(id, "running");
    try {
      if (k === "transport") {
        // C-02: misma población y localización que el Sandbox. D11c: una
        // tarjeta de la misma ciudad que la base corre con la `Q` de la
        // corrida de la base —la misma gente en el mismo lugar, estática
        // comparativa de corto plazo—; una de otra ciudad, con la suya.
        const baseId = baseDeInputs(st.scenarios, st.baseId) ?? id;
        const base = st.scenarios.find((s) => s.id === baseId);
        let loc = localizacionDe(sc);
        let Q_dada: number[][] | null = null;
        let congelada = false;
        if (base && baseId !== id && mismaCiudad(sc, base)) {
          // La base corre primero: su corrida fija dónde vive la gente. Un
          // resultado suyo de cuando no era la base no sirve.
          await terminaDeCorrer(baseId);
          const vigente = (s?: Scenario) =>
            s?.result != null && s.transportBase?.id === s.id;
          const buscar = () =>
            useCompareStore.getState().scenarios.find((s) => s.id === baseId);
          if (!vigente(buscar())) await runOne(baseId);
          const b = buscar();
          if (!vigente(b) || !b?.result || !b.transportBase) {
            setError(id, t("compare.base_sin_resultado"));
            return;
          }
          loc = b.transportBase.localizacion;
          // Con «original» la `Q` es la mezcla uniforme: no se reenvía.
          Q_dada = loc === "equilibrio" ? b.result.localizacion_Q : null;
          congelada = true;
        }
        // Sin callback de iteración: acá interesa el resultado final, no la
        // convergencia en vivo. Qué motor corre lo decide `lib/api`.
        const result = await simularTransporte(
          sc.config,
          sc.landUse ?? defaultLandUseConfig,
          loc,
          () => {},
          undefined,
          Q_dada,
        );
        setTransportResult(id, result, {
          id: baseId,
          congelada,
          localizacion: loc,
        });
      } else if (k === "land_use") {
        const L = sc.config.city.n_celdas;
        const r = await resolverUsoDeSuelo({
          L,
          CBD: Math.floor(L / 2),
          largo_km: sc.config.city.largo_ciudad_km,
          land_use: sc.landUse ?? defaultLandUseConfig,
          demand: sc.config.demand,
          supply: sc.config.supply,
          modos_habilitados: sc.config.modos_habilitados,
          pendiente_porcentaje: sc.config.city.pendiente_porcentaje,
        });
        setLuResult(id, r);
      } else {
        // La población es ΣH del suelo de la tarjeta, como en las otras dos
        // lentes (D10d).
        const res = await resolverAcoplado({
          sim: sc.config,
          land_use: sc.landUse ?? defaultLandUseConfig,
          outer_max_iter: VUELTAS_ACOPLADO_MAX,
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
        // El MSA que agota `max_iter` no es un equilibrio: se marca como en la
        // lente Ciudad en equilibrio, para no comparar contra él a ciegas.
        name:
          (s.name || untitled(s.id)) +
          (s.result && !s.result.converged
            ? ` ${t("compare.not_converged")}`
            : ""),
        kpis:
          s.result && s.config
            ? computeKPIs(
                s.result,
                s.config.city.largo_ciudad_km,
                s.config.city.n_celdas,
                s.config.demand.globales.v_caminata,
                s.config.supply.bike.capacidad_pista,
                s.config.supply.train.capacidad_tren,
                s.config.supply.train.frec_max,
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
        values: s.luResult && s.config ? landUseValues(s.luResult) : null,
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scenarios, t],
  );

  const luRows = useMemo<MetricRow[]>(
    () => [
      {
        key: "theil",
        label: t("compare.lu.theil"),
        fmt: (v) => fmtDecimal(v, 3),
        betterWhen: "down",
      },
      {
        key: "dist_alto",
        label: t("compare.lu.dist_alto"),
        fmt: (v) => `${fmtDecimal(v, 2)} km`,
      },
      {
        key: "dist_medio",
        label: t("compare.lu.dist_medio"),
        fmt: (v) => `${fmtDecimal(v, 2)} km`,
      },
      {
        key: "dist_bajo",
        label: t("compare.lu.dist_bajo"),
        fmt: (v) => `${fmtDecimal(v, 2)} km`,
      },
    ],
    [t],
  );

  // ---- Ciudad en equilibrio ----
  // Sin los Δ de bienestar, que dependen de la base (más abajo).
  const cpColsSinDelta = useMemo<MetricCol[]>(
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

  const cpRows = useMemo<MetricRow[]>(
    () => [
      {
        key: "theil",
        label: t("compare.cp.theil"),
        fmt: (v) => fmtDecimal(v, 3),
        betterWhen: "down",
      },
      {
        key: "t_medio",
        label: t("compare.cp.t_medio"),
        fmt: (v) => `${fmtDecimal(v)} min`,
        betterWhen: "down",
      },
      {
        key: "auto",
        label: t("compare.cp.auto"),
        fmt: (v) => fmtPct(v),
      },
      {
        key: "carga_bajo",
        label: t("compare.cp.carga_bajo"),
        fmt: (v) => fmtPct(v),
        betterWhen: "down",
      },
      {
        key: "ratio_carga",
        label: t("compare.cp.ratio_carga"),
        fmt: (v) => `${fmtDecimal(v, 2)}×`,
        betterWhen: "down",
      },
      {
        key: "d_excedente",
        label: t("compare.cp.excedente_vs_base"),
        fmt: (v) => fmtPesos(v),
        betterWhen: "up",
        soloDelta: true,
      },
      {
        key: "bienestar",
        label: t("compare.cp.bienestar"),
        fmt: (v) => fmtPesos(v),
        // Restarlo entre escenarios es justo lo que no se puede: la red vacía
        // fija sólo los tiempos, y un peaje casi se cancela en él.
        sinDelta: true,
      },
      {
        key: "emisiones",
        label: t("compare.cp.emisiones"),
        fmt: (v) => `${fmtEntero(v)} kg/h`,
        betterWhen: "down",
      },
      {
        key: "iteraciones",
        label: t("compare.cp.iteraciones"),
        fmt: (v) => `${Math.round(v)}`,
      },
    ],
    [t],
  );

  // D11c: de dónde salió la población de cada resultado de transporte.
  const notaTransporte = (s: Scenario): string | undefined => {
    const tb = s.transportBase;
    if (!s.result || !tb) return undefined;
    if (tb.id !== baseInputsId) return t("compare.q.desactualizada");
    if (s.id === baseInputsId) return undefined;
    if (tb.congelada) return t("compare.q.congelada");
    return tb.localizacion === "equilibrio"
      ? t("compare.q.otra_ciudad_reloc")
      : t("compare.q.otra_ciudad");
  };

  const doneCount = scenarios.filter((s) => s.status === "done").length;
  const runningCount = scenarios.filter((s) => s.status === "running").length;
  const configuredCount = scenarios.filter((s) => s.config != null).length;
  // Base ELEGIBLE (C-01). Se distinguen dos: la de INPUTS —que existe apenas
  // hay una tarjeta configurada, para el diff y para marcar la tarjeta— y la de
  // RESULTADOS, que necesita una corrida. Sin separarlas, antes de correr no
  // había ninguna marcada y las dos tarjetas se veían igual.
  const baseInputsId = baseDeInputs(scenarios, baseIdSel);
  const baseId =
    (baseIdSel &&
    scenarios.some((s) => s.id === baseIdSel && s.status === "done")
      ? baseIdSel
      : undefined) ?? scenarios.find((s) => s.status === "done")?.id;

  // Bienestar: sólo el Δ contra la base de RESULTADOS, y sólo si se puede
  // restar. Sin memo: son tres restas por escenario.
  const noComparable = t("agg.no_comparable");
  const dCp = deltasBienestar(scenarios, baseId, nivelesAcoplado);
  const cpCols = conDeltas(cpColsSinDelta, dCp, noComparable);
  const dTr = deltasBienestar(scenarios, baseId, nivelesTransporte);
  const trCols = conDeltas(
    rows.map((r) => {
      const s = scenarios.find((x) => x.id === r.id);
      return {
        id: r.id,
        name: r.name,
        values: s && nivelesTransporte(s) ? {} : null,
      };
    }),
    dTr,
    noComparable,
  );
  const trRows: MetricRow[] = (
    [
      ["d_excedente", "compare.bien.excedente"],
      ["d_bienestar", "compare.bien.bienestar"],
      ["d_excedente_social", "compare.bien.excedente_social"],
    ] as const
  ).map(([key, label]) => ({
    key,
    label: t(label),
    fmt: (v) => fmtPesos(v),
    betterWhen: "up",
    soloDelta: true,
  }));

  // C-04: export CSV de la lente activa. Para transporte el spec espeja las
  // secciones de KPITable (mismas claves i18n); mantener ambos en sync.
  const exportCsv = () => {
    const MODES = ["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"] as const;
    const num = (v: number | null | undefined, dec = 2): string | number =>
      v == null || !Number.isFinite(v) ? "" : Number(v.toFixed(dec));
    let header: (string | number)[];
    let body: (string | number)[][];
    if (kind === "transport") {
      const cols = rows.filter((r) => r.kpis);
      header = [t("compare.kpi.metric"), ...cols.map((c) => c.name)];
      const fila = (
        seccion: string,
        metrica: string,
        valueOf: (k: ScenarioKPIs) => number | null,
        dec = 2,
      ): (string | number)[] => [
        `${seccion} · ${metrica}`,
        ...cols.map((c) => num(valueOf(c.kpis!), dec)),
      ];
      body = [
        ...MODES.map((m) =>
          fila(
            t("compare.kpi.modal_share"),
            `% ${t(`modes.${m.toLowerCase()}`)}`,
            (k) => k.modal_share[m] * 100,
            1,
          ),
        ),
        ...MODES.slice(0, 4).map((m) =>
          fila(
            t("compare.kpi.mean_time"),
            `${t(`modes.${m.toLowerCase()}`)} (min)`,
            (k) => k.tiempo_medio_min[m],
            1,
          ),
        ),
        fila(
          t("compare.kpi.operation"),
          t("compare.kpi.metro_freq"),
          (k) => k.frecuencia_metro,
          1,
        ),
        fila(
          t("compare.kpi.operation"),
          t("compare.kpi.final_residual"),
          (k) => k.residuo_final,
          3,
        ),
        fila(
          t("compare.kpi.operation"),
          t("compare.kpi.physical_trips"),
          (k) => k.viajes_fisicos,
          0,
        ),
        fila(
          t("compare.kpi.congestion"),
          t("metrics_table.vc_auto"),
          (k) => k.vc_auto,
        ),
        fila(
          t("compare.kpi.congestion"),
          t("metrics_table.vc_metro"),
          (k) => k.vc_metro,
        ),
        fila(
          t("compare.kpi.congestion"),
          t("metrics_table.vc_bici"),
          (k) => k.vc_bici,
        ),
        fila(
          t("compare.kpi.emissions"),
          `${t("compare.kpi.total")} (kg/h)`,
          (k) => k.co2_total,
          0,
        ),
        fila(
          t("compare.kpi.emissions"),
          `${t("modes.auto")} (kg/h)`,
          (k) => k.co2_auto,
          0,
        ),
        fila(
          t("compare.kpi.emissions"),
          `${t("modes.metro")} (kg/h)`,
          (k) => k.co2_metro,
          0,
        ),
        ...([1, 2, 3] as const).flatMap((s) => {
          const sec = `${t("compare.kpi.stratum")} ${s}`;
          return [
            fila(
              sec,
              `${t("compare.kpi.travel_time")} (min)`,
              (k) => k.by_stratum[s].mean_time_min,
              1,
            ),
            fila(
              sec,
              t("compare.kpi.utility"),
              (k) => k.by_stratum[s].mean_utility,
            ),
            ...MODES.slice(0, 4).map((m) =>
              fila(
                sec,
                `% ${t(`modes.${m.toLowerCase()}`)}`,
                (k) => k.by_stratum[s].modal_share[m] * 100,
                1,
              ),
            ),
          ];
        }),
        ...trRows.map((r) => [
          `${t("compare.bien.title")} · ${r.label}`,
          ...cols.map((c) =>
            num(trCols.find((x) => x.id === c.id)?.values?.[r.key] ?? null, 0),
          ),
        ]),
      ];
    } else if (kind === "land_use") {
      const cols = luCols.filter((c) => c.values);
      header = [t("compare.kpi.metric"), ...cols.map((c) => c.name)];
      body = luRows.map((r) => [
        r.label,
        ...cols.map((c) => num(c.values![r.key] ?? null, 3)),
      ]);
    } else {
      const cols = cpCols.filter((c) => c.values);
      header = [t("compare.kpi.metric"), ...cols.map((c) => c.name)];
      body = cpRows.map((r) => [
        r.label,
        ...cols.map((c) => num(c.values![r.key] ?? null, 3)),
      ]);
    }
    downloadCsv(`comparacion-${kind}`, [header, ...body]);
  };

  return (
    <div
      className="main"
      style={{ padding: "var(--pad)", maxWidth: 1600, margin: "0 auto" }}
    >
      <div className="hero">
        <div className="hero-head">
          <div>
            <h1 className="hero-title">{t("compare.title")}</h1>
            <p className="hero-sub" style={{ margin: "6px 0 0" }}>
              {t("compare.subtitle")}
            </p>
          </div>
        </div>

        {/* Lente de comparación: qué solver corre sobre los mismos escenarios. */}
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <span className="text-etiqueta text-muted">
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
            <span className="text-etiqueta text-muted">
              {t("compare.coupled_hint", { max: VUELTAS_ACOPLADO_MAX })}
            </span>
          )}
          {kind === "transport" && (
            <div className="text-etiqueta text-muted">
              {t("compare.transport_hint_corto")}
              <PorQue>{t("compare.transport_hint_porque")}</PorQue>
            </div>
          )}
        </div>
      </div>

      <div className="panel-grid" style={{ marginBottom: "var(--gap)" }}>
        {scenarios.map((s, i) => (
          <div key={s.id} className="col-6">
            <ScenarioCard
              scenario={s}
              onRun={() => void runOne(s.id)}
              removable={i >= 2}
              isBase={s.id === baseInputsId}
              onMakeBase={s.config ? () => setBaseId(s.id) : undefined}
              nota={kind === "transport" ? notaTransporte(s) : undefined}
            />
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
                borderRadius: "var(--radius)",
                background: "var(--panel)",
                fontFamily: "var(--font-body)",
                fontSize: "var(--fs-etiqueta)",
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
            className="flex items-center gap-2 text-etiqueta text-muted"
            role="status"
          >
            <span className="pulse-dot" aria-hidden />
            {t("compare.processing", { count: runningCount })}
          </span>
        )}
        {doneCount > 0 && (
          <span className="text-etiqueta text-muted">
            {t("compare.ready_count", {
              done: doneCount,
              total: scenarios.length,
            })}
          </span>
        )}
        {doneCount > 0 && (
          <button type="button" onClick={exportCsv} className="btn ml-auto">
            ↓ {t("compare.export_csv")}
          </button>
        )}
      </div>

      {/* Diff de INPUTS. Va antes de los resultados y NO espera a que corran:
          sirve para revisar qué se está por comparar. Es la mitad que faltaba
          del par «cambié esto → pasó esto». */}
      {configuredCount >= 2 && (
        <div className="panel-grid" style={{ marginBottom: "var(--gap)" }}>
          <Panel
            title={t("compare.diff.title")}
            meta={t("compare.diff.meta")}
            cls="col-12"
          >
            <ScenarioDiffTable scenarios={scenarios} baseId={baseInputsId} />
          </Panel>
        </div>
      )}

      {doneCount > 0 && kind === "transport" && (
        <div className="panel-grid">
          <Panel
            n="00"
            title={t("compare.highlights")}
            meta="auto · diff"
            cls="col-12"
          >
            <ComparisonHighlights scenarios={rows} baseId={baseId} />
          </Panel>

          <Panel
            n="01"
            title={t("compare.kpis")}
            meta="delta vs base"
            cls="col-12"
          >
            <KPITable scenarios={rows} baseId={baseId} />
          </Panel>

          <Panel
            n="02"
            title={t("compare.bien.title")}
            meta="delta vs base"
            cls="col-12"
          >
            <MetricCompareTable cols={trCols} rows={trRows} baseId={baseId} />
            <p className="kpi-caption" style={{ marginTop: 8 }}>
              {t("compare.bien.caption")}
            </p>
            <AvisosBienestar deltas={dTr} cols={trCols} />
          </Panel>

          <Panel
            n="03"
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
          <Panel
            n="00"
            title={t("compare.lu.table_title")}
            meta="delta vs base"
            cls="col-12"
          >
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
                <StratumDistribution
                  composition={expectedComposition(
                    s.luResult!.result.Q,
                    s.luResult!.S,
                  )}
                />
              </Panel>
            ))}
        </div>
      )}

      {doneCount > 0 && kind === "coupled" && (
        <div className="panel-grid">
          <Panel
            n="00"
            title={t("compare.cp.table_title")}
            meta="delta vs base"
            cls="col-12"
          >
            <MetricCompareTable cols={cpCols} rows={cpRows} baseId={baseId} />
            <p className="kpi-caption" style={{ marginTop: 8 }}>
              {t("compare.cp.caption")}
            </p>
            <AvisosBienestar deltas={dCp} cols={cpCols} />
          </Panel>
        </div>
      )}
    </div>
  );
}
