/**
 * Tema light/dark con preferencia del sistema como opción. Usamos
 * `document.documentElement.classList.toggle('dark', ...)` porque Tailwind
 * está configurado en modo `darkMode: "class"`.
 *
 * El tema se persiste en localStorage con la clave `titirilquen.theme`.
 */

export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "titirilquen.theme";

export function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === "light" || raw === "dark" || raw === "system") return raw;
  return "system";
}

export function storeTheme(theme: Theme): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, theme);
}

/**
 * Resuelve `system` al valor efectivo que preferirían las media queries.
 */
export function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme !== "system") return theme;
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

/**
 * Aplica el tema al <html> — idempotente, seguro para llamar en cada cambio.
 */
export function applyTheme(theme: Theme): "light" | "dark" {
  const resolved = resolveTheme(theme);
  document.documentElement.classList.toggle("dark", resolved === "dark");
  document.documentElement.style.colorScheme = resolved;
  return resolved;
}

/**
 * Suscribe a cambios de la media query — útil cuando theme = "system".
 * Devuelve una función para cancelar.
 */
export function watchSystemTheme(onChange: (isDark: boolean) => void): () => void {
  if (typeof window === "undefined") return () => {};
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = (e: MediaQueryListEvent) => onChange(e.matches);
  mq.addEventListener("change", handler);
  return () => mq.removeEventListener("change", handler);
}
