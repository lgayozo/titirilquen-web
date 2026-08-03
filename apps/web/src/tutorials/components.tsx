import { Link, useNavigate } from "react-router-dom";

import { CoupledFlowchart } from "@/components/viz/CoupledFlowchart";
import { MSAFlowchart } from "@/components/viz/MSAFlowchart";
import { cn } from "@/lib/cn";
import { useLandUseStore } from "@/store/landUseStore";
import { useSimulationStore } from "@/store/simulationStore";
import { TUTORIAL_SCENARIOS } from "@/tutorials/scenarios";

interface CalloutProps {
  type?: "info" | "warn";
  children: React.ReactNode;
}

export function Callout({ type = "info", children }: CalloutProps) {
  const label = type === "warn" ? "Nota" : "Info";
  return (
    <aside
      role="note"
      aria-label={type === "warn" ? "Advertencia" : "Información"}
      className={cn("tut-callout", type === "warn" && "warn")}
    >
      <div className="tut-callout-label">{label}</div>
      <div className="tut-callout-body">{children}</div>
    </aside>
  );
}

interface NextStepProps {
  to: string;
  children: React.ReactNode;
}

export function NextStep({ to, children }: NextStepProps) {
  return (
    <div className="tut-next">
      <Link to={`/tutorial/${to}`}>
        <span>{children}</span>
        <span className="arrow" aria-hidden>
          →
        </span>
      </Link>
    </div>
  );
}

interface OverleafRefProps {
  /** Sección del Overleaf de donde proviene la ecuación (sin el símbolo §). */
  sec: string;
  /** Marca de revisión [R-n]/[S-n] si la ecuación pertenece a la revisión
   * jun-2026; linkea a la agenda OVERLEAF_CHANGES.md del repo web. */
  tag?: string;
}

/** Cita de procedencia de una ecuación: el documento matemático (Overleaf) es
 * la referencia normativa del modelo. Se cita por sección —los números de
 * ecuación del Overleaf son automáticos e inestables— y, si corresponde, por
 * la marca de revisión. */
export function OverleafRef({ sec, tag }: OverleafRefProps) {
  return (
    <div className="tut-eqref">
      Overleaf · §{sec}
      {tag && (
        <>
          {" · "}
          <a
            href={`https://github.com/lgayozo/titirilquen-web/blob/main/docs/OVERLEAF_CHANGES.md`}
            target="_blank"
            rel="noreferrer"
          >
            [{tag}]
          </a>
        </>
      )}
    </div>
  );
}

interface DocLinkProps {
  path: string;
  children: React.ReactNode;
}

export function DocLink({ path, children }: DocLinkProps) {
  return (
    <a
      href={`https://github.com/lehyt2163/Titirilquen${path}`}
      target="_blank"
      rel="noreferrer"
    >
      {children}
    </a>
  );
}

interface LoadScenarioProps {
  /** Id en TUTORIAL_SCENARIOS (src/tutorials/scenarios.ts). */
  id: string;
  children: React.ReactNode;
}

/** Botón «cargar escenario» de las actividades guiadas (F-02): aplica el
 * estado inicial de la actividad a los stores (desde los defaults, no desde la
 * config viva — reproducible) y navega al módulo. Si había un resultado, el
 * banner de staleness del módulo lo señala. */
export function LoadScenario({ id, children }: LoadScenarioProps) {
  const navigate = useNavigate();
  const scenario = TUTORIAL_SCENARIOS[id];
  if (!scenario) return null;
  const onClick = () => {
    const { sim, landUse } = scenario.build();
    if (sim) useSimulationStore.getState().replaceConfig(sim);
    if (landUse) useLandUseStore.getState().setConfig(() => landUse);
    navigate(scenario.to);
  };
  return (
    <button type="button" onClick={onClick} className="tut-load">
      ▶ {children}
    </button>
  );
}

export const mdxComponents = {
  Callout,
  NextStep,
  DocLink,
  OverleafRef,
  LoadScenario,
  MSAFlowchart,
  CoupledFlowchart,
  a: (props: React.AnchorHTMLAttributes<HTMLAnchorElement>) => {
    if (props.href && props.href.startsWith("/")) {
      return (
        <Link to={props.href} className={props.className}>
          {props.children}
        </Link>
      );
    }
    return <a {...props} target="_blank" rel="noreferrer" />;
  },
};
