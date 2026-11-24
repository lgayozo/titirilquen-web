import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

/**
 * «¿por qué?» plegable (B3). La regla del rediseño: un texto en pantalla no
 * pasa de ~25 palabras; lo que explica el porqué va aquí, cerrado, y la
 * explicación larga vive en el tutorial. `<details>` nativo: abre con teclado
 * y se anuncia a lectores de pantalla.
 */
export function PorQue({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const { t } = useTranslation("common");
  return (
    <details className={cn("porque", className)}>
      <summary>{t("porque")}</summary>
      <div className="porque-body">{children}</div>
    </details>
  );
}
