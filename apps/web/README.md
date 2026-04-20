# @titirilquen/web

Frontend Vite + React 18 + TypeScript.

## Desarrollo

```bash
pnpm install
pnpm dev          # http://localhost:5173
```

Asume que `api` corre en `http://localhost:8000` (proxy configurado en `vite.config.ts`).

## Estructura

```
src/
├── main.tsx                Entry + router
├── index.css               Tailwind base
├── components/
│   ├── RootLayout.tsx      Header + nav + footer
│   ├── LanguageSwitcher.tsx
│   └── CityStrip.tsx       Visualización 1D de la ciudad
├── pages/
│   ├── TutorialPage.tsx    Landing + pasos (MDX pendiente)
│   ├── SandboxPage.tsx     App principal
│   └── ComparePage.tsx     Placeholder
├── i18n/                   ES/EN con namespaces (common, simulator)
├── lib/
│   ├── api.ts              Cliente FastAPI + SSE
│   ├── types.ts            Espejo manual de los schemas Pydantic
│   ├── defaults.ts         Config inicial
│   └── cn.ts               Utility Tailwind
└── store/
    └── simulationStore.ts  Zustand — estado global
```

## Fases pendientes

- Integrar Pyodide (engine=local)
- Exponer parámetros avanzados de oferta via sliders
- Utility breakdown interactivo (bar chart apilado por modo)
- Animación del loop MSA con traza de convergencia
- Import/export `.ttrq.json`
- Tutorial MDX
