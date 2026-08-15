import { useTranslation } from "react-i18next";

import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { defaultLandUseConfig } from "@/lib/api-v2";
import { densidadDerivadaHabKm } from "@/lib/citySupply";
import { cn } from "@/lib/cn";
import { defaultSimulationConfig } from "@/lib/defaults";
import {
  CITY_PRESETS,
  POLICY_PRESETS,
  type PolicyPresetValues,
} from "@/lib/presets";
import type { SimulationConfig } from "@/lib/types";
import type { LandUseConfig } from "@/lib/types-v2";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

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

const nf = (v: number) => v.toLocaleString("es-CL");
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
      fmt: (v) => v.toFixed(2),
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
    keys: ["num_pistas", "parking", "bencina", "factor_flota"],
  },
  {
    labelKey: "modes.metro",
    keys: ["num_estaciones", "frec_max", "cap_tren", "tarifa"],
  },
  { labelKey: "modes.bici", keys: ["cap_bici"] },
];

const CAMPO: Record<
  keyof PolicyPresetValues,
  {
    labelKey: string;
    get: (c: SimulationConfig) => number;
    fmt: (v: number) => string;
  }
> = {
  num_pistas: {
    labelKey: "coupled.param.pistas",
    get: (c) => c.supply.car.num_pistas,
    fmt: nf,
  },
  parking: {
    labelKey: "coupled.param.parking",
    get: (c) => c.demand.globales.costo_parking,
    fmt: money,
  },
  bencina: {
    labelKey: "coupled.param.bencina",
    get: (c) => c.demand.globales.costo_combustible_km,
    fmt: (v) => `${money(v)}/km`,
  },
  factor_flota: {
    labelKey: "coupled.param.factor_flota",
    get: (c) => c.demand.globales.factor_flota_auto,
    fmt: (v) => `× ${v.toFixed(2)}`,
  },
  num_estaciones: {
    labelKey: "coupled.param.estaciones",
    get: (c) => c.supply.train.num_estaciones,
    fmt: nf,
  },
  frec_max: {
    labelKey: "coupled.param.frec",
    get: (c) => c.supply.train.frec_max,
    fmt: (v) => `${nf(v)} tr/h`,
  },
  cap_tren: {
    labelKey: "coupled.param.cap_tren",
    get: (c) => c.supply.train.capacidad_tren,
    fmt: (v) => `${nf(v)} pax`,
  },
  tarifa: {
    labelKey: "coupled.param.tarifa",
    get: (c) => c.demand.globales.costo_tarifa_metro,
    fmt: money,
  },
  cap_bici: {
    labelKey: "coupled.param.cap_bici",
    get: (c) => c.supply.bike.capacidad_pista,
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
  const setConfig = useSimulationStore((s) => s.setConfig);
  const setLandUse = useLandUseStore((s) => s.setConfig);
  const landUse = useLandUseStore((s) => s.config);

  const cities = Object.entries(CITY_PRESETS).filter(
    ([k]) => k !== "Personalizado",
  );
  const policies = Object.entries(POLICY_PRESETS).filter(
    ([k]) => k !== "Personalizado",
  );

  // La ciudad activa se identifica por las dos dimensiones de forma que el
  // preset fija (largo y σ); la densidad no, porque es derivada (ver applyCity).
  // Si además declara `poblacion` (los de ESCALA) hay que compararla: Base y
  // Metrópolis comparten geometría y sin esto el `.find` devolvería siempre el
  // primero, mostrando «Base» en una ciudad de 144.000 habitantes.
  const sumaHActual = landUse.H_por_estrato.reduce((a, b) => a + b, 0);
  const activeCity = cities.find(
    ([, v]) =>
      config.city.largo_ciudad_km === v.largo_ciudad &&
      (v.sigma === undefined || landUse.oferta_sigma_frac === v.sigma) &&
      (v.poblacion === undefined || Math.round(sumaHActual) === v.poblacion),
  )?.[0];

  const activePolicy = policies.find(([, v]) =>
    (Object.keys(v) as (keyof PolicyPresetValues)[]).every(
      (k) => CAMPO[k].get(config) === v[k],
    ),
  )?.[0];

  /**
   * ISO-POBLACIÓN: el preset de ciudad cambia SOLO el largo y conserva ΣH; la
   * densidad se recalcula como ρ = ΣH/largo. Así «compacta vs dispersa» compara
   * forma urbana con la misma gente, que es la comparativa estática que interesa.
   *
   * Antes se escalaba ΣH desde la densidad del preset y la población cambiaba
   * (Compacta 50.400 vs Dispersa 19.500): eso INVERTÍA la lectura de congestión
   * —la compacta parecía saturada (v/c 1.25 vs 0.55) por tener 2.6× más gente,
   * cuando a igual población es 0.92 vs 0.98— y enmascaraba el efecto real de la
   * compacidad sobre la bici (+5.0 pp medidos vs +1.0 pp aparente).
   *
   * El campo `densidad` de CITY_PRESETS lo sigue usando el módulo acoplado
   * (applyJointPreset), donde las poblaciones difieren a propósito por
   * estabilidad numérica del loop exterior (D-24).
   *
   * EXCEPCIÓN — presets de ESCALA (`poblacion` declarada): «Metrópolis» existe
   * justamente para mover la población, así que fija ΣH escalando los estratos
   * y conservando sus proporciones. «Base» también la declara para que el viaje
   * de vuelta funcione: sin eso, volver de Metrópolis dejaba la geometría de
   * Base con 144.000 habitantes. Compacta y Dispersa NO la declaran a
   * propósito: comparan forma a la población que el usuario tenga.
   */
  const applyCity = (name: string) => {
    const p = CITY_PRESETS[name];
    if (!p?.largo_ciudad) return;
    const largo = p.largo_ciudad;
    const sumaH = landUse.H_por_estrato.reduce((a, b) => a + b, 0);
    const sumaFinal = p.poblacion ?? sumaH;
    setConfig((c) => ({
      ...c,
      city: {
        ...c.city,
        largo_ciudad_km: largo,
        densidad_hab_km: densidadDerivadaHabKm(sumaFinal, largo),
      },
    }));
    // La concentración de la oferta (σ) es la segunda dimensión de la forma:
    // sin ella el preset movía la mitad del efecto.
    setLandUse((lu) => {
      const next = p.sigma !== undefined ? { ...lu, oferta_sigma_frac: p.sigma } : lu;
      if (p.poblacion === undefined || sumaH <= 0) return next;
      // `H_por_estrato` es `tuple[int, int, int]` en Pydantic: hay que entregar
      // enteros. El tercero absorbe el residuo para que ΣH dé EXACTO — si no,
      // el redondeo movería la suma y `activeCity` no reconocería su propio
      // preset.
      const k = p.poblacion / sumaH;
      const [h1, h2] = next.H_por_estrato;
      const a = Math.round(h1 * k);
      const b = Math.round(h2 * k);
      return { ...next, H_por_estrato: [a, b, p.poblacion - a - b] };
    });
  };

  const applyPolicy = (name: string) => {
    const p = POLICY_PRESETS[name];
    if (!p) return;
    setConfig((c) => ({
      ...c,
      supply: {
        ...c.supply,
        car: {
          ...c.supply.car,
          ...(p.num_pistas !== undefined && { num_pistas: p.num_pistas }),
        },
        bike: {
          ...c.supply.bike,
          ...(p.cap_bici !== undefined && { capacidad_pista: p.cap_bici }),
        },
        train: {
          ...c.supply.train,
          ...(p.num_estaciones !== undefined && {
            num_estaciones: p.num_estaciones,
          }),
          ...(p.frec_max !== undefined && { frec_max: p.frec_max }),
          ...(p.cap_tren !== undefined && { capacidad_tren: p.cap_tren }),
        },
      },
      demand: {
        ...c.demand,
        globales: {
          ...c.demand.globales,
          ...(p.tarifa !== undefined && { costo_tarifa_metro: p.tarifa }),
          ...(p.parking !== undefined && { costo_parking: p.parking }),
          ...(p.bencina !== undefined && { costo_combustible_km: p.bencina }),
        },
      },
    }));
  };

  const esCiudad = variant === "city";
  const nCambios = esCiudad
    ? filasCiudad(config, landUse).filter((f) => f.valor !== f.base).length
    : GRUPOS.flatMap((g) => g.keys).filter(
        (k) => CAMPO[k].get(config) !== CAMPO[k].get(defaultSimulationConfig),
      ).length;

  return (
    <CollapsibleSection
      title={t("presets.title")}
      meta={(esCiudad ? activeCity : activePolicy) || t("presets.custom")}
      defaultOpen
    >
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
          <p className="mt-1 text-[10px] leading-snug text-muted">
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
              valor: CAMPO[k].get(config),
              base: CAMPO[k].get(defaultSimulationConfig),
              fmt: CAMPO[k].fmt,
            }))}
          />
        ))}

      <p className="mt-2 text-[10px] leading-snug text-muted">
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
        <div className="mt-1 font-fig text-[9px] uppercase tracking-[0.1em] text-muted opacity-70">
          {titulo}
        </div>
      )}
      <dl className="grid grid-cols-[1fr_auto] gap-x-2 text-[10.5px]">
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
        "rounded-full border px-2 py-0.5 text-[10.5px]",
        active
          ? "border-[var(--ink)] bg-[var(--ink)] text-[var(--paper)]"
          : "border-[var(--rule)] text-[var(--ink-2)] hover:bg-[var(--paper-2)]",
      )}
    >
      {children}
    </button>
  );
}
