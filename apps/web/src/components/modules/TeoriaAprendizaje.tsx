/**
 * El modelo del módulo de aprendizaje, con sus ecuaciones y sus indicadores.
 *
 * No es decoración: sin saber qué es cada símbolo, Φ = 1,01 o Δ* = 39,8 min no
 * dicen nada. Cada ecuación viene con el significado de sus componentes, y las
 * de ciudad se marcan como tales porque sólo existen cuando aprende la
 * población entera.
 *
 * El LaTeX NO se traduce (es notación); lo traducido es la prosa.
 */

import { useTranslation } from "react-i18next";

import { Formula, Simbolo } from "@/components/ui/Formula";

interface Bloque {
  /** Clave de i18n bajo `aprendizaje.teoria.`. */
  id: string;
  /** Sólo aparece en el modo ciudad: no tiene sentido con una persona. */
  soloCiudad?: boolean;
  ecuaciones: string[];
  /** [símbolo en LaTeX, clave del significado]. */
  simbolos: [string, string][];
}

const BLOQUES: Bloque[] = [
  {
    id: "percibido",
    ecuaciones: [
      String.raw`b_{ni}(t) \;=\; \sum_{t' < t} w_{ni}(t', t)\, x_{ni}(t')`,
      String.raw`w_{ni}(t', t) \;=\; \frac{a_{ni}(t')\,(t - t')^{-d}}{\sum_{s < t} a_{ni}(s)\,(t - s)^{-d}}`,
    ],
    simbolos: [
      [String.raw`b_{ni}(t)`, "b"],
      [String.raw`x_{ni}(t')`, "x"],
      [String.raw`a_{ni}(t')`, "a"],
      [String.raw`w_{ni}(t', t)`, "w"],
      ["d", "d"],
    ],
  },
  {
    id: "eleccion",
    ecuaciones: [
      String.raw`V_{ni}(t) \;=\; \bar V_i \;+\; \beta\,\bigl(b_{ni}(t) - \tau_i\bigr)`,
      String.raw`P_{ni}(t) \;=\; \frac{e^{\mu V_{ni}(t)}}{\sum_{j} e^{\mu V_{nj}(t)}}`,
    ],
    simbolos: [
      [String.raw`\bar V_i`, "vref"],
      [String.raw`\beta`, "beta"],
      [String.raw`\tau_i`, "tau"],
      [String.raw`\mu`, "mu"],
    ],
  },
  {
    id: "ventaja",
    ecuaciones: [
      String.raw`A \;=\; \frac{\Delta V}{|\beta|}, \qquad P^{*} \;=\; \Lambda(\Delta V)`,
    ],
    simbolos: [
      [String.raw`\Delta V`, "dv"],
      ["A", "A"],
      [String.raw`P^{*}`, "pestrella"],
      [String.raw`\Lambda(z)`, "logit"],
    ],
  },
  {
    id: "phi",
    ecuaciones: [
      String.raw`\Phi \;=\; \frac{\bar S - \overline{1/J}}{\bar P^{*} - \overline{1/J}}`,
    ],
    simbolos: [
      [String.raw`\bar S`, "S"],
      [String.raw`\overline{1/J}`, "uniforme"],
      [String.raw`\Phi`, "phi"],
    ],
  },
  {
    id: "racha",
    ecuaciones: [
      String.raw`W_k \;=\; \frac{\sum_{j=1}^{k} j^{-d}}{\sum_{j=1}^{k} j^{-d} + (k+1)^{-d}}`,
      String.raw`\Delta^{*} \;=\; \frac{A}{W_k}, \qquad P_{\text{post}} \;=\; \Lambda\bigl(\Delta V - |\beta|\,W_k\,\Delta\bigr)`,
    ],
    simbolos: [
      ["k", "k"],
      [String.raw`\Delta`, "delta"],
      ["W_k", "wk"],
      [String.raw`\Delta^{*}`, "dcritico"],
      [String.raw`P_{\text{post}}`, "ppost"],
    ],
  },
  {
    id: "dispersion",
    soloCiudad: true,
    ecuaciones: [
      String.raw`R \;=\; \frac{\operatorname{Var}\bigl(\text{cuota observada}\bigr)}{\bar p\,(1 - \bar p)\,/\,U}`,
    ],
    simbolos: [
      ["R", "R"],
      [String.raw`\bar p`, "pbarra"],
      ["U", "U"],
    ],
  },
  {
    id: "brecha",
    soloCiudad: true,
    ecuaciones: [
      String.raw`B \;=\; \frac{\mathbb{E}\bigl[V^{\text{decisión}}\bigr] - \mathbb{E}\bigl[V^{\text{experimentada}}\bigr]}{|\beta|}`,
    ],
    simbolos: [
      ["B", "B"],
      [String.raw`V^{\text{decisión}}`, "vdec"],
      [String.raw`V^{\text{experimentada}}`, "vexp"],
    ],
  },
];

export function TeoriaAprendizaje({ modo }: { modo: "persona" | "ciudad" }) {
  const { t } = useTranslation("simulator");
  const visibles = BLOQUES.filter((b) => modo === "ciudad" || !b.soloCiudad);

  return (
    <div className="teoria">
      <p className="teoria-intro">{t("aprendizaje.teoria.intro")}</p>
      {visibles.map((b) => (
        <section key={b.id} className="teoria-bloque">
          <h3>{t(`aprendizaje.teoria.${b.id}.titulo`)}</h3>
          <p>{t(`aprendizaje.teoria.${b.id}.texto`)}</p>
          {b.ecuaciones.map((e) => (
            <Formula key={e} tex={e} />
          ))}
          <dl className="teoria-glosa">
            {b.simbolos.map(([tex, clave]) => (
              <div key={clave}>
                <dt>
                  <Simbolo tex={tex} />
                </dt>
                <dd>{t(`aprendizaje.teoria.${b.id}.sim.${clave}`)}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}
