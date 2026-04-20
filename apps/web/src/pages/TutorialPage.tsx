import { lazy, Suspense, useMemo } from "react";
import { MDXProvider } from "@mdx-js/react";
import { NavLink, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { mdxComponents } from "@/tutorials/components";
import {
  TUTORIAL_TOC_ES,
  TUTORIAL_TOC_EN,
  tutorialsByLang,
  type TutorialMeta,
} from "@/tutorials/manifest";
import { cn } from "@/lib/cn";

export function TutorialPage() {
  const { i18n, t } = useTranslation("simulator");
  const params = useParams<{ slug: string }>();
  const lang = (i18n.resolvedLanguage === "en" ? "en" : "es") as "es" | "en";

  const toc = lang === "en" ? TUTORIAL_TOC_EN : TUTORIAL_TOC_ES;
  const slug = params.slug ?? toc[0]?.slug ?? "intro";

  const Component = useMemo(() => {
    const entry = tutorialsByLang[lang].find((e) => e.meta.slug === slug);
    if (!entry) return null;
    return lazy(entry.load);
  }, [lang, slug]);

  const currentIdx = toc.findIndex((t) => t.slug === slug);
  const prev = currentIdx > 0 ? toc[currentIdx - 1] : null;
  const next = currentIdx < toc.length - 1 ? toc[currentIdx + 1] : null;

  return (
    <div className="grid grid-cols-[220px_1fr] gap-8">
      <nav
        aria-label={t("tutorial.toc")}
        className="h-fit rounded-lg border border-slate-200 bg-white p-3 text-sm dark:border-slate-800 dark:bg-slate-950"
      >
        <h2 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          {t("tutorial.toc")}
        </h2>
        <ol className="space-y-1">
          {toc.map((entry) => (
            <TocItem key={entry.slug} entry={entry} />
          ))}
        </ol>
      </nav>

      <article className="prose-none max-w-3xl pb-12">
        {Component ? (
          <Suspense fallback={<SkeletonArticle />}>
            <MDXProvider components={mdxComponents}>
              <Component />
            </MDXProvider>
          </Suspense>
        ) : (
          <div className="rounded-lg border border-dashed border-slate-300 p-12 text-center text-sm text-slate-500 dark:border-slate-700">
            {t("tutorial.not_found", { slug })}
          </div>
        )}

        <div className="mt-10 flex items-center justify-between border-t border-slate-200 pt-4 text-sm dark:border-slate-800">
          {prev ? (
            <NavLink
              to={`/tutorial/${prev.slug}`}
              className="flex items-center gap-1 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            >
              ← {prev.title}
            </NavLink>
          ) : (
            <span />
          )}
          {next && (
            <NavLink
              to={`/tutorial/${next.slug}`}
              className="flex items-center gap-1 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            >
              {next.title} →
            </NavLink>
          )}
        </div>
      </article>
    </div>
  );
}

function TocItem({ entry }: { entry: TutorialMeta }) {
  return (
    <li>
      <NavLink
        to={`/tutorial/${entry.slug}`}
        className={({ isActive }) =>
          cn(
            "block rounded px-2 py-1.5",
            isActive
              ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-slate-100"
              : "text-slate-600 hover:bg-slate-50 dark:text-slate-400 dark:hover:bg-slate-900"
          )
        }
      >
        <div className="text-[13px]">
          <span className="font-mono text-[10px] text-slate-400">{entry.order}.</span>{" "}
          {entry.title}
        </div>
        {entry.tagline && (
          <div className="mt-0.5 text-[11px] text-slate-400">{entry.tagline}</div>
        )}
      </NavLink>
    </li>
  );
}

function SkeletonArticle() {
  const { t } = useTranslation("simulator");
  return (
    <div className="space-y-3 py-4" aria-busy="true" aria-label={t("tutorial.loading")}>
      <div className="h-6 w-2/3 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
      <div className="h-3 w-full animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
      <div className="h-3 w-5/6 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
      <div className="h-3 w-4/6 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />
    </div>
  );
}
