import { test, expect } from "@playwright/test";

/**
 * Simulación end-to-end real con el motor Pyodide (por defecto). El primer
 * arranque descarga Pyodide + numpy/scipy/pydantic desde CDN, así que el test
 * usa un timeout amplio y está tagueado @slow para poder excluirlo en CI
 * rápido (`--grep-invert @slow`).
 */
test.describe("simulación end-to-end @slow", () => {
  test("corre el MSA en Pyodide y puebla los KPIs", async ({ page }) => {
    test.setTimeout(180_000);
    await page.goto("/sandbox");

    await page.locator("button.run-btn").click();

    const kpiValues = page.locator(".kpis .kpi .value");
    // Antes de correr el primer KPI (viajes) es "—"; al terminar es un número.
    await expect(kpiValues.first()).not.toHaveText("—", { timeout: 170_000 });

    // El KPI de reparto Auto debe ser un porcentaje y aparecen los paneles FIG.
    // (hay más de un .panel-grid: el Inspector de utilidad es permanente; el
    // grid de resultados aparece con la corrida — verificamos este último).
    await expect(kpiValues.nth(1)).toContainText("%");
    await expect(
      page.locator(".panel-grid", { hasText: "Red vial" }),
    ).toBeVisible();
  });
});
