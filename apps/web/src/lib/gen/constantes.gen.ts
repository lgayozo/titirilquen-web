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

/** Valor social del tiempo ($/hora-pasajero), Precios Sociales del SNI.
 *  Se actualiza cada año. */
export const VOT_SOCIAL_CLP_HORA = 3338.0;

/** Nombre del wheel que el worker de Pyodide instala. Cambia con la
 *  versión del core; tenerlo acá evita que quede hardcodeado y viejo. */
export const WHEEL_FILENAME = "titirilquen_core-0.2.0-py3-none-any.whl";
