/**
 * Renderiza a MathML las ecuaciones de los informes de `docs/` y `sandbox/`.
 *
 *     node tools/renderiza_ecuaciones.js            # todos los archivos
 *     node tools/renderiza_ecuaciones.js --check    # falla si algo esta desactualizado
 *
 * **Por que MathML y no KaTeX HTML.** Los informes se leen offline, desde
 * `file://` y en papel. El HTML de KaTeX necesita sus propias fuentes: 1,2 MB
 * de binarios versionados, o un CDN que rompe el uso sin red. MathML lo
 * renderiza el navegador solo, con la fuente matematica del sistema —
 * `Cambria Math`, que es justo la que el CSS de los informes ya pide— y pesa
 * 783 bytes por ecuacion contra 7.712.
 *
 * **La fuente de verdad es el atributo, no el markup.** Cada ecuacion se
 * escribe asi:
 *
 *     <div class="ecuacion" data-tex="Q_h = \\int f(w)\\,dw" data-id="(4)"></div>
 *
 * y este script le mete adentro el `<math>` generado. Es idempotente: vuelve a
 * escribir el contenido entero cada vez, asi que editar el `data-tex` y
 * re-correrlo alcanza. El LaTeX queda a la vista en el HTML, no escondido en
 * un blob generado.
 */

const fs = require("fs");
const path = require("path");
const katex = require("katex");

const RAIZ = path.resolve(__dirname, "..");
const ARCHIVOS = [
  "docs/hev-cuadratura.html",
  "docs/informe-hev.html",
  "sandbox/hev-paso-a-paso/informe.html",
  "sandbox/impacto-hev/informe.html",
  "sandbox/impacto-rho/informe.html",
];

/** `<div class="ecuacion…" data-tex="…" [data-id="…"]> … </div>` */
const ECUACION = /<div class="(ecuacion[^"]*)"([^>]*?)>([\s\S]*?)<\/div>/g;

function atributo(attrs, nombre) {
  const m = attrs.match(new RegExp(`${nombre}="([^"]*)"`));
  return m ? m[1] : null;
}

/** Deshace las entidades HTML del atributo antes de pasarlo a KaTeX. */
function desescapa(s) {
  return s
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&");
}

function renderiza(tex, id) {
  const mathml = katex.renderToString(desescapa(tex), {
    output: "mathml",
    displayMode: true,
    throwOnError: true,
    strict: "ignore",
  });
  const marca = id ? `<span class="id">${id}</span>` : "";
  return `\n  ${marca}${mathml}\n`;
}

function procesa(rel, comprobar) {
  const abs = path.join(RAIZ, rel);
  const antes = fs.readFileSync(abs, "utf8");
  let n = 0;
  let saltadas = 0;

  const despues = antes.replace(ECUACION, (todo, clase, attrs, cuerpo) => {
    const tex = atributo(attrs, "data-tex");
    if (!tex) {
      // Ecuacion todavia escrita a mano: se deja como esta. Convertirla es
      // agregarle `data-tex`, no tocar este script.
      saltadas++;
      return todo;
    }
    n++;
    return `<div class="${clase}"${attrs}>${renderiza(tex, atributo(attrs, "data-id"))}</div>`;
  });

  const cambio = despues !== antes;
  if (cambio && !comprobar) fs.writeFileSync(abs, despues);
  return { rel, n, saltadas, cambio };
}

function main() {
  const comprobar = process.argv.includes("--check");
  let sucios = 0;
  let total = 0;
  let pendientes = 0;

  for (const rel of ARCHIVOS) {
    const r = procesa(rel, comprobar);
    total += r.n;
    pendientes += r.saltadas;
    if (r.cambio) sucios++;
    const estado = r.cambio
      ? comprobar
        ? "DESACTUALIZADO"
        : "actualizado"
      : "al dia";
    console.log(
      `  ${r.rel.padEnd(40)} ${String(r.n).padStart(2)} en MathML` +
        (r.saltadas ? `, ${r.saltadas} a mano` : "") +
        `   ${estado}`,
    );
  }

  console.log(
    `\n  ${total} ecuaciones renderizadas, ${pendientes} todavia a mano.`,
  );
  if (comprobar && sucios) {
    console.error(
      `\n  ${sucios} archivo(s) desactualizado(s). Corre` +
        ` \`node tools/renderiza_ecuaciones.js\` y commitea el resultado.`,
    );
    process.exit(1);
  }
}

main();
