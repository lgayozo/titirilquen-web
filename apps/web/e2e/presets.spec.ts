import { test, expect, type Page } from "@playwright/test";

/**
 * La galería no depende del orden de los clics (auditoría A3, oct-2026).
 *
 * Las políticas declaran pistas y ciclovía para la escala de Base; a la escala
 * de otra ciudad se aplica su razón (`capacidadPolitica`). Antes la política
 * pisaba la escala: Metrópolis → Pro-Auto quedaba con 5 pistas y 3.000 bici/h,
 * y Pro-Auto → Metrópolis con 16 y 24.000.
 */

async function navegar(page: Page, nombre: string) {
  await page
    .getByRole("banner")
    .getByRole("link", { name: nombre, exact: true })
    .click();
}

async function chip(page: Page, nombre: string) {
  await page.getByRole("button", { name: nombre, exact: true }).click();
}

/** Lee pistas y ciclovía de la tabla de la galería de políticas (Transporte). */
async function capacidad(page: Page) {
  await navegar(page, "Transporte");
  const valor = async (termino: string) => {
    const texto = await page
      .getByRole("term")
      .filter({ hasText: termino })
      .locator("xpath=following-sibling::*[1]")
      .innerText();
    return Number(texto.replace(/\D/g, ""));
  };
  return {
    pistas: await valor("Pistas auto"),
    ciclovia: await valor("Capacidad ciclovía"),
  };
}

for (const [ciudad, politica, esperado] of [
  ["Metrópolis", "Pro-Auto", { pistas: 20, ciclovia: 12000 }],
  ["Metrópolis", "Ciclorrecreovía", { pistas: 12, ciclovia: 57600 }],
  ["Base", "Pro-Bici", { pistas: 4, ciclovia: 12000 }],
] as const) {
  test(`${ciudad} + ${politica} da lo mismo en ambos órdenes`, async ({
    page,
  }) => {
    await page.goto("/");
    await navegar(page, "Uso de suelo");
    await chip(page, ciudad);
    await navegar(page, "Transporte");
    await chip(page, politica);
    const ciudadPrimero = await capacidad(page);

    await page.goto("/");
    await navegar(page, "Transporte");
    await chip(page, politica);
    await navegar(page, "Uso de suelo");
    await chip(page, ciudad);
    const politicaPrimero = await capacidad(page);

    expect(ciudadPrimero).toEqual(esperado);
    expect(politicaPrimero).toEqual(esperado);
    // Y la política se sigue reconociendo a esa escala.
    await expect(
      page.getByRole("button", { name: politica, exact: true }),
    ).toHaveAttribute("aria-pressed", "true");
  });
}
