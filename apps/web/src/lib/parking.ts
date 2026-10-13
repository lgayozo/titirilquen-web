import { VIAJES_POR_TOUR } from "@/lib/gen/constantes.gen";

type T = (k: string, o?: Record<string, unknown>) => string;

/** `costo_parking` es un costo POR DÍA: se paga una vez por tour
 *  casa-trabajo-casa. El modelo simula un viaje de ida representativo, que
 *  carga `1/VIAJES_POR_TOUR` de ese pago. Se muestran los dos números para que
 *  la conversión quede a la vista y nadie lea el por-viaje como un descuento. */
export function fmtParking(porDia: number, t: T): string {
  const peso = (v: number) => `$${v.toLocaleString("es-CL")}`;
  return t("economy_params.parking_desglose", {
    ns: "simulator",
    dia: peso(porDia),
    viaje: peso(porDia / VIAJES_POR_TOUR),
  });
}
