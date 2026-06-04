import { test, expect } from "@playwright/test";

/** Rutas de la nav (etiquetas en español, idioma por defecto). */
const ROUTES = [
  { name: "Transporte", path: "/sandbox" },
  { name: "Uso de suelo", path: "/land-use" },
  { name: "Acoplado", path: "/coupled" },
  { name: "Comparar", path: "/compare" },
  { name: "Acerca de", path: "/about" },
  { name: "Tutorial", path: "/" },
];

test.describe("smoke / navegación", () => {
  test("carga la app con topbar y contenido principal", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Titirilquen/);
    await expect(page.getByRole("banner")).toBeVisible();
    await expect(page.locator("#main-content")).toBeVisible();
  });

  for (const route of ROUTES) {
    test(`navega a "${route.name}"`, async ({ page }) => {
      await page.goto("/");
      await page
        .getByRole("banner")
        .getByRole("link", { name: route.name, exact: true })
        .click();
      await expect(page).toHaveURL(new RegExp(`${route.path}$`));
      await expect(page.locator("#main-content")).toBeVisible();
    });
  }

  test("sandbox muestra el botón de simular", async ({ page }) => {
    await page.goto("/sandbox");
    await expect(page.locator("button.run-btn")).toBeVisible();
  });

  test("acerca de muestra los créditos", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByText("Acerca de Titirilquen")).toBeVisible();
  });
});
