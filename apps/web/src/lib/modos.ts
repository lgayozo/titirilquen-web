/**
 * Los modos y cómo se muestran: orden, color y formato de cifras.
 *
 * Todo esto estaba declarado en cada figura que lo necesitaba — el mapa de
 * colores en siete archivos, el orden en seis— y las copias habían DIVERGIDO:
 * una figura ordenaba al revés, otra incluía «Varado» y otra no, y en
 * `SandboxPage` el mapa se reconstruía en cada render dentro de un `useMemo`.
 * El efecto visible es que la leyenda no significaba lo mismo de un gráfico al
 * de al lado.
 *
 * Los formateadores tenían un problema peor y más silencioso: 26 llamadas a
 * `toLocaleString()` **sin locale**, que usa el del navegador. En un navegador
 * en inglés la misma cifra salía «36,000» en una figura y «36.000» en la
 * vecina, en la misma pantalla. Después se fijó «es-CL» para los miles, pero
 * los decimales seguían saliendo de `toFixed` (siempre con punto): «36.000» al
 * lado de «24.7%». Ahora el locale de TODAS las cifras sale del idioma de la
 * interfaz (`localeCifras`), no del navegador: en español «36.000 · 24,7 %»,
 * en inglés «36,000 · 24.7%», y nunca las dos convenciones en una pantalla.
 */

import i18n from "i18next";

import {
  CORTE_BICI_MIN,
  CORTE_CAMINATA_MIN,
  MODOS,
  MODOS_CON_TELETRABAJO,
} from "@/lib/gen/constantes.gen";
import type { Modo, StratumId } from "@/lib/types";

export { CORTE_BICI_MIN, CORTE_CAMINATA_MIN, MODOS, MODOS_CON_TELETRABAJO };

/** Todo lo que puede aparecer en un reparto, incluido quien no viajó. */
export type CategoriaModal = Modo | "Varado";

/**
 * Orden canónico de las series. Es el mismo del núcleo (`constantes.MODOS`),
 * que además define el layout del cubo `demanda_estrato`: alterarlo acá
 * desalinearía las figuras respecto de los datos.
 */
export const ORDEN_MODOS: readonly Modo[] =
  MODOS_CON_TELETRABAJO as readonly Modo[];

/** Ídem incluyendo a los varados — sólo el módulo acoplado los reporta. */
export const ORDEN_CON_VARADO: readonly CategoriaModal[] = [
  ...MODOS_CON_TELETRABAJO,
  "Varado",
] as CategoriaModal[];

/**
 * Color de cada categoría. Los valores son variables CSS y no colores literales
 * porque el simulador tiene dos temas: la definición vive en `index.css`.
 */
export const COLOR_MODO: Record<CategoriaModal, string> = {
  Auto: "var(--auto)",
  Metro: "var(--metro)",
  Bici: "var(--bici)",
  Caminata: "var(--walk)",
  Teletrabajo: "var(--tele)",
  Varado: "var(--muted)",
};

/** La misma tabla con las claves en minúscula, para los componentes que
 *  identifican el modo por su clave de traducción y no por su nombre. */
export const COLOR_MODO_MINUSCULA: Record<string, string> = {
  auto: COLOR_MODO.Auto,
  metro: COLOR_MODO.Metro,
  bici: COLOR_MODO.Bici,
  caminata: COLOR_MODO.Caminata,
  teletrabajo: COLOR_MODO.Teletrabajo,
};

/** Color de cada estrato (1 = alto). Vive acá, junto al de los modos, para
 *  que haya un solo mapa por familia de variables: antes cada figura de
 *  estratos declaraba el suyo. */
export const COLOR_ESTRATO: Record<StratumId, string> = {
  1: "var(--s1)",
  2: "var(--s2)",
  3: "var(--s3)",
};

/**
 * Sobre estos tiempos el modo deja de ser una alternativa considerada (min).
 * Vienen del núcleo: son supuestos del modelo de elección, no de la figura.
 */
export const CORTE_POR_MODO: Partial<Record<string, number>> = {
  caminata: CORTE_CAMINATA_MIN,
  bici: CORTE_BICI_MIN,
};

// ---------------------------------------------------------------------------
// Formato de cifras
// ---------------------------------------------------------------------------

/** Locale de las cifras: el del idioma de la interfaz, no el del navegador
 *  (ver la nota del encabezado). Es una función y no una constante porque el
 *  idioma cambia en caliente con el selector. */
export const localeCifras = (): string =>
  i18n.resolvedLanguage === "en" ? "en-US" : "es-CL";

/** `Intl.NumberFormat` es caro de construir: uno por locale y precisión. */
const formatos = new Map<string, Intl.NumberFormat>();

/** Número con `decimales` fijos y los separadores del idioma activo:
 *  24.71 → «24,7» (es) · «24.7» (en). El signo negativo es «−» (U+2212),
 *  el mismo de `fmtPesos`, y un −0,04 redondeado no sale «−0,0». */
export const fmtDecimal = (v: number, decimales = 1): string => {
  const locale = localeCifras();
  const clave = `${locale}|${decimales}`;
  let f = formatos.get(clave);
  if (!f) {
    f = new Intl.NumberFormat(locale, {
      minimumFractionDigits: decimales,
      maximumFractionDigits: decimales,
    });
    formatos.set(clave, f);
  }
  const r = Number(v.toFixed(decimales));
  return f.format(r === 0 ? 0 : r).replace("-", "−");
};

/** Diferencia con signo explícito: «+1,2» · «−0,4» · «0,0». El signo se
 *  decide sobre el valor YA redondeado, para que un −0,04 no salga «−0,0». */
export const fmtDelta = (v: number, decimales = 1): string => {
  const s = fmtDecimal(v, decimales);
  return Number(v.toFixed(decimales)) > 0 ? `+${s}` : s;
};

/** Entero con separador de miles: 36000 → «36.000» (es) · «36,000» (en). */
export const fmtEntero = (v: number): string => fmtDecimal(v, 0);

/** Pesos, con el signo ANTES del símbolo: −$3.331, no $-3.331. */
export const fmtPesos = (v: number): string =>
  `${Math.round(v) < 0 ? "−" : ""}$${fmtEntero(Math.abs(v))}`;

/** Porcentaje: «24,7 %» en español (con espacio duro, como pide la RAE) y
 *  «24.7%» en inglés. `v` ya viene en puntos porcentuales (24.7, no 0.247). */
export const fmtPct = (v: number, decimales = 1): string =>
  `${fmtDecimal(v, decimales)}${sufijoPct()}`;

/** El \u00ab%\u00bb con o sin espacio seg\u00fan el idioma, para quien arma la cifra aparte. */
export const sufijoPct = (): string =>
  localeCifras() === "en-US" ? "%" : "\u00a0%";

/** Minutos: un decimal bajo 10, entero por encima — para que las columnas de
 *  una tabla no bailen de ancho. */
export const fmtMinutos = (v: number): string =>
  `${fmtDecimal(v, v >= 10 ? 0 : 1)} min`;

/** Número con la precisión que su magnitud justifica. */
export const fmtNumero = (v: number, umbral = 10): string =>
  fmtDecimal(v, Math.abs(v) >= umbral ? 0 : 1);
