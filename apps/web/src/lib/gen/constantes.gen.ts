// GENERADO por packages/titirilquen_core/tools/genera_contrato.py — NO EDITAR.
// Para cambiar algo de acá, cambiá el núcleo Python y corré `npm run sync:core`.

/** Orden canónico de los modos: define el orden de las series en toda
 *  figura y el layout del cubo `demanda_estrato`. */
export const MODOS = ["Auto", "Metro", "Bici", "Caminata"] as const;

export const MODOS_CON_TELETRABAJO = [
  "Auto",
  "Metro",
  "Bici",
  "Caminata",
  "Teletrabajo",
] as const;

/** Sobre estos tiempos el modo deja de ser una alternativa considerada
 *  (min). Son supuestos del modelo de elección, no parámetros. */
export const CORTE_CAMINATA_MIN = 30.0;
export const CORTE_BICI_MIN = 45.0;

/** Especificación `umbrales="suaves"`: pendiente del corte CMNL (1/min),
 *  umbral de dominancia del metro y su pendiente (1/min generalizado).
 *  Ver `constantes.OMEGA_CORTE_SUAVE` y siguientes. */
export const OMEGA_CORTE_SUAVE = 0.5;
export const A_DOMINANCIA_METRO = 1.2;
export const OMEGA_DOMINANCIA_METRO = 0.25;

/** Valor social del tiempo ($/hora-pasajero), Precios Sociales del SNI.
 *  Se actualiza cada año. */
export const VOT_SOCIAL_CLP_HORA = 3338.0;

/** Viajes por tour casa-trabajo-casa: el parking (costo por día) se
 *  reparte entre la ida y la vuelta. */
export const VIAJES_POR_TOUR = 2;

/** Viajes de conmutación por mes: mensualiza el logsum de transporte. */
export const VIAJES_MES = 44;

/** Tolerancia del loop acoplado ($/hogar-mes sobre la brecha de T/λ_h,
 *  D10): ver `constantes.TOL_ACOPLADO_CLP_MES`. */
export const TOL_ACOPLADO_CLP_MES = 100.0;

/** Tope de vueltas del loop acoplado: default y cota en todos los
 *  consumidores (D-61). Ver `constantes.VUELTAS_ACOPLADO_MAX`. */
export const VUELTAS_ACOPLADO_MAX = 10;

/** Fracción de la capacidad real sobre la que se evalúa la BPR del auto
 *  (capacidad práctica, D6): ver `constantes.FACTOR_CAPACIDAD_PRACTICA`. */
export const FACTOR_CAPACIDAD_PRACTICA = 0.8;

/** Nombre del wheel que el worker de Pyodide instala. Cambia con la
 *  versión del core; tenerlo acá evita que quede hardcodeado y viejo. */
export const WHEEL_FILENAME = "titirilquen_core-0.2.0-py3-none-any.whl";
