import { useTranslation } from "react-i18next";

import { SidebarSection } from "@/components/ui/SidebarSection";
import { cn } from "@/lib/cn";
import { CITY_PRESETS, POLICY_PRESETS, type PolicyPresetValues } from "@/lib/presets";
import type { SimulationConfig } from "@/lib/types";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

/**
 * Galería de presets del Sandbox (F-01): expone CITY_PRESETS y POLICY_PRESETS
 * como chips de acción. Un preset de ciudad debe escalar TAMBIÉN la población
 * del uso de suelo (H_por_estrato): la app puebla desde ahí, no desde
 * `densidad_hab_km` (S-05) — sin eso el preset sería inerte.
 *
 * Los chips aplican sobre la config VIVA (una política no resetea la ciudad ni
 * los ajustes del usuario). "Personalizado" no es un chip: es el estado en que
 * ningún preset con nombre coincide con la config.
 */

/** Campos de la config que definen una política (mismos que applyJointPreset). */
function policyFields(cfg: SimulationConfig): Required<PolicyPresetValues> {
  return {
    tarifa: cfg.demand.globales.costo_tarifa_metro,
    parking: cfg.demand.globales.costo_parking,
    bencina: cfg.demand.globales.costo_combustible_km,
    num_pistas: cfg.supply.car.num_pistas,
    num_estaciones: cfg.supply.train.num_estaciones,
    cap_bici: cfg.supply.bike.capacidad_pista,
    frec_max: cfg.supply.train.frec_max,
    cap_tren: cfg.supply.train.capacidad_tren,
  };
}

/** Rótulos de los campos de política (claves ya existentes de coupled.param). */
const FIELD_LABEL_KEY: Record<keyof PolicyPresetValues, string> = {
  tarifa: "coupled.param.tarifa",
  parking: "coupled.param.parking",
  bencina: "coupled.param.bencina",
  num_pistas: "coupled.param.pistas",
  num_estaciones: "coupled.param.estaciones",
  cap_bici: "coupled.param.cap_bici",
  frec_max: "coupled.param.frec",
  cap_tren: "coupled.param.cap_tren",
};

export function PresetGallery() {
  const { t } = useTranslation("simulator");
  const config = useSimulationStore((s) => s.config);
  const setConfig = useSimulationStore((s) => s.setConfig);
  const setLandUse = useLandUseStore((s) => s.setConfig);
  const landUse = useLandUseStore((s) => s.config);

  const cities = Object.entries(CITY_PRESETS).filter(([k]) => k !== "Personalizado");
  const policies = Object.entries(POLICY_PRESETS).filter(([k]) => k !== "Personalizado");

  const activeCity = cities.find(
    ([, v]) =>
      config.city.largo_ciudad_km === v.largo_ciudad &&
      config.city.densidad_hab_km === v.densidad,
  )?.[0];

  const current = policyFields(config);
  const activePolicy = policies.find(([, v]) =>
    (Object.keys(v) as (keyof PolicyPresetValues)[]).every((k) => current[k] === v[k]),
  )?.[0];

  const applyCity = (name: string) => {
    const p = CITY_PRESETS[name];
    if (!p?.largo_ciudad || !p.densidad) return;
    setConfig((c) => ({
      ...c,
      city: { ...c.city, largo_ciudad_km: p.largo_ciudad!, densidad_hab_km: p.densidad! },
    }));
    // Escalar ΣH = densidad·largo conservando los shares actuales del suelo.
    const total = p.densidad * p.largo_ciudad;
    setLandUse((lu) => {
      const sum = lu.H_por_estrato.reduce((a, b) => a + b, 0) || 1;
      return {
        ...lu,
        H_por_estrato: lu.H_por_estrato.map((h) =>
          Math.max(1, Math.round((total * h) / sum)),
        ) as [number, number, number],
      };
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
          ...(p.num_estaciones !== undefined && { num_estaciones: p.num_estaciones }),
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

  // Qué cambió el preset activo respecto de la config default equivalente:
  // mostramos los campos que la política FIJA (todos sus campos declarados),
  // para que el estudiante vea por qué el escenario es pro-X.
  const activeDiff = activePolicy
    ? (Object.entries(POLICY_PRESETS[activePolicy]!) as [
        keyof PolicyPresetValues,
        number,
      ][])
    : null;

  const nf = (v: number) => v.toLocaleString("es-CL");

  return (
    <SidebarSection
      title={t("presets.title")}
      meta={activePolicy ?? activeCity ?? t("presets.custom")}
      defaultOpen
    >
      <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
        {t("presets.city_label")}
      </div>
      <div className="mb-2 flex flex-wrap gap-1">
        {cities.map(([name]) => (
          <Chip key={name} active={activeCity === name} onClick={() => applyCity(name)}>
            {name}
          </Chip>
        ))}
      </div>

      <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
        {t("presets.policy_label")}
      </div>
      <div className="flex flex-wrap gap-1">
        {policies.map(([name]) => (
          <Chip key={name} active={activePolicy === name} onClick={() => applyPolicy(name)}>
            {name}
          </Chip>
        ))}
      </div>

      {activeDiff && (
        <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-0.5 text-[10px] text-muted">
          {activeDiff.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-1">
              <dt>{t(FIELD_LABEL_KEY[k])}</dt>
              <dd className="font-mono">{nf(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      <p className="mt-2 text-[10px] leading-snug text-muted">
        {t("presets.hint", {
          pop: nf(landUse.H_por_estrato.reduce((a, b) => a + b, 0)),
        })}
      </p>
    </SidebarSection>
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
