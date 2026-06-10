import { test, expect } from "@playwright/test";

/**
 * Flujos de persistencia: exportar `.ttrq.json` y compartir por link `?s=`.
 * Sembramos un valor reconocible en el store vía `window.__stores` (afordancia
 * de dev expuesta en `main.tsx`) para no depender de etiquetas de sliders.
 */

declare global {
  interface Window {
    __stores: {
      simulation: {
        getState: () => {
          config: { max_iter: number };
          setConfig: (u: (c: { max_iter: number }) => unknown) => void;
        };
      };
    };
  }
}

async function seedMaxIter(page: import("@playwright/test").Page, value: number) {
  await page.evaluate((v) => {
    window.__stores.simulation.getState().setConfig((c) => ({ ...c, max_iter: v }));
  }, value);
}

test.describe("escenarios: exportar y compartir", () => {
  test("exporta la config como .ttrq.json con el schema correcto", async ({ page }) => {
    await page.goto("/sandbox");
    await seedMaxIter(page, 17);

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar configuración" }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toContain(".ttrq.json");

    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) chunks.push(chunk as Buffer);
    const file = JSON.parse(Buffer.concat(chunks).toString("utf-8"));

    expect(file.$schema).toBe("titirilquen-scenario/v2");
    expect(file.config.max_iter).toBe(17);
    // v2: el escenario incluye también el suelo y las preferencias del acoplado.
    expect(file.land_use).toBeDefined();
    expect(file.coupled?.poblacion).toBeGreaterThan(0);
  });

  test("compartir genera un link ?s= que restaura la config", async ({ page, context }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.goto("/sandbox");
    await seedMaxIter(page, 19);

    await page.getByRole("button", { name: "Compartir por link" }).click();
    const link = await page.evaluate(() => navigator.clipboard.readText());
    expect(link).toContain("?s=");

    await page.goto(link);
    const restored = await page.evaluate(
      () => window.__stores.simulation.getState().config.max_iter
    );
    expect(restored).toBe(19);
  });
});
