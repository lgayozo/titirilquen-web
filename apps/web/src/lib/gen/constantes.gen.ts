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

/** Consumo de bencina de un auto en movimiento (MESPIVU, tabla
 *  13.1.1-3): velocidad (km/h) → ml/km. Se interpola linealmente y fuera
 *  del rango se queda en el extremo. Ver `operacion_vehicular.py`. */
export const CONSUMO_AUTO_VELOCIDAD_KMH = [
  10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0,
] as const;
export const CONSUMO_AUTO_ML_KM = [
  205.6, 110.2, 81.3, 68.9, 63.7, 62.4, 64.0, 67.5, 73.1, 80.1,
] as const;

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
