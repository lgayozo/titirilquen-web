import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { densidadDerivadaHabKm } from "@/lib/citySupply";
import type { SimulationConfig } from "@/lib/types";
import { useLandUseStore } from "@/store/landUseStore";

interface CityBuilderProps {
  config: SimulationConfig;
  onChange: (updater: (prev: SimulationConfig) => SimulationConfig) => void;
}

export function CityBuilder({ config, onChange }: CityBuilderProps) {
  const { t } = useTranslation("simulator");
  // La población (ΣH) es el input; la densidad se deriva de ella y del largo.
  const sumaH = useLandUseStore((s) =>
    s.config.H_por_estrato.reduce((a, b) => a + b, 0),
  );

  const setCity = (patch: Partial<SimulationConfig["city"]>) =>
    onChange((c) => ({ ...c, city: { ...c.city, ...patch } }));

  return (
    <>
      <CollapsibleSection
        title={t("sections.city")}
        meta={t("city_params.meta", {
          km: config.city.largo_ciudad_km,
          n: config.city.n_celdas,
        })}
      >
        <LabeledSlider
          label={t("city_params.largo_ciudad_km")}
          value={config.city.largo_ciudad_km}
          min={5}
          max={40}
          step={1}
          unit="km"
          hint={t("city_params.largo_hint", {
            pob: sumaH.toLocaleString("es-CL"),
            rho: densidadDerivadaHabKm(
              sumaH,
              config.city.largo_ciudad_km,
            ).toLocaleString("es-CL"),
          })}
          onChange={(v) =>
            // Cambiar el largo con población fija ⇒ la densidad se recalcula.
            setCity({
              largo_ciudad_km: v,
              densidad_hab_km: densidadDerivadaHabKm(sumaH, v),
            })
          }
        />
        <LabeledSlider
          label={t("city_params.n_parcelas")}
          value={config.city.n_celdas}
          min={51}
          max={1001}
          step={50}
          hint={t("city_params.n_parcelas_hint", {
            dx: Math.round(
              (config.city.largo_ciudad_km / config.city.n_celdas) * 1000,
            ),
          })}
          onChange={(v) => setCity({ n_celdas: v % 2 === 0 ? v + 1 : v })}
        />
        <LabeledSlider
          label={t("city_params.pendiente_porcentaje")}
          value={config.city.pendiente_porcentaje}
          min={-10}
          max={10}
          step={0.5}
          unit="%"
          hint={t("city_params.pendiente_hint")}
          onChange={(v) => setCity({ pendiente_porcentaje: v })}
        />
        {/* El factor de teletrabajo NO está acá: vive en «Economía», dentro de
            Transporte. Es una política de gestión de demanda —saca viajes de la
            punta— y no un atributo de la forma urbana, así que estaba a una
            página de distancia de las otras palancas (tarifa, parking, pistas).
            El campo del schema sigue siendo `city.teletrabajo_factor`; lo que se
            movió es dónde se edita. */}
      </CollapsibleSection>
    </>
  );
}
