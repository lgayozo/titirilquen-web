/**
 * Tipos de presentación que no pertenecen a ningún componente en particular.
 *
 * Varios tipos de dominio del frontend viven hoy dentro del archivo del
 * componente que los estrenó, y las páginas los importan desde ahí — un
 * acoplamiento que sobrevive al componente. Este módulo es su destino.
 */

/**
 * Una barra de una estadística agregada: categoría, valor y color.
 *
 * Nació para el componente `StatBars` (barras verticales por categoría), que
 * se retiró al reemplazarse esa figura por la tabla de resultados. La forma
 * sobrevivió porque `avgStats` la sigue usando como estructura intermedia
 * antes de armar `transportMetrics`; de ahí que conserve `color`, que una
 * tabla no necesita.
 */
export interface StatBar {
  label: string;
  value: number;
  color: string;
}
