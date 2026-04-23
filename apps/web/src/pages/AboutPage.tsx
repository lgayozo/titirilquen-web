import { useTranslation } from "react-i18next";

interface Author {
  name: string;
  roleKey: string;
}

const ORIGINAL_AUTHORS: readonly Author[] = [
  { name: "Angelo Guevara", roleKey: "about.roles.lead_author" },
  { name: "Sebastian Acevedo", roleKey: "about.roles.author" },
  { name: "Pablo Alvarez", roleKey: "about.roles.author" },
  { name: "Fernando Castillo", roleKey: "about.roles.author" },
] as const;

const WEB_AUTHORS: readonly Author[] = [
  { name: "Leandro Gayozo", roleKey: "about.roles.web_engineer" },
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
        <div className="about-section-head">{t("about.sections.model_authors")}</div>
        <h3>{t("about.model_authors.heading")}</h3>
        <p>{t("about.model_authors.body")}</p>
        <div className="authors-grid">
          {ORIGINAL_AUTHORS.map((author) => (
            <AuthorCard key={author.name} name={author.name} role={t(author.roleKey)} />
          ))}
        </div>
        <div className="about-tags">
          <span className="about-tag">{t("about.tags.fcfm")}</span>
          <span className="about-tag">{t("about.tags.uchile")}</span>
          <span className="about-tag">{t("about.tags.transport")}</span>
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-head">{t("about.sections.web_impl")}</div>
        <h3>{t("about.web_impl.heading")}</h3>
        <p>{t("about.web_impl.body")}</p>
        <div className="authors-grid authors-grid--wide">
          {WEB_AUTHORS.map((author) => (
            <AuthorCard key={author.name} name={author.name} role={t(author.roleKey)} />
          ))}
        </div>
      </section>

      <section className="about-section">
        <div className="about-section-head">{t("about.sections.license")}</div>
        <h3>{t("about.license.heading")}</h3>
        <p>{t("about.license.body")}</p>
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

function AuthorCard({ name, role }: { name: string; role: string }) {
  return (
    <div className="author-card">
      <div className="author-name">{name}</div>
      <p className="author-role">{role}</p>
    </div>
  );
}
