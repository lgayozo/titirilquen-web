import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { votClpHora } from "@/lib/agregados";
import { defaultSimulationConfig } from "@/lib/defaults";
import type {
  PhysicalPenalties,
  SimulationConfig,
  StratumBetas,
  StratumConfig,
  StratumId,
} from "@/lib/types";

/**
 * Panel de CALIBRACIÓN del logit: los 14 coeficientes por estrato que hasta
 * ahora el estudiante no veía en ninguna parte, más las dos probabilidades
 * estructurales de la población (tenencia de auto, tasa base de teletrabajo).
 *
 * Va separado de las palancas de política a propósito y así rotulado: mover un
 * beta cambia el MODELO de comportamiento, no la ciudad ni la oferta. Un
 * escenario donde bajó el uso del auto porque se editó `asc_auto` no dice nada
 * sobre política de transporte.
 *
 * Dos decisiones de diseño:
 *
 * 1. **Campos numéricos, no sliders.** Los coeficientes cruzan órdenes de
 *    magnitud —`b_costo` va de −0,00008 (estrato alto) a −0,0006 (bajo), un
 *    factor 7,5— así que no hay rango común que poner en un slider. El
 *    contraste visual con los sliders de política además refuerza el rótulo.
 *
 * 2. **Las cifras derivadas arriba.** Catorce números en utiles son ilegibles;
 *    el valor del tiempo (β_t/β_c) y las razones espera/viaje y caminata/viaje
 *    son la traducción a unidades que el estudiante puede juzgar.
 *
 * No toca el core ni el schema: los betas ya viajan dentro de
 * `SimulationConfig.demand.estratos[h].betas`, así que ya se exportan, ya van
 * en el link compartido y ya los cubre el test de contrato.
 */

interface Props {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
}

const STRATA: StratumId[] = [1, 2, 3];

/** Claves de `StratumBetas` que son escalares (excluye el sub-objeto). */
type BetaKey = Exclude<keyof StratumBetas, "penalizaciones_fisicas">;

const ASC_KEYS: BetaKey[] = ["asc_auto", "asc_metro", "asc_bici", "asc_caminata"];
const TIEMPO_KEYS: BetaKey[] = [
  "b_tiempo_viaje",
  "b_tiempo_espera",
  "b_tiempo_acceso",
  "b_tiempo_caminata",
  "b_costo",
];
const PENAL_KEYS: (keyof PhysicalPenalties)[] = [
  "bici_10",
  "bici_20",
  "bici_30",
  "walk_5",
  "walk_15",
  "walk_25",
];

/** Paso de edición por parámetro: `b_costo` vive en 1e-4, el resto en 1e-2. */
const STEP: Record<BetaKey, number> = {
  asc_auto: 0.05,
  asc_metro: 0.05,
  asc_bici: 0.05,
  asc_caminata: 0.05,
  b_tiempo_viaje: 0.005,
  b_tiempo_espera: 0.005,
  b_tiempo_acceso: 0.005,
  b_tiempo_caminata: 0.005,
  b_costo: 0.00002,
};

const fmtMoney = (v: number) =>
  `${v < 0 ? "−" : ""}$${Math.round(Math.abs(v)).toLocaleString("es-CL")}`;

/**
 * Campo numérico que confirma al SALIR del campo (o con Enter), no en cada
 * tecla. Dos razones:
 *
 * - Mientras se teclea hace falta un borrador de texto, porque estados
 *   intermedios como `-0.` o `-0.00` no sobreviven a un `value` numérico
 *   controlado: se colapsarían a `0` y sería imposible escribir un negativo
 *   chico como −0,0002.
 * - Atando ese borrador al foco, un cambio externo —restaurar los defaults,
 *   importar un escenario— nunca compite contra él: ocurre con el campo sin
 *   foco, o sea sin borrador que tape el valor nuevo.
 *
 * De paso, confirmar al salir evita recalcular las cifras derivadas con
 * números a medio escribir.
 */
function NumberField({
  label,
  value,
  step,
  onChange,
  title,
}: {
  label: string;
  value: number;
  step: number;
  onChange: (v: number) => void;
  title?: string;
}) {
  const [draft, setDraft] = useState<string | null>(null);

  const confirmar = () => {
    if (draft == null) return;
    const n = Number(draft);
    if (draft.trim() !== "" && Number.isFinite(n) && n !== value) onChange(n);
    setDraft(null);
  };

  return (
    <label className="flex items-baseline justify-between gap-2" title={title}>
      <span className="text-[11px] leading-tight text-[var(--ink-2)]">
        {label}
      </span>
      <input
        type="number"
        step={step}
        value={draft ?? String(value)}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={confirmar}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
        }}
        className="w-[88px] shrink-0 text-right tabular-nums"
        style={{
          background: "var(--paper)",
          border: "1px solid var(--rule)",
          color: "var(--ink)",
          fontFamily: "var(--font-fig)",
          fontSize: 11,
          padding: "3px 5px",
        }}
      />
    </label>
  );
}

function Grupo({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="mt-3">
      <div className="mb-1.5 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
        {title}
      </div>
      <div className="flex flex-col gap-1.5">{children}</div>
      {hint && (
        <p className="mt-1.5 text-[10px] leading-snug text-muted">{hint}</p>
      )}
    </div>
  );
}

export function CalibrationPanel({ config, onChange }: Props) {
  const { t } = useTranslation("simulator");
  const [estrato, setEstrato] = useState<StratumId>(2);

  const s = config.demand.estratos[estrato];
  const betas = s.betas;

  /** Todas las escrituras parten del estrato VIGENTE en el store (`c`), no del
   *  capturado en este render: si dos campos se editan dentro del mismo batch
   *  de React, un patch armado desde el closure revertiría al otro. */
  const updateStratum = (fn: (s: StratumConfig) => StratumConfig) =>
    onChange((c) => ({
      ...c,
      demand: {
        ...c.demand,
        estratos: {
          ...c.demand.estratos,
          [estrato]: fn(c.demand.estratos[estrato]),
        },
      },
    }));

  const setStratum = (patch: Partial<StratumConfig>) =>
    updateStratum((s) => ({ ...s, ...patch }));

  const setBeta = (patch: Partial<StratumBetas>) =>
    updateStratum((s) => ({ ...s, betas: { ...s.betas, ...patch } }));

  const setPenal = (patch: Partial<PhysicalPenalties>) =>
    updateStratum((s) => ({
      ...s,
      betas: {
        ...s.betas,
        penalizaciones_fisicas: { ...s.betas.penalizaciones_fisicas, ...patch },
      },
    }));

  const restaurar = () =>
    updateStratum(() => defaultSimulationConfig.demand.estratos[estrato]);

  // Cifras derivadas: la traducción de los coeficientes a unidades juzgables.
  const vot = votClpHora(config.demand, estrato);
  const razon = (b: number) =>
    betas.b_tiempo_viaje === 0 ? null : b / betas.b_tiempo_viaje;
  const rEspera = razon(betas.b_tiempo_espera);
  const rAcceso = razon(betas.b_tiempo_acceso);
  const rCaminata = razon(betas.b_tiempo_caminata);
  const fmtRazon = (r: number | null) => (r == null ? "—" : `${r.toFixed(2)}×`);

  // Resumen plegado: el valor del tiempo de los tres estratos. Con β costo ≥ 0
  // no está definido, y mostrarlo igual daría un VoT negativo sin sentido.
  const votTodos = STRATA.map((h) => {
    const bc = config.demand.estratos[h].betas.b_costo;
    return bc < 0 ? fmtMoney(votClpHora(config.demand, h)) : "—";
  });

  return (
    <CollapsibleSection
      title={t("calibration.title")}
      meta={votTodos.join(" · ")}
    >
      <p className="mb-3 text-[11px] leading-snug text-muted">
        {t("calibration.not_a_policy")}
      </p>

      <div className="seg" style={{ width: "100%" }}>
        {STRATA.map((h) => (
          <button
            key={h}
            type="button"
            className={estrato === h ? "active" : ""}
            onClick={() => setEstrato(h)}
            style={{ flex: 1 }}
          >
            {t(`strata.${h === 1 ? "alto" : h === 2 ? "medio" : "bajo"}`)}
          </button>
        ))}
      </div>

      {/* Cifras derivadas — se recalculan al editar cualquier coeficiente. */}
      <dl
        className="mt-3 flex flex-col gap-1 border-y py-2"
        style={{ borderColor: "var(--rule)" }}
      >
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[11px] text-[var(--ink-2)]">
            {t("calibration.vot")}
          </dt>
          <dd className="font-fig text-[12px] tabular-nums text-[var(--ink)]">
            {betas.b_costo < 0 ? `${fmtMoney(vot)}/h` : "—"}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[11px] text-[var(--ink-2)]">
            {t("calibration.ratio_espera")}
          </dt>
          <dd className="font-fig text-[12px] tabular-nums text-[var(--ink)]">
            {fmtRazon(rEspera)}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[11px] text-[var(--ink-2)]">
            {t("calibration.ratio_acceso")}
          </dt>
          <dd className="font-fig text-[12px] tabular-nums text-[var(--ink)]">
            {fmtRazon(rAcceso)}
          </dd>
        </div>
        <div className="flex items-baseline justify-between gap-2">
          <dt className="text-[11px] text-[var(--ink-2)]">
            {t("calibration.ratio_caminata")}
          </dt>
          <dd className="font-fig text-[12px] tabular-nums text-[var(--ink)]">
            {fmtRazon(rCaminata)}
          </dd>
        </div>
      </dl>
      <p className="mt-1.5 text-[10px] leading-snug text-muted">
        {t("calibration.ratio_hint")}
      </p>
      {betas.b_costo >= 0 && (
        <p
          className="mt-1.5 text-[10px] leading-snug"
          style={{ color: "var(--accent)" }}
        >
          {t("calibration.b_costo_warn")}
        </p>
      )}

      <Grupo title={t("calibration.g_asc")} hint={t("calibration.g_asc_hint")}>
        {ASC_KEYS.map((k) => (
          <NumberField
            key={k}
            label={t(`calibration.p.${k}`)}
            value={betas[k]}
            step={STEP[k]}
            onChange={(v) => setBeta({ [k]: v } as Partial<StratumBetas>)}
          />
        ))}
      </Grupo>

      <Grupo
        title={t("calibration.g_tiempo")}
        hint={t("calibration.g_tiempo_hint")}
      >
        {TIEMPO_KEYS.map((k) => (
          <NumberField
            key={k}
            label={t(`calibration.p.${k}`)}
            value={betas[k]}
            step={STEP[k]}
            onChange={(v) => setBeta({ [k]: v } as Partial<StratumBetas>)}
          />
        ))}
      </Grupo>

      <Grupo
        title={t("calibration.g_penal")}
        hint={t("calibration.g_penal_hint")}
      >
        {PENAL_KEYS.map((k) => (
          <NumberField
            key={k}
            label={t(`calibration.p.${k}`)}
            value={betas.penalizaciones_fisicas[k]}
            step={0.01}
            onChange={(v) => setPenal({ [k]: v } as Partial<PhysicalPenalties>)}
          />
        ))}
      </Grupo>

      <Grupo title={t("calibration.g_poblacion")}>
        <NumberField
          label={t("calibration.p.prob_auto")}
          value={s.prob_auto}
          step={0.05}
          onChange={(v) => setStratum({ prob_auto: Math.min(1, Math.max(0, v)) })}
        />
        <NumberField
          label={t("calibration.p.prob_teletrabajo")}
          value={s.prob_teletrabajo}
          step={0.05}
          onChange={(v) =>
            setStratum({ prob_teletrabajo: Math.min(1, Math.max(0, v)) })
          }
        />
      </Grupo>
      <p className="mt-1.5 text-[10px] leading-snug text-muted">
        {t("calibration.prob_teletrabajo_hint")}
      </p>

      <button
        type="button"
        className="chip-toggle mt-3"
        onClick={restaurar}
        style={{ width: "100%" }}
      >
        {t("calibration.reset")}
      </button>
    </CollapsibleSection>
  );
}
