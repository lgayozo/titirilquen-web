/**
 * Los costos unitarios de la infraestructura, editables.
 *
 * Existen para que ampliar oferta no sea gratis: sin ellos, toda política que
 * agrega capacidad —una pista, veinte estaciones, el doble de ciclovía, una
 * flota híbrida— gana siempre, porque sus beneficios se cuentan y su costo no.
 *
 * **Parten en cero.** No hay una fuente para estos valores en `reference/`, y
 * un número plausible inventado sería peor que declarar el vacío. Con ceros
 * los resultados son los de siempre; se llenan acá con un dato.
 *
 * Como los precios sociales, son calibración: los presets los conservan y
 * viajan con el escenario. Entran sólo a la evaluación (costo de recursos y
 * bienestar social), no a la elección de modo.
 */

import { useTranslation } from "react-i18next";

import { NumberField } from "@/components/modules/CalibrationPanel";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { PorQue } from "@/components/ui/PorQue";
import type { SimulationConfig } from "@/lib/types";

type Inversion = SimulationConfig["inversion"];

/** Campo, paso del control y mínimo que exige el núcleo. */
const CAMPOS: readonly (readonly [keyof Inversion, number, number])[] = [
  ["costo_pista_km_clp", 100_000_000, 0],
  ["costo_estacion_clp", 1_000_000_000, 0],
  ["costo_ciclovia_km_clp", 10_000_000, 0],
  ["sobrecosto_flota_limpia_clp", 500_000, 0],
  ["vida_util_anios", 1, 1],
  ["horas_punta_anio", 50, 1],
];

const COSTOS: readonly (keyof Inversion)[] = [
  "costo_pista_km_clp",
  "costo_estacion_clp",
  "costo_ciclovia_km_clp",
  "sobrecosto_flota_limpia_clp",
];

interface Props {
  config: SimulationConfig;
  /** El `setConfig` del store: recibe una función sobre la config previa. */
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
}

export function InversionPanel({ config, onChange }: Props) {
  const { t } = useTranslation("simulator");
  const inv = config.inversion;
  const sinCostos = COSTOS.every((k) => inv[k] === 0);
  return (
    <CollapsibleSection
      title={t("inversion.titulo")}
      meta={sinCostos ? t("inversion.sin_costos") : t("inversion.con_costos")}
    >
      <p className="mb-2 text-etiqueta leading-snug text-muted">
        {t("inversion.corto")}
      </p>
      {sinCostos && (
        <p
          className="mb-2 text-etiqueta leading-snug text-[var(--alerta)]"
          role="status"
        >
          {t("inversion.aviso_cero")}
        </p>
      )}
      <div className="flex flex-col gap-1.5">
        {CAMPOS.map(([campo, paso, minimo]) => (
          <NumberField
            key={campo}
            label={t(`inversion.campo.${campo}`)}
            value={inv[campo]}
            step={paso}
            onChange={(v) =>
              onChange((c) => ({
                ...c,
                inversion: { ...c.inversion, [campo]: Math.max(minimo, v) },
              }))
            }
          />
        ))}
      </div>
      <PorQue>{t("inversion.porque")}</PorQue>
    </CollapsibleSection>
  );
}
