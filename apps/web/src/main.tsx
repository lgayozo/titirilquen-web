import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider, createBrowserRouter } from "react-router-dom";

import "@/i18n";
import "@/index.css";
import { applyTheme, getStoredTheme } from "@/lib/theme";
import { RootLayout } from "@/components/RootLayout";
import { AboutPage } from "@/pages/AboutPage";
import { ComparePage } from "@/pages/ComparePage";
import { CoupledPage } from "@/pages/CoupledPage";
import { LandUsePage } from "@/pages/LandUsePage";
import { SandboxPage } from "@/pages/SandboxPage";
import { TutorialPage } from "@/pages/TutorialPage";
import { useCompareStore } from "@/store/compareStore";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";

// Aplica el tema antes de renderizar para evitar flash sin estilos.
applyTheme(getStoredTheme());

if (import.meta.env.DEV) {
  (window as unknown as { __stores: object }).__stores = {
    simulation: useSimulationStore,
    landUse: useLandUseStore,
    compare: useCompareStore,
  };
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { index: true, element: <TutorialPage /> },
      { path: "tutorial", element: <TutorialPage /> },
      { path: "tutorial/:slug", element: <TutorialPage /> },
      { path: "sandbox", element: <SandboxPage /> },
      { path: "land-use", element: <LandUsePage /> },
      { path: "coupled", element: <CoupledPage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "about", element: <AboutPage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
