import { useTranslation } from "react-i18next";

/**
 * Rótulo de tabla, con el mismo formato que el de figura.
 *
 * Es la misma estructura que el header de figura (ver `Panel`): numeral de dos
 * dígitos en la familia de figuras y color de acento, seguido del nombre en la
 * familia de display a 14 px. Antes el rótulo entero iba en mono gris de 10 px
 * con versalitas, así que una tabla y una figura contiguas no parecían del
 * mismo documento.
 *
 * Es un componente y no tres strings de i18n justamente para que las tres
 * tablas no puedan volver a divergir.
 */
export function CaptionTabla({ n, nombre }: { n: string; nombre: string }) {
  const { t } = useTranslation("simulator");
  return (
    <caption>
      {/* El espacio es real y no sólo margen: sin él, copiar el rótulo daba
          «TABLA 01Agregados de ciudad completa». */}
      <span className="n">{t("tabla_n", { n })}</span>{" "}
      <span className="nombre">{nombre}</span>
    </caption>
  );
}
