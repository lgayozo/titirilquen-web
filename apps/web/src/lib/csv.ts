/**
 * Descarga de datos tabulares como CSV — para exportar métricas de una corrida
 * y compararlas luego entre escenarios (beneficios/desbeneficios sociales).
 *
 * Formato: UTF-8 con BOM (para que Excel en es-CL respete los acentos) y
 * separador coma con comillas cuando el valor lo requiere.
 */

const escapeCell = (v: string | number): string => {
  const s = String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

export function toCsv(rows: readonly (readonly (string | number)[])[]): string {
  return rows.map((r) => r.map(escapeCell).join(",")).join("\r\n");
}

export function downloadCsv(
  filename: string,
  rows: readonly (readonly (string | number)[])[],
): void {
  const blob = new Blob(["﻿" + toCsv(rows)], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
