/**
 * La geometría del eje de posición, declarada una sola vez.
 *
 * Todas las figuras que dibujan «algo a lo largo de la ciudad» comparten el
 * mismo eje físico: 0 km a la izquierda, el CBD al centro, el largo total a la
 * derecha. Para que el alumno pueda recorrer la página en vertical preguntando
 * «¿qué pasa en el km 7?», una misma posición tiene que caer en la MISMA columna
 * de píxeles en todas.
 *
 * Hasta el 2026-08-17 no era así. Cada figura traía su propio margen:
 *
 *     FlowProfile          left 40 · right 10   → CBD en x 887
 *     NetworkDiagram       left 82 · right 16   → CBD en x 905
 *     ModeShareByLocation  left 34 · right 10   → CBD en x 867
 *
 * Tres geometrías para un mismo eje, con el CBD —que es la misma posición
 * física— cayendo en tres columnas distintas de la pantalla. Medido sobre la
 * corrida por defecto. El plano PRE-simulación sí declaraba el principio («ambas
 * comparten el eje de posición, así que una misma celda cae en la misma
 * columna»); se cumplía antes de simular y se perdía después.
 *
 * `left` es el mayor de los tres a propósito: `NetworkDiagram` rotula sus bandas
 * con el nombre del modo («BICICLETA») a la izquierda del área de datos y
 * necesita ese ancho. Las otras figuras usan ese espacio para números alineados
 * a la derecha (`textAnchor="end"` pegado al borde del área), así que el ancho
 * extra no se ve como hueco: se ve como alineación.
 *
 * Si alguna figura necesita un margen distinto, la respuesta correcta casi
 * siempre es cambiar ESTA constante —y que todas la sigan— y no volver a
 * declarar uno local.
 */
export const EJE_ESPACIAL = {
  /** Espacio para las etiquetas del eje Y y los rótulos de banda. */
  left: 82,
  /** Aire a la derecha para que la última barra no toque el borde. */
  right: 16,
} as const;

/**
 * Ancho útil del área de datos para un contenedor de `W` píxeles.
 *
 * Nunca baja de 1 para no producir escalas negativas cuando el contenedor
 * todavía no fue medido (el primer render con `ResizeObserver` da 0).
 */
export function anchoDatos(W: number): number {
  return Math.max(1, W - EJE_ESPACIAL.left - EJE_ESPACIAL.right);
}
