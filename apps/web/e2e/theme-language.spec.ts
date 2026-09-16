import { test, expect } from "@playwright/test";

test.describe("tema e idioma", () => {
  test("cambia el tema vía el botón cíclico", async ({ page }) => {
    await page.goto("/");
    const html = page.locator("html");
    // Un solo botón que cicla paper → journal → dark → paper.
    const theme = page
      .getByRole("banner")
      .getByRole("button", { name: "Tema" });

    await theme.click();
    await expect(html).toHaveAttribute("data-theme", "journal");

    await theme.click();
    await expect(html).toHaveAttribute("data-theme", "dark");

    await theme.click();
    await expect(html).toHaveAttribute("data-theme", "paper");
  });

  test("cambia el idioma ES → EN y traduce la interfaz", async ({ page }) => {
    await page.goto("/");
    const banner = page.getByRole("banner");
    await expect(
      banner.getByRole("link", { name: "Uso de suelo", exact: true }),
    ).toBeVisible();

    await page
      .getByRole("radiogroup", { name: "Idioma" })
      .getByRole("radio", { name: "EN" })
      .click();

    // La nav se traduce: "Uso de suelo" → "Land use", "Acerca de" → "About".
    await expect(
      banner.getByRole("link", { name: "Land use", exact: true }),
    ).toBeVisible();
    await expect(
      banner.getByRole("link", { name: "About", exact: true }),
    ).toBeVisible();
  });
});
