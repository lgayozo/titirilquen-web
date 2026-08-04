import { useTranslation } from "react-i18next";

import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";
import type { Scenario } from "@/store/compareStore";

/**
 * Diff de **inputs** entre escenarios: qué parámetros difieren de la base.
 *
 * La tabla de KPIs dice qué CAMBIÓ EN LOS RESULTADOS; sin esto falta la otra
 * mitad del par pedagógico, qué se cambió para provocarlo. El resumen de la
 * tarjeta no alcanza: mostraba solo parking y tarifa, así que dos escenarios
 * que difieren en capacidad de ciclovía se veían idénticos.
 *
 * Solo se listan las filas donde ALGÚN escenario difiere de la base — con ~30
 * parámetros, mostrarlos todos enterraría los tres que importan.
 */

interface Campo {
  labelKey: string;
  /** `null` ⇒ el escenario no tiene ese dato (p. ej. sin uso de suelo). */
  get: (
    c: SimulationConfig,
    lu: LandUseConfig | null,
  ) => number | string | null;
  fmt?: (v: number | string) => string;
}

const nf = (v: number | string) =>
  typeof v === "number" ? v.toLocaleString("es-CL") : String(v);
const money = (v: number | string) =>
  typeof v === "number" ? `$${nf(v)}` : String(v);

/** Orden fijo por subsistema, igual criterio que la galería de presets. */
const GRUPOS: { labelKey: string; campos: Campo[] }[] = [
  {
    labelKey: "compare.diff.city",
    campos: [
      {
        labelKey: "compare.diff.largo",
        get: (c) => c.city.largo_ciudad_km,
        fmt: (v) => `${nf(v)} km`,
      },
      { labelKey: "compare.diff.celdas", get: (c) => c.city.n_celdas },
      {
        labelKey: "compare.diff.pendiente",
        get: (c) => c.city.pendiente_porcentaje,
        fmt: (v) => `${nf(v)} %`,
      },
      {
        labelKey: "compare.diff.teletrabajo",
        get: (c) => c.city.teletrabajo_factor,
        fmt: (v) => `× ${nf(v)}`,
      },
      { labelKey: "compare.diff.forma", get: (_c, lu) => lu?.forma ?? null },
      {
        labelKey: "compare.diff.sigma",
        get: (_c, lu) => lu?.oferta_sigma_frac ?? null,
      },
      {
        labelKey: "compare.diff.poblacion",
        get: (_c, lu) =>
          lu ? lu.H_por_estrato.reduce((a, b) => a + b, 0) : null,
      },
    ],
  },
  {
    labelKey: "modes.auto",
    campos: [
      { labelKey: "coupled.param.pistas", get: (c) => c.supply.car.num_pistas },
      {
        labelKey: "supply_params.car.v_max_kmh",
        get: (c) => c.supply.car.v_max_kmh,
        fmt: (v) => `${nf(v)} km/h`,
      },
      {
        labelKey: "supply_params.car.ancho_pista_m",
        get: (c) => c.supply.car.ancho_pista_m,
        fmt: (v) => `${nf(v)} m`,
      },
      {
        labelKey: "compare.diff.alpha_bpr_auto",
        get: (c) => c.supply.car.alpha_bpr,
      },
      {
        labelKey: "compare.diff.beta_bpr_auto",
        get: (c) => c.supply.car.beta_bpr,
      },
      {
        labelKey: "coupled.param.parking",
        get: (c) => c.demand.globales.costo_parking,
        fmt: money,
      },
      {
        labelKey: "coupled.param.bencina",
        get: (c) => c.demand.globales.costo_combustible_km,
        fmt: (v) => `${money(v)}/km`,
      },
      {
        labelKey: "coupled.param.factor_flota",
        get: (c) => c.demand.globales.factor_flota_auto,
        fmt: (v) => `× ${nf(v)}`,
      },
    ],
  },
  {
    labelKey: "modes.metro",
    campos: [
      {
        labelKey: "coupled.param.estaciones",
        get: (c) => c.supply.train.num_estaciones,
      },
      {
        labelKey: "coupled.param.cap_tren",
        get: (c) => c.supply.train.capacidad_tren,
        fmt: (v) => `${nf(v)} pax`,
      },
      {
        labelKey: "supply_params.train.frec_min",
        get: (c) => c.supply.train.frec_min,
        fmt: (v) => `${nf(v)} tph`,
      },
      {
        labelKey: "supply_params.train.frec_max",
        get: (c) => c.supply.train.frec_max,
        fmt: (v) => `${nf(v)} tph`,
      },
      {
        labelKey: "supply_params.train.v_tren_kmh",
        get: (c) => c.supply.train.v_tren_kmh,
        fmt: (v) => `${nf(v)} km/h`,
      },
      {
        labelKey: "coupled.param.tarifa",
        get: (c) => c.demand.globales.costo_tarifa_metro,
        fmt: money,
      },
      {
        labelKey: "compare.diff.anden_alpha",
        get: (c) => c.supply.train.anden_alpha,
      },
      {
        labelKey: "compare.diff.anden_beta",
        get: (c) => c.supply.train.anden_beta,
      },
    ],
  },
  {
    labelKey: "modes.bici",
    campos: [
      {
        labelKey: "coupled.param.cap_bici",
        get: (c) => c.supply.bike.capacidad_pista,
        fmt: (v) => `${nf(v)} bici/h`,
      },
      {
        labelKey: "supply_params.bike.v_media_kmh",
        get: (c) => c.supply.bike.v_media_kmh,
        fmt: (v) => `${nf(v)} km/h`,
      },
      {
        labelKey: "compare.diff.alpha_bpr_bici",
        get: (c) => c.supply.bike.alpha_bpr,
      },
      {
        labelKey: "compare.diff.beta_bpr_bici",
        get: (c) => c.supply.bike.beta_bpr,
      },
    ],
  },
  {
    labelKey: "compare.diff.numerico",
    campos: [
      { labelKey: "compare.diff.max_iter", get: (c) => c.max_iter },
      { labelKey: "compare.diff.tolerance", get: (c) => c.tolerance },
      { labelKey: "compare.diff.assignment", get: (c) => c.assignment },
    ],
  },
];

interface Props {
  scenarios: Scenario[];
  baseId: string | undefined;
}

export function ScenarioDiffTable({ scenarios, baseId }: Props) {
  const { t } = useTranslation("simulator");
  const conConfig = scenarios.filter((s) => s.config);
  const base = conConfig.find((s) => s.id === baseId) ?? conConfig[0];
  if (!base?.config || conConfig.length < 2) {
    return (
      <p className="text-[11px] text-[var(--muted)]">
        {t("compare.diff.need_two")}
      </p>
    );
  }
  const otros = conConfig.filter((s) => s.id !== base.id);

  const valor = (sc: Scenario, campo: Campo) =>
    sc.config ? campo.get(sc.config, sc.landUse) : null;

  const grupos = GRUPOS.map((g) => ({
    labelKey: g.labelKey,
    filas: g.campos
      .map((campo) => {
        const vBase = valor(base, campo);
        const vOtros = otros.map((sc) => valor(sc, campo));
        // Solo interesa la fila si alguien difiere de la base.
        const difiere = vOtros.some((v) => v !== vBase);
        return difiere ? { campo, vBase, vOtros } : null;
      })
      .filter((f): f is NonNullable<typeof f> => f !== null),
  })).filter((g) => g.filas.length > 0);

  if (grupos.length === 0) {
    return (
      <p className="text-[11px] text-[var(--muted)]">
        {t("compare.diff.identical")}
      </p>
    );
  }

  const fmt = (campo: Campo, v: number | string | null) =>
    v == null ? "—" : campo.fmt ? campo.fmt(v) : nf(v);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--rule)] text-[11px] uppercase tracking-wide text-[var(--muted)]">
            <th className="py-1 text-left font-normal">
              {t("compare.diff.parametro")}
            </th>
            <th className="py-1 text-right font-normal">
              {base.name ||
                t("compare.scenario_card.untitled", { id: base.id })}{" "}
              <span className="text-[var(--accent)]">
                ({t("compare.scenario_card.base")})
              </span>
            </th>
            {otros.map((sc) => (
              <th key={sc.id} className="py-1 text-right font-normal">
                {sc.name || t("compare.scenario_card.untitled", { id: sc.id })}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grupos.map((g) => (
            <tr key={g.labelKey} className="align-top">
              <td colSpan={2 + otros.length} className="pt-2">
                <table className="w-full">
                  <tbody>
                    <tr>
                      <td
                        colSpan={2 + otros.length}
                        className="pb-1 text-[10px] uppercase tracking-wide text-[var(--muted)]"
                      >
                        {t(g.labelKey)}
                      </td>
                    </tr>
                    {g.filas.map(({ campo, vBase, vOtros }) => (
                      <tr
                        key={campo.labelKey}
                        className="border-t border-[var(--rule)]"
                      >
                        <td className="py-1 pr-2">{t(campo.labelKey)}</td>
                        <td className="py-1 text-right tabular-nums text-[var(--muted)]">
                          {fmt(campo, vBase)}
                        </td>
                        {vOtros.map((v, i) => (
                          <td
                            key={otros[i]!.id}
                            className={cnDiff(v !== vBase)}
                          >
                            {fmt(campo, v)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Resalta solo lo que cambia. Sin semántica de bueno/malo: subir una tarifa no
 *  es «peor», depende de la pregunta. */
function cnDiff(cambia: boolean): string {
  return cambia
    ? "py-1 text-right tabular-nums font-medium text-[var(--accent)]"
    : "py-1 text-right tabular-nums text-[var(--muted)]";
}
