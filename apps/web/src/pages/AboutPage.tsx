import { useTranslation } from "react-i18next";

/** Autoría unificada: modelo original + re-arquitectura web, todos asociados a
 * FCFM · U. de Chile · Transporte (los tags aplican al equipo completo). */
const AUTHORS: readonly string[] = [
  "Angelo Guevara",
  "Leandro Gayozo",
  "Sebastian Acevedo",
  "Pablo Alvarez",
  "Fernando Castillo",
] as const;

const LINKS = [
  {
    labelKey: "about.links.original_repo",
    url: "https://github.com/lehyt2163/Titirilquen",
  },
  {
    labelKey: "about.links.web_repo",
    url: "https://github.com/lgayozo/titirilquen-web",
  },
  {
    labelKey: "about.links.streamlit",
    url: "https://titirilquenv1.streamlit.app",
  },
  {
    labelKey: "about.links.license",
    url: "https://www.gnu.org/licenses/gpl-3.0.en.html",
  },
] as const;

export function AboutPage() {
  const { t } = useTranslation("common");

  return (
    <div className="about">
      <header className="about-hero">
        <div className="about-eyebrow">{t("about.eyebrow")}</div>
        <h1 className="about-title">{t("about.title")}</h1>
        <p className="about-lede">{t("about.lede")}</p>
      </header>

      <section className="about-section">
        <div className="about-section-head">{t("about.sections.authorship")}</div>
        <h3>{t("about.authorship.heading")}</h3>
        <p>{t("about.authorship.body")}</p>
        <div className="authors-grid">
          {AUTHORS.map((name) => (
            <div key={name} className="author-card">
              <div className="author-name">{name}</div>
            </div>
          ))}
        </div>
        <div className="about-tags">
          <span className="about-tag">{t("about.tags.fcfm")}</span>
          <span className="about-tag">{t("about.tags.uchile")}</span>
          <span className="about-tag">{t("about.tags.transport")}</span>
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-head">{t("about.sections.links")}</div>
        <div className="about-links">
          {LINKS.map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className="about-link"
            >
              <div className="about-link-label">{t(link.labelKey)}</div>
              <div className="about-link-url">{link.url}</div>
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
