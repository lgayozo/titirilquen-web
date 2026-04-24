import { Link } from "react-router-dom";

import { CoupledFlowchart } from "@/components/viz/CoupledFlowchart";
import { MSAFlowchart } from "@/components/viz/MSAFlowchart";
import { cn } from "@/lib/cn";

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

export const mdxComponents = {
  Callout,
  NextStep,
  DocLink,
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
