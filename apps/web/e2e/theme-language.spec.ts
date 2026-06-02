import { test, expect } from "@playwright/test";

test.describe("tema e idioma", () => {
  test("cambia el tema vía el selector", async ({ page }) => {
    await page.goto("/");
    const html = page.locator("html");
    const theme = page.getByRole("radiogroup", { name: "Tema" });

    await theme.getByRole("radio", { name: "Oscuro" }).click();
    await expect(html).toHaveAttribute("data-theme", "dark");

    await theme.getByRole("radio", { name: "Journal" }).click();
    await expect(html).toHaveAttribute("data-theme", "journal");

    await theme.getByRole("radio", { name: "Papel" }).click();
    await expect(html).toHaveAttribute("data-theme", "paper");
  });

  test("cambia el idioma ES → EN y traduce la interfaz", async ({ page }) => {
    await page.goto("/");
    const banner = page.getByRole("banner");
    await expect(banner.getByRole("link", { name: "Uso de suelo", exact: true })).toBeVisible();

    await page.getByRole("radiogroup", { name: "Idioma" }).getByRole("radio", { name: "EN" }).click();

    // La nav se traduce: "Uso de suelo" → "Land use", "Acerca de" → "About".
    await expect(banner.getByRole("link", { name: "Land use", exact: true })).toBeVisible();
    await expect(banner.getByRole("link", { name: "About", exact: true })).toBeVisible();
  });
});
