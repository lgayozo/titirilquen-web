#!/usr/bin/env node
/**
 * Sincroniza TODO lo que el frontend deriva del núcleo Python. Ejecutar tras
 * cualquier cambio en el paquete: si no, el navegador sigue corriendo el
 * código anterior y los tipos generados quedan mintiendo.
 *
 *   1. Recompila el wheel que instala Pyodide (`public/pyodide/`).
 *   2. Genera el contrato TypeScript (`src/lib/gen/`).
 *   3. Regenera los fixtures golden del contrato (`e2e/fixtures/`).
 *
 * Usa `uv`, que es el gestor de entornos del repo (los tests y los scripts de
 * auditoría se corren con `uv run`). La versión anterior de este script
 * buscaba un intérprete suelto en el PATH e intentaba `pip install build`,
 * lo que en macOS falla contra PEP 668 ("externally-managed-environment") y
 * dejaba el flujo documentado sin funcionar. `uv build` no necesita nada
 * instalado: resuelve el backend de build en un entorno efímero.
 *
 * El wheel previo se borra SOLO después de compilar con éxito, para que un
 * fallo no deje a Pyodide sin asset.
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

const UV = process.env.UV ?? "uv";
try {
  execSync(`${UV} --version`, { stdio: "ignore" });
} catch {
  console.error(
    `No se encontró '${UV}'. Este repo usa uv para todo lo de Python.\n` +
      "  macOS/Linux:  curl -LsSf https://astral.sh/uv/install.sh | sh\n" +
      "  Windows:      winget install astral-sh.uv\n" +
      "Si lo tenés en otra ruta: UV=/ruta/a/uv npm run build:core-wheel",
  );
  process.exit(1);
}

console.log("Compilando wheel de titirilquen_core con uv…");
execSync(`${UV} build --wheel --out-dir "${OUT_DIR}"`, {
  cwd: CORE_PKG,
  stdio: "inherit",
});

// `uv build` deja un `.gitignore` con `*` en el directorio de salida, pensado
// para un `dist/` que no se versiona. Acá el wheel SÍ va al repo (es el asset
// que sirve Pyodide), y ese archivo es una trampa silenciosa: se ignora a sí
// mismo, así que no aparece en `git status`, y en un clon limpio haría que el
// wheel recién compilado fuera invisible para git.
const UV_GITIGNORE = resolve(OUT_DIR, ".gitignore");
if (existsSync(UV_GITIGNORE)) {
  rmSync(UV_GITIGNORE);
}

// Conservar solo el wheel recién generado; borrar versiones viejas. Importa
// cuando cambia el número de versión: sin esto quedarían dos .whl y el worker
// tomaría el que dice su constante, no el nuevo.
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
  console.log(`  (borrado el wheel viejo ${stale.f})`);
}

console.log(`  wheel: public/pyodide/${wheels[0].f}`);

// 2. Contrato TypeScript generado desde Pydantic.
console.log("Generando el contrato TypeScript…");
execSync(`${UV} run python tools/genera_contrato.py`, {
  cwd: CORE_PKG,
  stdio: "inherit",
});

// 3. Fixtures golden: pinean las formas de oferta del core para que el espejo
//    de `citySupply.ts` no pueda driftar en silencio.
console.log("Regenerando fixtures golden…");
execSync(`${UV} run --extra dev python tests/test_contract_frontend.py`, {
  cwd: CORE_PKG,
  stdio: "inherit",
});

console.log("\nNúcleo sincronizado. Si `git status` muestra cambios en");
console.log("src/lib/gen o e2e/fixtures, van en el mismo commit que el core.");
