import { defineConfig, devices } from "@playwright/test";

/**
 * E2E con Playwright. El servidor de dev (Vite) se levanta automáticamente.
 * El motor por defecto es Pyodide (local), así que la mayoría de los tests
 * NO requieren la API de FastAPI; sólo el test de simulación real necesita
 * red (descarga Pyodide + numpy/scipy desde CDN) y por eso usa un timeout
 * propio y está tagueado @slow.
 */
// Puerto PROPIO del E2E, distinto del 5173 que `vite.config.ts` usa para
// desarrollo. Con el puerto compartido, `reuseExistingServer` adoptaba en
// silencio cualquier Vite que estuviera escuchando ahí —incluido el de otro
// proyecto— y la suite corría entera contra la app equivocada.
const PORT = Number(process.env.E2E_PORT ?? 5273);
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
    // `--strictPort` para que Vite falle si el puerto está tomado en vez de
    // saltar al siguiente: sin eso el servidor queda en otro puerto y Playwright
    // espera 120 s en una URL donde no hay nada.
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
