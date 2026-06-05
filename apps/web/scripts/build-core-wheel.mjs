#!/usr/bin/env node
/**
 * Re-compila el wheel de `titirilquen_core` y lo deja en `public/pyodide/`.
 * Ejecutar tras cualquier cambio en el paquete Python.
 *
 * Robusto frente a entornos sin `python` en el PATH: detecta el intérprete
 * (override con `PYTHON=...`), asegura el paquete `build`, y solo elimina el
 * wheel previo DESPUÉS de compilar con éxito (así un fallo no deja a Pyodide
 * sin asset).
 */
import { execSync } from "node:child_process";
import { existsSync, readdirSync, rmSync, statSync } from "node:fs";
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

/** Primer intérprete de Python que responde a `--version`. */
function resolvePython() {
  const candidates = [process.env.PYTHON, "python3", "python", "py -3"].filter(
    Boolean,
  );
  for (const cmd of candidates) {
    try {
      execSync(`${cmd} --version`, { stdio: "ignore" });
      return cmd;
    } catch {
      // probar el siguiente
    }
  }
  return null;
}

const PY = resolvePython();
if (!PY) {
  console.error(
    "No se encontró un intérprete de Python. Instalá Python 3.11+ o indicá la ruta con PYTHON=/ruta/al/python.",
  );
  process.exit(1);
}

// Asegurar el paquete `build` (no viene con `pip install -e ".[dev]"`).
try {
  execSync(`${PY} -c "import build"`, { stdio: "ignore" });
} catch {
  console.log("El paquete 'build' no está; instalándolo…");
  try {
    execSync(`${PY} -m pip install build`, { stdio: "inherit" });
  } catch {
    console.error(
      `No se pudo instalar 'build'. Instalalo a mano: ${PY} -m pip install build`,
    );
    process.exit(1);
  }
}

console.log(`Compilando wheel de titirilquen_core (con ${PY})…`);
execSync(`${PY} -m build --wheel --outdir "${OUT_DIR}"`, {
  cwd: CORE_PKG,
  stdio: "inherit",
});

// Conservar solo el wheel recién generado (el más nuevo); borrar versiones viejas.
const wheels = readdirSync(OUT_DIR)
  .filter((f) => f.endsWith(".whl"))
  .map((f) => ({ f, mtime: statSync(resolve(OUT_DIR, f)).mtimeMs }))
  .sort((a, b) => b.mtime - a.mtime);

if (wheels.length === 0) {
  console.error("No se generó wheel.");
  process.exit(1);
}

for (const stale of wheels.slice(1)) {
  rmSync(resolve(OUT_DIR, stale.f));
}

console.log(`Wheel listo: public/pyodide/${wheels[0].f}`);
