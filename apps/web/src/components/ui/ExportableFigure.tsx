import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Download, FileImage, FileCode2 } from "lucide-react";

import { cn } from "@/lib/cn";
import { downloadPng, downloadSvg } from "@/lib/svg-export";

interface ExportableFigureProps {
  /** Nombre base del archivo al descargar (sin extensión). */
  name: string;
  /** Título accesible de la figura (anunciado por lectores de pantalla). */
  title: string;
  /** Descripción larga opcional para lectores de pantalla. */
  description?: string;
  /** Si se especifica, añade width/height pixeladas al SVG exportado. */
  exportSize?: { width: number; height: number };
  className?: string;
  children: React.ReactNode;
}

/**
 * Envuelve una figura SVG añadiendo:
 *   - Botón de exportar (SVG / PNG)
 *   - `<figure>` + `<figcaption>` para estructura semántica
 *   - Detección automática del `<svg>` interno (primer descendiente)
 *
 * El contenido puede ser un <svg> solo o un contenedor con un svg dentro.
 * El export captura el primer <svg> descendiente.
 */
export function ExportableFigure({
  name,
  title,
  description,
  exportSize,
  className,
  children,
}: ExportableFigureProps) {
  const { t } = useTranslation("common");
  const ref = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const findSvg = (): SVGElement | null => {
    return ref.current?.querySelector("svg") ?? null;
  };

  const onSvg = () => {
    const svg = findSvg();
    if (svg) downloadSvg(svg, name, exportSize);
    setMenuOpen(false);
  };

  const onPng = async () => {
    const svg = findSvg();
    if (svg) await downloadPng(svg, name, exportSize);
    setMenuOpen(false);
  };

  return (
    <figure
      className={cn("relative group", className)}
      aria-label={title}
    >
      <div ref={ref}>{children}</div>
      {description && <figcaption className="sr-only">{description}</figcaption>}

      <div className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
        <button
          type="button"
          onClick={() => setMenuOpen((o) => !o)}
          aria-label={`${t("actions.export_svg")}: ${title}`}
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          className="rounded bg-slate-900/80 p-1.5 text-white backdrop-blur hover:bg-slate-900 dark:bg-slate-100/80 dark:text-slate-900 dark:hover:bg-slate-100"
        >
          <Download className="h-3.5 w-3.5" aria-hidden />
        </button>
        {menuOpen && (
          <div
            role="menu"
            className="absolute right-0 top-full mt-1 min-w-[120px] overflow-hidden rounded border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
          >
            <button
              type="button"
              role="menuitem"
              onClick={onSvg}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <FileCode2 className="h-3.5 w-3.5" aria-hidden />
              SVG
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => void onPng()}
              className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <FileImage className="h-3.5 w-3.5" aria-hidden />
              PNG
            </button>
          </div>
        )}
      </div>
    </figure>
  );
}
