import { test, expect } from "@playwright/test";

/**
 * Simulación end-to-end real con el motor Pyodide (el de POR DEFECTO). El
 * primer arranque descarga Pyodide + numpy/scipy/pydantic desde CDN, así que el
 * test usa un timeout amplio y está tagueado @slow para poder excluirlo del CI
 * rápido (`--grep-invert @slow`).
 *
 * Es además el ÚNICO test del repo que ejerce el runtime del navegador: el core
 * corre en CPython bajo pytest y el resto de la suite e2e no toca el motor. Por
 * eso el CI lo corre en su propio job (`pyodide`) en vez de dejarlo fuera:
 * alinear `pydantic>=2.8` en el núcleo dejó el motor sin arrancar con toda la
 * suite en verde, porque Pyodide 0.26.4 trae 2.7.0 precompilado y `micropip`
 * aborta con "already installed".
 *
 * De dónde se lee el fallo
 * ------------------------
 * Del STORE, no de la consola. Se probó lo obvio primero —`page.on("console")`
 * y `page.on("pageerror")`— y con el wheel bloqueado a propósito capturaron
 * **cero** errores: lo que falla vive dentro de un Web Worker y no se propaga a
 * la página. El worker postea `{type:"error"}` al main thread, `failRun` lo
 * deja en `stage: "error"`, y ahí sí se lee, con el traceback de micropip
 * incluido. Medido: 7 s hasta el diagnóstico contra los 170 s del timeout.
 *
 * El ÉXITO se sigue midiendo por el DOM (los KPIs poblados) porque es el
 * contrato con el usuario; el store se usa sólo para cortar temprano cuando hay
 * fallo. Si `window.__stores` dejara de existir, el test no se rompe: pierde el
 * diagnóstico rápido y vuelve a esperar el DOM.
 */

/** Lo que el store dice del motor, si es que está expuesto. */
type Diagnostico = { estado: "error"; mensaje: string } | false;

test.describe("simulación end-to-end @slow", () => {
  test("corre el MSA en Pyodide y puebla los KPIs", async ({ page }) => {
    test.setTimeout(180_000);

    await page.goto("/sandbox");
    await page.locator("button.run-btn").click();

    const kpiValues = page.locator(".kpis .kpi .value");
    // Antes de correr, el primer KPI (viajes) es "—"; al terminar es un número.
    const kpisListos = expect(kpiValues.first()).not.toHaveText("—", {
      timeout: 170_000,
    });

    // Carrera contra el diagnóstico: lo que ocurra primero manda. Sin esto, un
    // motor que no arranca se manifiesta como un timeout mudo de 170 s y el
    // mensaje de micropip —que dice exactamente qué pasó— queda sin leerse.
    const fallo = page
      .waitForFunction(
        (): Diagnostico => {
          const s = (
            window as unknown as {
              __stores?: { simulation?: { getState: () => unknown } };
            }
          ).__stores?.simulation?.getState() as
            | { stage?: string; error?: string | null }
            | undefined;
          if (s?.stage === "error") {
            return { estado: "error", mensaje: s.error ?? "(sin mensaje)" };
          }
          return false;
        },
        undefined,
        { timeout: 170_000 },
      )
      .then((h) => h.jsonValue())
      // Si nadie falla, esta espera se agota: es el caso bueno, no un problema.
      .catch(() => null);

    const resultado = await Promise.race([
      kpisListos.then(() => null),
      fallo.then((d) => (d && d.estado === "error" ? d : null)),
    ]);

    if (resultado) {
      throw new Error(
        `El motor Pyodide no arrancó. El store reportó:\n\n  ${resultado.mensaje}\n\n` +
          `Si el mensaje menciona "already installed", el núcleo pidió una ` +
          `versión de un paquete que Pyodide ya trae precompilado — revisá las ` +
          `cotas en packages/titirilquen_core/pyproject.toml. Si menciona ` +
          `"Can't fetch wheel", el wheel no se está sirviendo: puede faltar ` +
          `\`npm run sync:core\`.`,
      );
    }

    // El KPI de reparto Auto debe ser un porcentaje y aparecen los paneles FIG.
    // (hay más de un .panel-grid: el Inspector de utilidad es permanente; el
    // grid de resultados aparece con la corrida — verificamos este último).
    await expect(kpiValues.nth(1)).toContainText("%");
    await expect(
      page.locator(".panel-grid", { hasText: "Red vial" }),
    ).toBeVisible();
  });
});
