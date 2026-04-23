/**
 * Sistema de temas editorial: `paper` (default), `dark`, `journal`, `system`.
 *
 * Aplicamos el tema mediante `data-theme` en `<html>` — no usamos `.dark`
 * porque queremos 3 paletas distintas, no solo dos. Tailwind está configurado
 * con `darkMode: ['selector', '[data-theme="dark"]']` para que las clases
 * `dark:` se activen cuando el tema efectivo es `dark`.
 *
 * La preferencia se persiste en localStorage. `system` resuelve a `paper` o
 * `dark` según la media query del SO.
 */

export type Theme = "paper" | "dark" | "journal" | "system";
export type ResolvedTheme = "paper" | "dark" | "journal";

const STORAGE_KEY = "titirilquen.theme";

export function getStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === "paper" || raw === "dark" || raw === "journal" || raw === "system") return raw;
  // Compat con valores antiguos
  if (raw === "light") return "paper";
  return "system";
}

export function storeTheme(theme: Theme): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, theme);
}

export function resolveTheme(theme: Theme): ResolvedTheme {
  if (theme !== "system") return theme;
  if (typeof window === "undefined") return "paper";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "paper";
}

export function applyTheme(theme: Theme): ResolvedTheme {
  const resolved = resolveTheme(theme);
  document.documentElement.dataset.theme = resolved;
  // Mantener color-scheme para navegadores que lo usan
  document.documentElement.style.colorScheme = resolved === "dark" ? "dark" : "light";
  return resolved;
}

export function watchSystemTheme(onChange: (isDark: boolean) => void): () => void {
  if (typeof window === "undefined") return () => {};
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const handler = (e: MediaQueryListEvent) => onChange(e.matches);
  mq.addEventListener("change", handler);
  return () => mq.removeEventListener("change", handler);
}
