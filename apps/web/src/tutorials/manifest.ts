/**
 * Manifest de tutoriales MDX por idioma.
 *
 * `import.meta.glob` con `eager: false` hace code-splitting automático:
 * cada MDX se carga sólo cuando el usuario navega a esa sección.
 */

import type { ComponentType } from "react";

export interface TutorialMeta {
  slug: string;
  order: number;
  title: string;
  tagline?: string;
}

export interface TutorialEntry {
  meta: TutorialMeta;
  load: () => Promise<{ default: ComponentType }>;
}

type MdxModule = {
  default: ComponentType;
  frontmatter?: TutorialMeta;
};

const esModules = import.meta.glob<MdxModule>("./es/*.mdx");
const enModules = import.meta.glob<MdxModule>("./en/*.mdx");

/**
 * Extrae el slug del nombre de archivo `./es/02-city.mdx` → `city` (usando
 * frontmatter si está, o el nombre en fallback).
 */
function slugFromPath(path: string): string {
  const base = path.split("/").pop() ?? path;
  return base.replace(/^\d+-/, "").replace(/\.mdx$/, "");
}

function buildEntries(modules: Record<string, () => Promise<MdxModule>>): TutorialEntry[] {
  const raw = Object.entries(modules).map(([path, loader]) => ({
    path,
    slug: slugFromPath(path),
    order: extractOrder(path),
    loader,
  }));
  raw.sort((a, b) => a.order - b.order);

  return raw.map(({ path, slug, order, loader }) => ({
    meta: {
      slug,
      order,
      title: humanize(slug),
    },
    load: async () => {
      const mod = await loader();
      if (mod.frontmatter) {
        // Actualizar meta en caliente si el MDX declara frontmatter
        const frontSlug = mod.frontmatter.slug ?? slug;
        if (frontSlug !== slug) {
          console.warn(`[tutorials] slug frontmatter "${frontSlug}" != path "${slug}" en ${path}`);
        }
      }
      return { default: mod.default };
    },
  }));
}

function extractOrder(path: string): number {
  const m = path.match(/\/(\d+)-/);
  return m ? parseInt(m[1] ?? "0", 10) : 0;
}

function humanize(slug: string): string {
  return slug.charAt(0).toUpperCase() + slug.slice(1).replace(/-/g, " ");
}

export const tutorialsByLang: Record<"es" | "en", TutorialEntry[]> = {
  es: buildEntries(esModules),
  en: buildEntries(enModules),
};

/**
 * TOC estático (ES) — se usa para la navegación lateral sin cargar los MDX.
 * Los títulos deben coincidir con el frontmatter de cada archivo.
 */
export const TUTORIAL_TOC_ES: readonly TutorialMeta[] = [
  { slug: "intro", order: 1, title: "Bienvenida", tagline: "Por qué ciudad lineal" },
  { slug: "city", order: 2, title: "Ciudad", tagline: "Discretización y población" },
  { slug: "supply", order: 3, title: "Oferta", tagline: "BPR, Greenshields, metro" },
  { slug: "demand", order: 4, title: "Demanda", tagline: "Utilidad + logit" },
  { slug: "equilibrium", order: 5, title: "Equilibrio", tagline: "MSA + loop acoplado" },
  { slug: "experimenting", order: 6, title: "Experimentar", tagline: "Presets y actividades" },
] as const;

export const TUTORIAL_TOC_EN: readonly TutorialMeta[] = TUTORIAL_TOC_ES;
