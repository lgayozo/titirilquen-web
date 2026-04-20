#!/usr/bin/env node
/**
 * Re-compila el wheel de `titirilquen_core` y lo deja en `public/pyodide/`.
 * Ejecutar tras cualquier cambio en el paquete Python.
 */
import { execSync } from "node:child_process";
import { existsSync, readdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = resolve(__dirname, "..");
const CORE_PKG = resolve(WEB_ROOT, "..", "..", "packages", "titirilquen_core");
const OUT_DIR = resolve(WEB_ROOT, "public", "pyodide");

if (!existsSync(CORE_PKG)) {
  console.error(`No se encuentra el paquete core en ${CORE_PKG}`);
  process.exit(1);
}

for (const f of readdirSync(OUT_DIR).filter((n) => n.endsWith(".whl"))) {
  rmSync(resolve(OUT_DIR, f));
}

console.log("Compilando wheel de titirilquen_core…");
execSync(`python -m build --wheel --outdir "${OUT_DIR}"`, {
  cwd: CORE_PKG,
  stdio: "inherit",
});

const whl = readdirSync(OUT_DIR).find((f) => f.endsWith(".whl"));
if (!whl) {
  console.error("No se generó wheel.");
  process.exit(1);
}
console.log(`Wheel listo: public/pyodide/${whl}`);
