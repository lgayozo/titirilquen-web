/**
 * Una ecuación renderizada con KaTeX, en bloque o en línea.
 *
 * Estaba dentro de `TeoriaAprendizaje`; sale acá porque la tabla de agregados
 * necesita exactamente lo mismo y duplicar el envoltorio de KaTeX garantizaba
 * que las dos se fueran separando.
 *
 * `throwOnError: false` deja ver el fuente LaTeX si algo falla, en vez de
 * romper la página entera: una fórmula mal escrita no debe costar la vista.
 */

import katex from "katex";
import { useMemo } from "react";

export function Formula({ tex }: { tex: string }) {
  const html = useMemo(
    () => katex.renderToString(tex, { throwOnError: false, displayMode: true }),
    [tex],
  );
  return (
    <div
      className="teoria-formula"
      // El HTML lo produce KaTeX a partir de una constante del módulo: no hay
      // entrada de usuario en juego.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export function Simbolo({ tex }: { tex: string }) {
  const html = useMemo(
    () =>
      katex.renderToString(tex, { throwOnError: false, displayMode: false }),
    [tex],
  );
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}
