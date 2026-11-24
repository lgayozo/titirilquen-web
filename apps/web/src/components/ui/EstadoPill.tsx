import {
  Circle,
  CircleCheck,
  CircleX,
  LoaderCircle,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/cn";

/** Estados del cálculo que distingue la interfaz. «sin_converger» cubre
 *  también la corrida sin criterio de parada: ninguna de las dos es un
 *  equilibrio verificado. */
export type Estado = "listo" | "calculando" | "ok" | "sin_converger" | "error";

const ICONO: Record<Estado, LucideIcon> = {
  listo: Circle,
  calculando: LoaderCircle,
  ok: CircleCheck,
  sin_converger: TriangleAlert,
  error: CircleX,
};

const CLASE: Record<Estado, string | null> = {
  listo: null,
  calculando: "estado-pill--alerta",
  ok: "estado-pill--ok",
  sin_converger: "estado-pill--error",
  error: "estado-pill--error",
};

/**
 * Pastilla con el estado del cálculo. Lleva siempre ícono y texto: el color
 * solo no basta para distinguir un equilibrio de una corrida que no cumplió
 * el criterio de parada. Sin `role="status"`: la barra de estado de la
 * página ya anuncia el veredicto y dos regiones vivas lo dirían dos veces.
 */
export function EstadoPill({
  estado,
  children,
}: {
  estado: Estado;
  children: React.ReactNode;
}) {
  const Icono = ICONO[estado];
  return (
    <span className={cn("estado-pill", CLASE[estado])}>
      <Icono
        aria-hidden
        className={cn(estado === "calculando" && "animate-spin")}
      />
      {children}
    </span>
  );
}
