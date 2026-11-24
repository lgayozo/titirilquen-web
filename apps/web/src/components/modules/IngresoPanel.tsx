/**
 * El ingreso mensual de cada estrato, y por qué no ordena la ciudad.
 *
 * Vivía como un deslizador DESHABILITADO dentro de «Estrato · puja», en Uso de
 * suelo: se veía como un control roto y la pregunta volvía una y otra vez
 * («¿por qué el ingreso no se mueve?»). Acá se puede editar, y la respuesta
 * está escrita al lado, a la vista y no plegada.
 *
 * La respuesta corta: en la puja `w = y + (f − u)/λ` el ingreso es una
 * constante del estrato, igual en todas las parcelas, y la utilidad de reserva
 * `u` se ajusta hasta ubicar a todos sus hogares; cualquier cambio de `y` lo
 * absorbe `u` y ninguna puja cambia. Lo que sí mueve es la carga mensual de
 * transporte (costo / ingreso) de Ciudad en equilibrio.
 *
 * Edita `LandUseConfig.estratos[h].y`: el dato sigue viviendo donde vivía.
 */

import { useTranslation } from "react-i18next";

import { NumberField } from "@/components/modules/CalibrationPanel";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { Formula } from "@/components/ui/Formula";
import { fmtDecimal } from "@/lib/modos";
import type { LandUseConfig } from "@/lib/types-v2";

const STR = ["alto", "medio", "bajo"] as const;

interface Props {
  config: LandUseConfig;
  /** El `setConfig` del store de suelo. */
  onChange: (updater: (prev: LandUseConfig) => LandUseConfig) => void;
}

export function IngresoPanel({ config, onChange }: Props) {
  const { t } = useTranslation("simulator");
  const setIngreso = (idx: 0 | 1 | 2, y: number) =>
    onChange((prev) => {
      const estratos = [...prev.estratos] as LandUseConfig["estratos"];
      // El núcleo exige ingreso positivo.
      estratos[idx] = { ...estratos[idx], y: Math.max(1, y) };
      return { ...prev, estratos };
    });

  return (
    <CollapsibleSection
      title={t("ingreso.titulo")}
      meta={config.estratos
        .map((e) => `$${fmtDecimal(e.y / 1_000_000)}M`)
        .join(" · ")}
    >
      <div className="flex flex-col gap-1.5">
        {([0, 1, 2] as const).map((i) => (
          <NumberField
            key={i}
            label={t("ingreso.campo", { estrato: t(`strata.${STR[i]}`) })}
            value={config.estratos[i].y}
            step={50_000}
            onChange={(v) => setIngreso(i, v)}
          />
        ))}
      </div>

      <p className="mt-3 text-etiqueta font-semibold leading-snug text-[var(--ink)]">
        {t("ingreso.pregunta")}
      </p>
      <p className="mt-1 text-etiqueta leading-snug text-muted">
        {t("ingreso.respuesta")}
      </p>
      <Formula
        tex={String.raw`w_{hi} \;=\; y_h \;+\; \frac{f_h(z_i) - u_h}{\lambda_h}`}
      />
      <ul className="mt-1 list-disc pl-4 text-etiqueta leading-snug text-muted">
        <li>{t("ingreso.paso_constante")}</li>
        <li>{t("ingreso.paso_reserva")}</li>
        <li>{t("ingreso.paso_orden")}</li>
      </ul>
      <p className="mt-2 text-etiqueta leading-snug text-[var(--ink)]">
        {t("ingreso.donde_importa")}
      </p>
    </CollapsibleSection>
  );
}
