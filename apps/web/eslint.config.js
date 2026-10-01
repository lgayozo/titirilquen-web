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
  // Los specs E2E corren en Node con APIs de Playwright.
  {
    files: ["e2e/**/*.ts"],
    languageOptions: { globals: { ...globals.node } },
  },
);
