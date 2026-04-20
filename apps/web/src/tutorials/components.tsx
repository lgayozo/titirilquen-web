import { Link } from "react-router-dom";
import { AlertCircle, Info, ArrowRight } from "lucide-react";

import { cn } from "@/lib/cn";

interface CalloutProps {
  type?: "info" | "warn";
  children: React.ReactNode;
}

export function Callout({ type = "info", children }: CalloutProps) {
  const styles =
    type === "warn"
      ? "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
      : "border-sky-300 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200";
  const Icon = type === "warn" ? AlertCircle : Info;
  return (
    <aside
      role="note"
      aria-label={type === "warn" ? "Advertencia" : "Información"}
      className={cn("my-4 flex gap-2 rounded-lg border p-3 text-sm", styles)}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="flex-1 [&>p:first-child]:mt-0 [&>p:last-child]:mb-0">{children}</div>
    </aside>
  );
}

interface NextStepProps {
  to: string;
  children: React.ReactNode;
}

export function NextStep({ to, children }: NextStepProps) {
  return (
    <div className="mt-8 flex justify-end">
      <Link
        to={`/tutorial/${to}`}
        className="inline-flex items-center gap-1 rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-300"
      >
        {children}
        <ArrowRight className="h-4 w-4" aria-hidden />
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
      className="underline decoration-dotted underline-offset-2"
    >
      {children}
    </a>
  );
}

/**
 * Componentes expuestos al MDXProvider. Las claves deben coincidir con los
 * nombres de los componentes usados en los `.mdx`.
 */
export const mdxComponents = {
  Callout,
  NextStep,
  DocLink,
  a: (props: React.AnchorHTMLAttributes<HTMLAnchorElement>) => {
    // Enlaces internos con React Router
    if (props.href && props.href.startsWith("/")) {
      return (
        <Link to={props.href} className={props.className ?? "underline"}>
          {props.children}
        </Link>
      );
    }
    return <a {...props} className={props.className ?? "underline"} target="_blank" rel="noreferrer" />;
  },
  h1: (p: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 {...p} className="mb-4 mt-6 text-2xl font-bold tracking-tight" />
  ),
  h2: (p: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 {...p} className="mb-2 mt-6 text-lg font-semibold" />
  ),
  h3: (p: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 {...p} className="mb-1 mt-4 text-sm font-semibold uppercase tracking-wide text-slate-500" />
  ),
  p: (p: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p {...p} className="my-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300" />
  ),
  ul: (p: React.HTMLAttributes<HTMLUListElement>) => (
    <ul {...p} className="my-3 list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300" />
  ),
  ol: (p: React.HTMLAttributes<HTMLOListElement>) => (
    <ol {...p} className="my-3 list-decimal space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300" />
  ),
  li: (p: React.HTMLAttributes<HTMLLIElement>) => <li {...p} />,
  code: (p: React.HTMLAttributes<HTMLElement>) => (
    <code
      {...p}
      className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.85em] dark:bg-slate-800"
    />
  ),
  pre: (p: React.HTMLAttributes<HTMLPreElement>) => (
    <pre
      {...p}
      className="my-4 overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100 dark:bg-slate-950"
    />
  ),
  table: (p: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="my-3 overflow-x-auto">
      <table {...p} className="w-full border-collapse text-sm" />
    </div>
  ),
  th: (p: React.HTMLAttributes<HTMLTableCellElement>) => (
    <th {...p} className="border-b border-slate-300 px-2 py-1 text-left font-semibold dark:border-slate-700" />
  ),
  td: (p: React.HTMLAttributes<HTMLTableCellElement>) => (
    <td {...p} className="border-b border-slate-100 px-2 py-1 dark:border-slate-800" />
  ),
};
