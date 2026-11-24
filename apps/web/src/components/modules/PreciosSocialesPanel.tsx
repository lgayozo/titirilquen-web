/**
 * Los precios sociales del SNI, editables.
 *
 * Se publican cada año (MDSF, «Precios Sociales — reporte anual»), así que no
 * pueden vivir en el código: son un bloque de la configuración
 * (`config.precios_sociales`) que viaja con el escenario. Actualizarlos es
 * escribir acá los valores del reporte nuevo y cambiar el año.
 *
 * Entran sólo a la EVALUACIÓN —costo de recursos, costo generalizado social y
 * excedente con ponderación social—, nunca a la elección de modo: cambiarlos
 * no mueve el equilibrio, pero sí obliga a volver a simular, porque los
 * agregados los calcula el núcleo al cerrar la corrida.
 */

import { useTranslation } from "react-i18next";

import { NumberField } from "@/components/modules/CalibrationPanel";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { PorQue } from "@/components/ui/PorQue";
import { defaultSimulationConfig } from "@/lib/defaults";
import type { SimulationConfig } from "@/lib/types";

type Precios = SimulationConfig["precios_sociales"];

/** Campo y paso del control, en el orden del reporte. */
const CAMPOS: readonly (readonly [keyof Precios, number])[] = [
  ["vigencia", 1],
  ["vst_viaje_clp_h", 1],
  ["ponderador_espera", 0.1],
  ["ponderador_caminata", 0.1],
  ["combustible_auto_clp_l", 1],
  ["lubricante_auto_clp_l", 1],
  ["neumatico_auto_clp", 1],
  ["vehiculo_auto_clp", 1000],
  ["mantencion_clp_h", 1],
  ["carbono_clp_t", 1],
  ["tasa_social_descuento", 0.005],
  ["iri", 0.5],
];

/** Topes que el núcleo exige además de «no negativo». */
const MAXIMO: Partial<Record<keyof Precios, number>> = {
  iri: 20,
  tasa_social_descuento: 1,
};

interface Props {
  config: SimulationConfig;
  /** El `setConfig` del store: recibe una función sobre la config previa. */
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
}

export function PreciosSocialesPanel({ config, onChange }: Props) {
  const { t } = useTranslation("simulator");
  const precios = config.precios_sociales;
  // Los de fábrica salen del núcleo (`constantes.py` → contrato generado), no
  // de este archivo: cuando se actualicen allá, el botón los sigue.
  const deFabrica = defaultSimulationConfig.precios_sociales;
  const esDeFabrica = JSON.stringify(precios) === JSON.stringify(deFabrica);
  return (
    <CollapsibleSection
      title={t("precios_sociales.titulo")}
      meta={String(precios.vigencia)}
    >
      <p className="mb-2 text-etiqueta leading-snug text-muted">
        {t("precios_sociales.corto")}
      </p>
      <div className="flex flex-col gap-1.5">
        {CAMPOS.map(([campo, paso]) => (
          <NumberField
            key={campo}
            label={t(`precios_sociales.campo.${campo}`)}
            value={precios[campo]}
            step={paso}
            onChange={(v) =>
              onChange((c) => ({
                ...c,
                // Ninguno puede ser negativo: el núcleo lo rechazaría.
                precios_sociales: {
                  ...c.precios_sociales,
                  [campo]: Math.min(MAXIMO[campo] ?? Infinity, Math.max(0, v)),
                },
              }))
            }
          />
        ))}
      </div>
      <button
        type="button"
        className="chip-toggle mt-2 w-full"
        disabled={esDeFabrica}
        onClick={() => onChange((c) => ({ ...c, precios_sociales: deFabrica }))}
      >
        {t("precios_sociales.restablecer", { anio: deFabrica.vigencia })}
      </button>
      <PorQue>{t("precios_sociales.porque")}</PorQue>
    </CollapsibleSection>
  );
}
