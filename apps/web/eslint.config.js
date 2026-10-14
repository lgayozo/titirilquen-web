import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist",
      "playwright-report",
      "test-results",
      "vite.config.*",
      "eslint.config.js",
      "scripts/**",
      "**/*.d.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.node },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      // Reglas clásicas de hooks (no las del React Compiler, demasiado estrictas).
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      // El código usa `any` puntualmente (interop Pyodide, CSS vars). No bloquear.
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-non-null-assertion": "off",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  // B1: el color vive en los tokens de `index.css` (y sus mapas en
  // `lib/modos.ts`). Un hex o una clase de paleta de Tailwind en un componente
  // no sigue el tema y saltea la regla «el color pertenece a los datos».
  // (Las regex de esquery no admiten el límite de palabra; de ahí el guion.)
  {
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/lib/gen/**"],
    rules: {
      "no-restricted-syntax": [
        "error",
        ...["Literal[value=%s]", "TemplateElement[value.raw=%s]"].flatMap(
          (sel) => [
            {
              selector: sel.replace("%s", "/#[0-9a-fA-F]{3,8}/"),
              message: "Color fijo: usá un token de index.css (var(--…)).",
            },
            {
              selector: sel.replace(
                "%s",
                "/-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]{2,3}/",
              ),
              message:
                "Clase de paleta de Tailwind: usá un token de index.css (p. ej. text-[var(--muted)]).",
            },
          ],
        ),
      ],
    },
  },
  // Los specs E2E corren en Node con APIs de Playwright.
  {
    files: ["e2e/**/*.ts"],
    languageOptions: { globals: { ...globals.node } },
  },
);
