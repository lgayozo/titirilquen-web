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

  const currentIdx = toc.findIndex((entry) => entry.slug === slug);
  const current = currentIdx >= 0 ? toc[currentIdx] : null;
  const prev = currentIdx > 0 ? toc[currentIdx - 1] : null;
  const next = currentIdx < toc.length - 1 ? toc[currentIdx + 1] : null;

  return (
    <div className="tutorial">
      <nav aria-label={t("tutorial.toc")} className="tutorial-toc">
        <h2>{t("tutorial.toc")}</h2>
        <ol>
          {toc.map((entry) => (
            <TocItem key={entry.slug} entry={entry} />
          ))}
        </ol>
      </nav>

      <article className="tutorial-article">
        {current && (
          <div className="tutorial-eyebrow">
            {t("tutorial.chapter", { n: String(current.order).padStart(2, "0") })}
            {" · "}
            {current.title}
          </div>
        )}

        {Component ? (
          <Suspense fallback={<SkeletonArticle />}>
            <MDXProvider components={mdxComponents}>
              <Component />
            </MDXProvider>
          </Suspense>
        ) : (
          <div className="tut-notfound">{t("tutorial.not_found", { slug })}</div>
        )}

        {(prev || next) && (
          <div className="tut-pager">
            {prev ? (
              <NavLink to={`/tutorial/${prev.slug}`}>
                <span className="arrow" aria-hidden>
                  ←
                </span>
                {prev.title}
              </NavLink>
            ) : (
              <span />
            )}
            {next ? (
              <NavLink to={`/tutorial/${next.slug}`}>
                {next.title}
                <span className="arrow" aria-hidden>
                  →
                </span>
              </NavLink>
            ) : (
              <span />
            )}
          </div>
        )}
      </article>
    </div>
  );
}

function TocItem({ entry }: { entry: TutorialMeta }) {
  return (
    <li>
      <NavLink
        to={`/tutorial/${entry.slug}`}
        className={({ isActive }) => cn(isActive && "active")}
      >
        <div>
          <span className="toc-num">§{entry.order}</span>
          {entry.title}
        </div>
        {entry.tagline && <span className="toc-tag">{entry.tagline}</span>}
      </NavLink>
    </li>
  );
}

function SkeletonArticle() {
  const { t } = useTranslation("simulator");
  return (
    <div className="tut-skeleton" aria-busy="true" aria-label={t("tutorial.loading")}>
      <div />
      <div />
      <div />
      <div />
    </div>
  );
}
