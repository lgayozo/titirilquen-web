import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { SidebarSection } from "@/components/ui/SidebarSection";
import type { LandUseConfig } from "@/lib/types-v2";

interface LandUseBuilderProps {
  config: LandUseConfig;
  onChange: (updater: (prev: LandUseConfig) => LandUseConfig) => void;
  /** Largo de la ciudad (km), para el total de población derivado. */
  largoKm: number;
}

const pct = (v: number) => `${(v * 100).toFixed(0)}%`;

export function LandUseBuilder({
  config,
  onChange,
  largoKm,
}: LandUseBuilderProps) {
  const { t } = useTranslation("simulator");

  const setStratum = (
    idx: 0 | 1 | 2,
    patch: Partial<LandUseConfig["estratos"][number]>,
  ) =>
    onChange((c) => {
      const next = [...c.estratos] as LandUseConfig["estratos"];
      next[idx] = { ...next[idx], ...patch };
      return { ...c, estratos: next };
    });


  // Proporciones π_h = H_h/ΣH (la mezcla) y ESCALA de población (ΣH). La
  // «densidad media» es una vista de la escala: densidad_media = ΣH / largo.
  // Mover la densidad reescala ΣH (y con ella la oferta S y la densidad por
  // celda = S/Δx); las proporciones fijan el reparto sin cambiar el total.
  const totalH = config.H_por_estrato.reduce((a, b) => a + b, 0) || 1;
  const pi = config.H_por_estrato.map((h) => h / totalH) as [
    number,
    number,
    number,
  ];
  const densMedia = totalH / largoKm;

  // Reescribe H con proporciones `p` y total `T` (Σ = T exacto, cada H ≥ 1).
  const writeH = (p: [number, number, number], T: number) => {
    const Ha = Math.max(1, Math.round(p[0] * T));
    const Hm = Math.max(1, Math.round(p[1] * T));
    const Hb = Math.max(1, T - Ha - Hm);
    onChange((c) => ({ ...c, H_por_estrato: [Ha, Hm, Hb] }));
  };

  const setProporciones = (a: number, m: number) => {
    const A = Math.max(0, Math.min(1, a));
    const M = Math.max(0, Math.min(1 - A, m));
    writeH([A, M, 1 - A - M], totalH);
  };

  // T = densidad_media · largo, ≥ 3 para garantizar ≥1 hogar por estrato.
  const setDensidadMedia = (dm: number) =>
    writeH(pi, Math.max(3, Math.round(dm * largoKm)));

  const labels = [t("strata.alto"), t("strata.medio"), t("strata.bajo")] as const;

  return (
    <>
      {/* ---- POBLACIÓN: proporciones (mezcla) + densidad por estrato ---- */}
      <SidebarSection
        title={t("land_use.section_poblacion")}
        meta={`≈ ${Math.round(totalH).toLocaleString()}`}
      >
        <div className="mb-1 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
          {t("land_use.proporciones")}
        </div>
        <LabeledSlider
          label={labels[0]}
          value={pi[0]}
          min={0}
          max={1}
          step={0.05}
          format={pct}
          onChange={(v) => setProporciones(v, pi[1])}
        />
        <LabeledSlider
          label={labels[1]}
          value={pi[1]}
          min={0}
          max={1 - pi[0]}
          step={0.05}
          format={pct}
          onChange={(v) => setProporciones(pi[0], v)}
        />
        <div className="text-[11px] text-muted">
          {labels[2]}: {pct(pi[2])} ({t("strata.auto_calculated")})
        </div>

        <div className="mb-1 mt-3 font-fig text-[10px] uppercase tracking-[0.08em] text-muted">
          {t("land_use.densidad_media_label")}
        </div>
        <LabeledSlider
          label={t("land_use.densidad_media")}
          value={densMedia}
          min={100}
          max={1500}
          step={50}
          unit="hab/km"
          onChange={setDensidadMedia}
        />

        <p className="mt-2 text-[10px] text-muted">
          {t("land_use.poblacion_total_hint", {
            total: Math.round(totalH).toLocaleString(),
            dens: Math.round(densMedia),
          })}
        </p>
      </SidebarSection>

      {/* ---- FORMA DE LA CIUDAD: perfil de oferta de vivienda ---- */}
      <SidebarSection
        title={t("land_use.section_forma")}
        meta={t(`land_use.forma_${config.forma}`)}
      >
        <div className="flex flex-wrap gap-1.5">
          {(
            [
              "normal",
              "uniforme",
              "exponencial",
              "meseta",
              "bimodal",
              "valle",
            ] as const
          ).map((f) => (
            <button
              key={f}
              type="button"
              className={`chip-toggle${config.forma === f ? " active" : ""}`}
              onClick={() => onChange((c) => ({ ...c, forma: f }))}
            >
              {t(`land_use.forma_${f}`)}
            </button>
          ))}
        </div>
        <p className="mt-1 text-[10px] text-muted">
          {t(`land_use.forma_hint_${config.forma}`)}
        </p>

        <LabeledSlider
          label={t("land_use.param_oferta_sigma")}
          value={config.oferta_sigma_frac}
          min={0.1}
          max={1.5}
          step={0.05}
          disabled={config.forma === "uniforme"}
          onChange={(v) => onChange((c) => ({ ...c, oferta_sigma_frac: v }))}
        />
        <p className="-mt-1 text-[10px] text-muted">
          {config.forma === "uniforme"
            ? t("land_use.oferta_sigma_na")
            : t("land_use.oferta_sigma_hint")}
        </p>

        {config.forma === "bimodal" && (
          <LabeledSlider
            label={t("land_use.param_separacion")}
            value={config.forma_param}
            min={0.1}
            max={1}
            step={0.05}
            onChange={(v) => onChange((c) => ({ ...c, forma_param: v }))}
          />
        )}
      </SidebarSection>

      {/* ---- PARÁMETROS DE PUJA (bid-rent): sensibilidades del estrato ---- */}
      <SidebarSection
        title={t("land_use.section_bidrent")}
        meta={`β=${config.beta.toFixed(1)}`}
        defaultOpen={false}
      >
        <LabeledSlider
          label={t("land_use.param_beta")}
          value={config.beta}
          min={0.1}
          max={5}
          step={0.1}
          onChange={(v) => onChange((c) => ({ ...c, beta: v }))}
        />
        <p className="mt-1 text-[10px] text-muted">
          {t("land_use.bidrent_hint")}
        </p>
      </SidebarSection>

      {[0, 1, 2].map((i) => {
        const idx = i as 0 | 1 | 2;
        const s = config.estratos[idx];
        return (
          <SidebarSection
            key={i}
            title={`${labels[idx]} · ${t("land_use.section_bidrent_short")}`}
            meta={`α=${s.alpha}`}
            defaultOpen={false}
          >
            <LabeledSlider
              label={t("land_use.param_alpha")}
              value={s.alpha}
              min={0.5}
              max={20}
              step={0.25}
              onChange={(v) => setStratum(idx, { alpha: v })}
            />
            <LabeledSlider
              label={t("land_use.param_rho")}
              value={s.rho}
              min={0}
              max={0.5}
              step={0.01}
              onChange={(v) => setStratum(idx, { rho: v })}
            />
            <LabeledSlider
              label={t("land_use.param_y")}
              value={s.y}
              min={100_000}
              max={10_000_000}
              step={100_000}
              format={(v) => `$${(v / 1_000_000).toFixed(1)}M`}
              disabled
              hint={t("land_use.y_na")}
              onChange={(v) => setStratum(idx, { y: v })}
            />
            <LabeledSlider
              label={t("land_use.param_lambda")}
              value={s.lambda}
              min={0.1}
              max={3}
              step={0.05}
              hint={t("land_use.lambda_artifact_logit")}
              onChange={(v) => setStratum(idx, { lambda: v })}
            />
          </SidebarSection>
        );
      })}
    </>
  );
}
