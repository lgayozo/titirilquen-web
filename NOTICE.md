# Aviso de atribución

Este proyecto es un **trabajo derivado** del simulador **Titirilquen** original:

- **Repositorio fuente**: https://github.com/lehyt2163/Titirilquen
- **Autores del modelo matemático y de la implementación original**:
  - Sebastian Acevedo
  - Pablo Alvarez
  - Fernando Castillo
  - Angelo Guevara
- **Institución**: Facultad de Ciencias Físicas y Matemáticas (FCFM), Universidad de Chile
- **Licencia original**: GPL-3.0-or-later

## Qué se portó verbatim del original

- Funciones de oferta: `demora_auto_tramo`, `demora_bici_tramo`, `oferta_tren`
  (ahora en [`packages/titirilquen_core/src/titirilquen_core/supply/`](packages/titirilquen_core/src/titirilquen_core/supply/))
- Funciones de demanda: `calcular_utilidades`, `elegir_modo`
  (ahora en [`packages/titirilquen_core/src/titirilquen_core/demand/`](packages/titirilquen_core/src/titirilquen_core/demand/))
- Clase `Ciudad` del módulo de uso de suelo (Alonso-Muth-Mills)
  (ahora en [`packages/titirilquen_core/src/titirilquen_core/land_use/`](packages/titirilquen_core/src/titirilquen_core/land_use/))
- Fórmula de emisiones CO₂ y factores por estrato
- Los 7 presets de políticas de transporte

## Cambios y agregados respecto al original

Los detalles están en [`docs/DISCREPANCIES.md`](docs/DISCREPANCIES.md). Resumen:

- Reestructurado en paquete Python tipado con Pydantic v2
- Frontend nuevo React/TypeScript con Vite (reemplaza la UI Streamlit)
- Motor dual: FastAPI (servidor) + Pyodide (navegador)
- Loop acoplado suelo↔transporte con streaming SSE
- Módulo de comparación de escenarios
- Tutorial interactivo con MDX y ecuaciones KaTeX
- Accesibilidad (ARIA, `prefers-reduced-motion`, skip link)
- Export SVG/PNG de figuras para material docente
- i18n ES/EN
- Documentación de discrepancias código↔Overleaf (11 notas D-01 a D-11)

## Licencia

Al ser un derivado de un trabajo GPLv3, este repositorio mantiene la misma
licencia **GNU General Public License v3.0 or later** — ver [`LICENSE`](LICENSE).

Cualquier modificación o redistribución debe mantener esta licencia y
preservar la atribución a los autores originales.
