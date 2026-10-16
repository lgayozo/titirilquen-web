import { useTranslation } from "react-i18next";

import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { PorQue } from "@/components/ui/PorQue";
import { defaultLandUseConfig } from "@/lib/defaults";
import type { LandUseConfig } from "@/lib/types-v2";

interface LandUseBuilderProps {
  config: LandUseConfig;
  onChange: (updater: (prev: LandUseConfig) => LandUseConfig) => void;
  /** Largo de la ciudad (km), para el total de población derivado. */
  largoKm: number;
  /** λ_h = |b_costo_h| de la demanda (alto, medio, bajo): sólo se muestra. */
  lambdas: readonly [number, number, number];
}

const pct = (v: number) => `${(v * 100).toFixed(0)}%`;

// Tres ciudades de contraste para μ. Medidas a flujo libre con ρ = 0 (oct-2026):
// mezclada Theil 0,12 y el alto a 2,4 km del CBD; base 0,39 y 1,4 km;
// segregada 0,70 y 0,85 km. La base es el default del núcleo.
const MU_PRESETS = [
  { key: "mezclada", mu: 0.1 },
  { key: "base", mu: defaultLandUseConfig.mu },
  { key: "segregada", mu: 0.8 },
] as const;

export function LandUseBuilder({
  config,
  onChange,
  largoKm,
  lambdas,
}: LandUseBuilderProps) {
  const { t } = useTranslation("simulator");

  // λ_h = |b_costo_h| no es parte de esta config (schema v6): el núcleo lo
  // deriva de la demanda, y se mueve desde la calibración de Transporte, junto
  // con la accesibilidad T que también depende de b_costo (D-41). α tampoco
  // (schema v7, D1 de la auditoría): la accesibilidad entra con peso 1. Las
  // palancas de preferencias de acá son μ (`config.mu`, valor de escenario
  // desde v10, común a los estratos) y ρ, por estrato.
  const fmtLambda = (v: number) => `${(v * 1e4).toFixed(2)}·10⁻⁴`;

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

  const labels = [
    t("strata.alto"),
    t("strata.medio"),
    t("strata.bajo"),
  ] as const;

  return (
    <>
      {/* ---- POBLACIÓN: proporciones (mezcla) + densidad por estrato ---- */}
      <CollapsibleSection
        title={t("land_use.section_poblacion")}
        meta={`≈ ${Math.round(totalH).toLocaleString("es-CL")}`}
      >
        <div className="mb-1 font-fig text-etiqueta uppercase tracking-[0.08em] text-muted">
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
        <div className="text-etiqueta text-muted">
          {labels[2]}: {pct(pi[2])} ({t("strata.auto_calculated")})
        </div>

        <div className="mb-1 mt-3 font-fig text-etiqueta uppercase tracking-[0.08em] text-muted">
          {t("land_use.densidad_media_label")}
        </div>
        <LabeledSlider
          label={t("land_use.densidad_media")}
          value={densMedia}
          min={100}
          // 3000: aire sobre el default 1800 (preset Base). Compacta (4200) se
          // aplica por preset, no por slider.
          max={3000}
          step={50}
          unit="hab/km"
          onChange={setDensidadMedia}
        />

        <p className="mt-2 text-etiqueta text-muted">
          {t("land_use.poblacion_total_corto", {
            total: Math.round(totalH).toLocaleString("es-CL"),
            dens: Math.round(densMedia),
          })}
        </p>
        <PorQue>{t("land_use.poblacion_total_porque")}</PorQue>
      </CollapsibleSection>

      {/* ---- FORMA DE LA CIUDAD: perfil de oferta de vivienda ---- */}
      <CollapsibleSection
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
        <p className="mt-1 text-etiqueta text-muted">
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
        <p className="-mt-1 text-etiqueta text-muted">
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
      </CollapsibleSection>

      {/* ---- PARÁMETROS DE PUJA (bid-rent): μ se mueve; λ sólo se muestra (D-41) ---- */}
      <CollapsibleSection
        title={t("land_use.section_bidrent")}
        meta={`μ=${config.mu.toFixed(2)}`}
        defaultOpen
      >
        <p className="text-etiqueta text-muted">
          {t("land_use.bidrent_corto")}
        </p>
        <PorQue className="mb-2">{t("land_use.bidrent_porque")}</PorQue>
        <LabeledSlider
          label={t("land_use.param_mu")}
          value={config.mu}
          min={0.05}
          max={1}
          step={0.05}
          format={(v) => v.toFixed(2)}
          hint={t("land_use.mu_corto")}
          onChange={(v) => onChange((c) => ({ ...c, mu: v }))}
        />
        <div className="mt-1 flex gap-1.5">
          {MU_PRESETS.map((p) => (
            <button
              key={p.key}
              type="button"
              className={`chip-toggle${Math.abs(config.mu - p.mu) < 1e-9 ? " active" : ""}`}
              style={{ flex: 1 }}
              onClick={() => onChange((c) => ({ ...c, mu: p.mu }))}
            >
              {t(`land_use.mu_preset_${p.key}`, { mu: p.mu.toFixed(2) })}
            </button>
          ))}
        </div>
        <PorQue>{t("land_use.mu_porque")}</PorQue>
        <p className="mt-1 text-etiqueta text-muted">
          {t("land_use.lambda_values_corto", {
            l1: fmtLambda(lambdas[0]),
            l2: fmtLambda(lambdas[1]),
            l3: fmtLambda(lambdas[2]),
          })}
        </p>
        <PorQue>{t("land_use.lambda_values_porque")}</PorQue>
      </CollapsibleSection>

      {[0, 1, 2].map((i) => {
        const idx = i as 0 | 1 | 2;
        const s = config.estratos[idx];
        return (
          <CollapsibleSection
            key={i}
            title={`${labels[idx]} · ${t("land_use.section_bidrent_short")}`}
            meta={`ρ=${s.rho.toFixed(0)}`}
            defaultOpen={false}
          >
            <LabeledSlider
              label={t("land_use.param_rho")}
              value={s.rho}
              min={0}
              max={60}
              step={1}
              format={(v) => v.toFixed(0)}
              hint={t("land_use.rho_corto")}
              onChange={(v) => setStratum(idx, { rho: v })}
            />
            <PorQue>{t("land_use.rho_porque")}</PorQue>
            <LabeledSlider
              label={t("land_use.param_y")}
              value={s.y}
              min={100_000}
              max={10_000_000}
              step={100_000}
              format={(v) => `$${(v / 1_000_000).toFixed(1)}M`}
              disabled
              hint={t("land_use.y_na_corto")}
              onChange={(v) => setStratum(idx, { y: v })}
            />
            <PorQue>{t("land_use.y_na_porque")}</PorQue>
          </CollapsibleSection>
        );
      })}
    </>
  );
}
