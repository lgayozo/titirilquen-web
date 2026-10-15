import { VIAJES_POR_TOUR } from "@/lib/gen/constantes.gen";

type T = (k: string, o?: Record<string, unknown>) => string;

/** `costo_parking` es un costo POR DÍA: se paga una vez por tour
 *  casa-trabajo-casa. El modelo simula un viaje de ida representativo, que
 *  carga `1/VIAJES_POR_TOUR` de ese pago. Se muestran los dos números para que
 *  la conversión quede a la vista y nadie lea el por-viaje como un descuento. */
/** El por-viaje solo, para la línea secundaria de un KPI angosto: el valor
 *  por día va como cifra principal (B4: los dos juntos desbordaban 96 px). */
export function fmtParkingPorViaje(porDia: number, t: T): string {
  return t("economy_params.parking_por_viaje", {
    ns: "simulator",
    viaje: `$${(porDia / VIAJES_POR_TOUR).toLocaleString("es-CL")}`,
  });
}

export function fmtParking(porDia: number, t: T): string {
  const peso = (v: number) => `$${v.toLocaleString("es-CL")}`;
  return t("economy_params.parking_desglose", {
    ns: "simulator",
    dia: peso(porDia),
    viaje: peso(porDia / VIAJES_POR_TOUR),
  });
}
