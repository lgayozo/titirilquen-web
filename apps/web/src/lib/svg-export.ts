/**
 * Export de figuras SVG (y PNG convertido desde SVG) para material docente.
 *
 * El truco: serializar el `<svg>` vivo incluyendo los estilos calculados
 * (computed styles) de cada nodo relevante. Tailwind genera clases que no
 * viajan al documento serializado; inlinerlas garantiza un SVG visualmente
 * idéntico cuando se abre fuera del navegador.
 */

const STYLE_PROPS = [
  "fill",
  "stroke",
  "stroke-width",
  "stroke-dasharray",
  "stroke-opacity",
  "fill-opacity",
  "opacity",
  "font-family",
  "font-size",
  "font-weight",
  "text-anchor",
] as const;

function inlineComputedStyles(source: SVGElement): SVGElement {
  const clone = source.cloneNode(true) as SVGElement;

  const srcNodes = source.querySelectorAll<SVGElement>("*");
  const cloneNodes = clone.querySelectorAll<SVGElement>("*");

  cloneNodes.forEach((node, i) => {
    const src = srcNodes[i];
    if (!src) return;
    const styles = getComputedStyle(src);
    const inline: string[] = [];
    for (const prop of STYLE_PROPS) {
      const value = styles.getPropertyValue(prop);
      if (value && value !== "none" && value !== "normal") {
        inline.push(`${prop}:${value}`);
      }
    }
    if (inline.length > 0) {
      const existing = node.getAttribute("style") ?? "";
      node.setAttribute("style", `${existing};${inline.join(";")}`.replace(/^;/, ""));
    }
  });

  // Aseguramos xmlns estándar
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  if (!clone.getAttribute("xmlns:xlink")) {
    clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  }
  return clone;
}

function applyPixelDimensions(svg: SVGElement, width: number, height: number): void {
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
}

export function serializeSvg(
  source: SVGElement,
  opts: { width?: number; height?: number } = {}
): string {
  const clone = inlineComputedStyles(source);
  const bbox = source.getBoundingClientRect();
  applyPixelDimensions(clone, opts.width ?? bbox.width, opts.height ?? bbox.height);
  const xml = new XMLSerializer().serializeToString(clone);
  return `<?xml version="1.0" encoding="UTF-8"?>\n${xml}`;
}

export function downloadSvg(
  source: SVGElement,
  filename: string,
  opts?: { width?: number; height?: number }
): void {
  const xml = serializeSvg(source, opts);
  const blob = new Blob([xml], { type: "image/svg+xml;charset=utf-8" });
  triggerDownload(blob, filename.endsWith(".svg") ? filename : `${filename}.svg`);
}

export async function downloadPng(
  source: SVGElement,
  filename: string,
  opts: { width?: number; height?: number; scale?: number } = {}
): Promise<void> {
  const bbox = source.getBoundingClientRect();
  const width = opts.width ?? bbox.width;
  const height = opts.height ?? bbox.height;
  const scale = opts.scale ?? 2;

  const xml = serializeSvg(source, { width, height });
  const url = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(xml)))}`;

  const img = new Image();
  img.crossOrigin = "anonymous";
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error("svg→png image load failed"));
    img.src = url;
  });

  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas 2d context unavailable");
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  await new Promise<void>((resolve) => {
    canvas.toBlob((blob) => {
      if (!blob) return resolve();
      triggerDownload(blob, filename.endsWith(".png") ? filename : `${filename}.png`);
      resolve();
    }, "image/png");
  });
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
