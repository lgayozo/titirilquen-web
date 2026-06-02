import { defineConfig, devices } from "@playwright/test";

/**
 * E2E con Playwright. El servidor de dev (Vite) se levanta automáticamente.
 * El motor por defecto es Pyodide (local), así que la mayoría de los tests
 * NO requieren la API de FastAPI; sólo el test de simulación real necesita
 * red (descarga Pyodide + numpy/scipy desde CDN) y por eso usa un timeout
 * propio y está tagueado @slow.
 */
const PORT = 5173;
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    locale: "es-CL",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
