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
 * vecina, en la misma pantalla.
 */

import {
  CORTE_BICI_MIN,
  CORTE_CAMINATA_MIN,
  MODOS,
  MODOS_CON_TELETRABAJO,
} from "@/lib/gen/constantes.gen";
import type { Modo } from "@/lib/types";

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
 * porque el simulador tiene tres temas: la definición vive en `index.css`.
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

/** El locale es FIJO. Ver la nota del encabezado: con el del navegador, dos
 *  figuras vecinas mostraban la misma cifra con separadores distintos. */
const LOCALE = "es-CL";

/** Entero con separador de miles: 36000 → «36.000». */
export const fmtEntero = (v: number): string =>
  Math.round(v).toLocaleString(LOCALE);

/** Pesos, con el signo ANTES del símbolo: −$3.331, no $-3.331. */
export const fmtPesos = (v: number): string =>
  `${v < 0 ? "−" : ""}$${Math.round(Math.abs(v)).toLocaleString(LOCALE)}`;

/** Porcentaje con un decimal. */
export const fmtPct = (v: number, decimales = 1): string =>
  `${v.toFixed(decimales)}%`;

/** Minutos: un decimal bajo 10, entero por encima — para que las columnas de
 *  una tabla no bailen de ancho. */
export const fmtMinutos = (v: number): string =>
  `${v >= 10 ? v.toFixed(0) : v.toFixed(1)} min`;

/** Número con la precisión que su magnitud justifica. */
export const fmtNumero = (v: number, umbral = 10): string =>
  v >= umbral ? v.toFixed(0) : v.toFixed(1);
