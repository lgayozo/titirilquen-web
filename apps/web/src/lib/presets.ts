/**
 * Presets de ciudad y de política.
 *
 * Eran un espejo a mano de `titirilquen_core.presets`: unos 77 valores que
 * había que mover en dos lugares cada vez que se recalibraba. Hoy se generan.
 *
 * La regla de siempre sigue vigente y ahora tiene test en el core
 * (`test_presets.py`): los presets declaran valores ABSOLUTOS, no diferencias
 * contra el default. Si una política omite un parámetro, aplicarla NO lo
 * restaura — hereda el del escenario vigente, y eso ya causó cuatro incidentes.
 */

export { CITY_PRESETS, POLICY_PRESETS } from "@/lib/gen/presets.gen";
export type {
  CityPresetName,
  CityPresetValues,
  PolicyPresetName,
  PolicyPresetValues,
} from "@/lib/gen/presets.gen";
