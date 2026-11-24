import { useTranslation } from "react-i18next";

import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { defaultLandUseConfig } from "@/lib/defaults";
import { densidadDerivadaHabKm } from "@/lib/citySupply";
import { cn } from "@/lib/cn";
import { defaultSimulationConfig } from "@/lib/defaults";
import {
  CITY_PRESETS,
  LEE_POLITICA,
  POLICY_PRESETS,
  ciudadActiva,
  escenarioDesdeBase,
  politicaActiva,
  tieneAjustesManuales,
  type CityPresetName,
  type PolicyPresetName,
  type PolicyPresetValues,
} from "@/lib/presets";
import { fmtParking } from "@/lib/parking";
import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";
import { fmtDecimal, localeCifras } from "@/lib/modos";

/**
 * Galería de presets del Sandbox (F-01): expone CITY_PRESETS y POLICY_PRESETS
 * como chips de acción, con una tabla de **posición fija** que muestra los
 * mismos parámetros en el mismo orden para todos los escenarios y marca cuáles
 * difieren del default. Sin orden fijo no se puede leer qué mueve cada preset:
 * antes se iteraba el objeto del preset y cada uno declara sus claves en orden
 * distinto (y `Ciclorrecreovía` ni siquiera las declara todas).
 *
 * La tabla se arma desde la config VIVA, no desde el preset: así refleja el
 * estado real (incluye ajustes manuales y los parámetros que un preset no fija).
 *
 * Un preset de ciudad debe escalar TAMBIÉN la población del uso de suelo
 * (H_por_estrato): la app puebla desde ahí, no desde `densidad_hab_km` (S-05).
 */

interface Fila {
  key: string;
  labelKey: string;
  /** Valor actual y de referencia; el delta se marca contra el default. */
  valor: number;
  base: number;
  fmt: (v: number) => string;
}

const nf = (v: number) => v.toLocaleString(localeCifras());
const money = (v: number) => `$${nf(v)}`;

function filasCiudad(cfg: SimulationConfig, lu: LandUseConfig): Fila[] {
  const pob = (c: LandUseConfig) => c.H_por_estrato.reduce((a, b) => a + b, 0);
  const sumaH = pob(lu);
  const sumaHBase = pob(defaultLandUseConfig);
  return [
    {
      key: "largo",
      labelKey: "coupled.param.largo",
      valor: cfg.city.largo_ciudad_km,
      base: defaultSimulationConfig.city.largo_ciudad_km,
      fmt: (v) => `${nf(v)} km`,
    },
    {
      // La población (ΣH del uso de suelo) es el INPUT de escala: es lo que
      // puebla el MSA. Los presets de ciudad la conservan (iso-población).
      key: "poblacion",
      labelKey: "coupled.param.poblacion",
      valor: sumaH,
      base: sumaHBase,
      fmt: (v) => `${nf(v)} hog`,
    },
    {
      // Segunda dimensión de la forma: qué tan concentrada está la vivienda
      // dentro de la ciudad (σ del perfil de oferta del uso de suelo).
      key: "sigma",
      labelKey: "coupled.param.compacidad",
      valor: lu.oferta_sigma_frac,
      base: defaultLandUseConfig.oferta_sigma_frac,
      fmt: (v) => fmtDecimal(v, 2),
    },
    {
      // …y la densidad es la CONSECUENCIA: ρ = ΣH/largo. Se calcula en vivo
      // para que sea verdad aunque `densidad_hab_km` quede desfasado.
      key: "densidad",
      labelKey: "coupled.param.densidad_derivada",
      valor: densidadDerivadaHabKm(sumaH, cfg.city.largo_ciudad_km),
      base: densidadDerivadaHabKm(
        sumaHBase,
        defaultSimulationConfig.city.largo_ciudad_km,
      ),
      fmt: (v) => `${nf(v)} hab/km`,
    },
  ];
}

/** Grupos de la tabla de política: orden FIJO, agrupado por subsistema. */
const GRUPOS: { labelKey: string; keys: (keyof PolicyPresetValues)[] }[] = [
  {
    labelKey: "modes.auto",
    keys: ["num_pistas", "parking", "bencina", "peaje", "factor_flota"],
  },
  {
    labelKey: "modes.metro",
    keys: ["num_estaciones", "frec_max", "cap_tren", "tarifa"],
  },
  { labelKey: "modes.bici", keys: ["cap_bici"] },
];

/** Sólo presentación: cómo se rotula y se formatea cada parámetro. De dónde
 *  se LEE lo dice `LEE_POLITICA`, que la tabla de agregados también necesita. */
type T = (k: string, o?: Record<string, unknown>) => string;

const CAMPO: Record<
  keyof PolicyPresetValues,
  { labelKey: string; fmt: (v: number, t: T) => string }
> = {
  num_pistas: {
    labelKey: "coupled.param.pistas",
    fmt: nf,
  },
  parking: {
    labelKey: "coupled.param.parking",
    fmt: fmtParking,
  },
  bencina: {
    labelKey: "coupled.param.bencina",
    fmt: (v) => `${money(v)}/l`,
  },
  peaje: {
    labelKey: "coupled.param.peaje",
    fmt: (v) => `${money(v)}/km`,
  },
  factor_flota: {
    labelKey: "coupled.param.factor_flota",
    fmt: (v) => `× ${fmtDecimal(v, 2)}`,
  },
  num_estaciones: {
    labelKey: "coupled.param.estaciones",
    fmt: nf,
  },
  frec_max: {
    labelKey: "coupled.param.frec",
    fmt: (v) => `${nf(v)} tr/h`,
  },
  cap_tren: {
    labelKey: "coupled.param.cap_tren",
    fmt: (v) => `${nf(v)} pax`,
  },
  tarifa: {
    labelKey: "coupled.param.tarifa",
    fmt: money,
  },
  cap_bici: {
    labelKey: "coupled.param.cap_bici",
    fmt: (v) => `${nf(v)} bici/h`,
  },
};

interface PresetGalleryProps {
  /** `city` en Uso de suelo (la forma urbana se define ahí) · `policy` en
   *  Transporte. Antes ambos vivían en Transporte, lo que ponía la definición
   *  de la ciudad en el módulo que solo la consume. */
  variant: "city" | "policy";
}

export function PresetGallery({ variant }: PresetGalleryProps) {
  const { t } = useTranslation("simulator");
  const config = useSimulationStore((s) => s.config);
  const replaceConfig = useSimulationStore((s) => s.replaceConfig);
  const setLandUse = useLandUseStore((s) => s.setConfig);
  const landUse = useLandUseStore((s) => s.config);

  const cities = Object.entries(CITY_PRESETS).filter(
    ([k]) => k !== "Personalizado",
  );
  const policies = Object.entries(POLICY_PRESETS).filter(
    ([k]) => k !== "Personalizado",
  );

  const activeCity = ciudadActiva(config, landUse);

  const activePolicy = politicaActiva(config, landUse);

  /**
   * Elegir un preset arma el escenario DESDE LA BASE (`escenarioDesdeBase`):
   * valores de fábrica + la ciudad + la política, conservando sólo la
   * calibración. No parcha la config que haya, así que dos corridas del mismo
   * par ciudad-política son la misma corrida y se pueden comparar.
   *
   * Ciudad y política son dos dimensiones: elegir una conserva la otra, si se
   * reconoce; si no se reconoce (se editó a mano), vuelve a la de Base.
   */
  const aplicar = (
    ciudad: CityPresetName | null,
    politica: PolicyPresetName | null,
  ) => {
    const e = escenarioDesdeBase({ config, landUse }, ciudad, politica);
    replaceConfig(e.config);
    setLandUse(() => e.landUse);
  };
  const applyCity = (name: string) =>
    aplicar(name as CityPresetName, activePolicy);
  const applyPolicy = (name: string) =>
    aplicar(activeCity, name as PolicyPresetName);

  const ajustesManuales = tieneAjustesManuales({ config, landUse });

  const esCiudad = variant === "city";
  const nCambios = esCiudad
    ? filasCiudad(config, landUse).filter((f) => f.valor !== f.base).length
    : GRUPOS.flatMap((g) => g.keys).filter(
        (k) =>
          LEE_POLITICA[k](config) !== LEE_POLITICA[k](defaultSimulationConfig),
      ).length;

  return (
    <CollapsibleSection
      title={t("presets.title")}
      meta={(esCiudad ? activeCity : activePolicy) || t("presets.custom")}
      defaultOpen
    >
      {/* La regla, a la vista: un preset no parcha lo que haya, lo rearma. Y
          si el escenario ya no es el preset tal cual, se avisa antes de que
          alguien compare dos corridas creyendo que son del mismo preset. */}
      <p className="mb-1.5 text-etiqueta leading-snug text-muted">
        {t("escenario.desde_base")}
      </p>
      {ajustesManuales && (
        <p
          className="mb-1.5 text-etiqueta leading-snug text-[var(--alerta)]"
          role="status"
        >
          {t("escenario.ajustes")}
        </p>
      )}
      {esCiudad && (
        <>
          <div className="mb-1.5 flex flex-wrap gap-1">
            {cities.map(([name]) => (
              <Chip
                key={name}
                active={activeCity === name}
                onClick={() => applyCity(name)}
              >
                {name}
              </Chip>
            ))}
          </div>
          <Tabla filas={filasCiudad(config, landUse)} t={t} />
          <p className="mt-1 text-etiqueta leading-snug text-muted">
            {t("presets.presets_hint")}
          </p>
        </>
      )}

      {!esCiudad && (
        <div className="mb-1.5 flex flex-wrap gap-1">
          {policies.map(([name]) => (
            <Chip
              key={name}
              active={activePolicy === name}
              onClick={() => applyPolicy(name)}
            >
              {name}
            </Chip>
          ))}
        </div>
      )}
      {!esCiudad &&
        GRUPOS.map((g) => (
          <Tabla
            key={g.labelKey}
            titulo={t(g.labelKey)}
            t={t}
            filas={g.keys.map((k) => ({
              key: k,
              labelKey: CAMPO[k].labelKey,
              valor: LEE_POLITICA[k](config),
              base: LEE_POLITICA[k](defaultSimulationConfig),
              fmt: (v: number) => CAMPO[k].fmt(v, t),
            }))}
          />
        ))}

      <p className="mt-2 text-etiqueta leading-snug text-muted">
        {nCambios > 0
          ? t("presets.diff_hint", { n: nCambios })
          : t("presets.no_diff_hint")}
      </p>
    </CollapsibleSection>
  );
}

/** Tabla de posición fija: mismas filas, mismo orden, para todo escenario.
 * Las que difieren del default se destacan con una flecha de dirección; NO se
 * colorean por «bueno/malo» (subir el parking es bueno o malo según el objetivo). */
function Tabla({
  filas,
  titulo,
  t,
}: {
  filas: Fila[];
  titulo?: string;
  t: (k: string, o?: Record<string, unknown>) => string;
}) {
  return (
    <div className="mb-1">
      {titulo && (
        <div className="mt-1 text-etiqueta text-muted opacity-70">{titulo}</div>
      )}
      <dl className="grid grid-cols-[1fr_auto] gap-x-2 text-etiqueta">
        {filas.map((f) => {
          const cambiado = f.valor !== f.base;
          return (
            <div key={f.key} className="col-span-2 grid grid-cols-subgrid">
              <dt
                className={cn(
                  cambiado ? "text-[var(--ink-2)]" : "text-muted opacity-60",
                )}
              >
                {t(f.labelKey)}
              </dt>
              <dd
                className={cn(
                  "text-right font-mono tabular-nums",
                  cambiado
                    ? "font-semibold text-[var(--ink)]"
                    : "text-muted opacity-60",
                )}
                title={
                  cambiado
                    ? t("presets.vs_base", { base: f.fmt(f.base) })
                    : t("presets.same_as_base")
                }
              >
                {f.fmt(f.valor)}
                {cambiado && (
                  <span aria-hidden className="ml-0.5">
                    {f.valor > f.base ? "↑" : "↓"}
                  </span>
                )}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-full border px-2 py-0.5 text-etiqueta",
        active
          ? "border-[var(--ink)] bg-[var(--ink)] text-[var(--paper)]"
          : "border-[var(--rule)] text-[var(--ink-2)] hover:bg-[var(--paper-2)]",
      )}
    >
      {children}
    </button>
  );
}
