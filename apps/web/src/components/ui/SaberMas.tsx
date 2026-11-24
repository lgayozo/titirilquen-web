/**
 * La etiqueta de una métrica, que se abre para mostrar de dónde sale la cifra:
 * por qué se mide, con qué ecuación, y dónde se calcula en el núcleo.
 *
 * **Por qué envuelve la etiqueta en vez de ir debajo.** La primera versión
 * ponía un «+ saber más» en su propia línea bajo cada fila, y con veinte
 * métricas eso repetía el mismo rótulo veinte veces y duplicaba el alto de la
 * tabla. Acá la etiqueta ES el `<summary>`: cerrada ocupa exactamente lo que
 * ocupaba antes, y lo único que se agrega es un «+» al inicio.
 *
 * También absorbe el «¿por qué?» que antes era un `PorQue` aparte. Eran dos
 * controles plegables, uno encima del otro, para responder la misma pregunta.
 * (`PorQue` sigue existiendo: lo usan otras trece pantallas.)
 *
 * **El puntero es `archivo · símbolo`, no `archivo:línea`.** Los punteros del
 * libro llevan número de línea porque `tools/verifica_mapa.py` los revisa en
 * cada pytest; ese verificador recorre `docs/libro/*.html` y no el frontend,
 * así que un número acá se correría en silencio con la primera edición del
 * núcleo. El nombre del símbolo no se corre, y `test_punteros_saber_mas.py`
 * comprueba que siga existiendo.
 */

import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Formula, Simbolo } from "@/components/ui/Formula";
import { cn } from "@/lib/cn";

export interface FuenteNucleo {
  /** Ruta dentro de `packages/titirilquen_core/src/titirilquen_core/`. */
  archivo: string;
  /** Función o variable donde vive el cálculo. */
  simbolo: string;
}

export interface SaberMasProps {
  /** La etiqueta de la fila: va dentro del `<summary>`, en una sola línea. */
  children: ReactNode;
  /** La ecuación, en LaTeX. No se traduce: es notación. */
  ecuacion: string;
  /** [símbolo en LaTeX, texto ya traducido]. */
  simbolos: [string, string][];
  fuente: FuenteNucleo;
  /** La explicación en prosa, cuando la métrica necesita una. */
  porque?: string;
  className?: string;
}

export function SaberMas({
  children,
  ecuacion,
  simbolos,
  fuente,
  porque,
  className,
}: SaberMasProps) {
  const { t } = useTranslation("simulator");
  return (
    <details className={cn("saber-mas", className)}>
      <summary>{children}</summary>
      <div className="saber-mas-body">
        {porque && <p className="saber-mas-porque">{porque}</p>}
        <Formula tex={ecuacion} />
        <dl className="saber-mas-glosa">
          {simbolos.map(([tex, texto]) => (
            <div key={tex}>
              <dt>
                <Simbolo tex={tex} />
              </dt>
              <dd>{texto}</dd>
            </div>
          ))}
        </dl>
        <p className="saber-mas-fuente">
          {t("agg.saber_mas_fuente")}{" "}
          <code>
            {fuente.archivo} · {fuente.simbolo}
          </code>
        </p>
      </div>
    </details>
  );
}
