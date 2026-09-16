import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { FlowProfile } from "@/components/viz/FlowProfile";

interface CorridorFlowFigureProps {
  /** Flujo acumulado del corredor por celda — la serie que se grafica. */
  flujo: readonly number[];
  /** Demanda ORIGINADA por celda. Si viene, se habilita la animación: el flujo
   *  del corredor es exactamente su suma acumulada por lado hacia el CBD, así
   *  que cada frame del barrido es una suma parcial REAL del modelo y no una
   *  interpolación entre dos imágenes. Sin ella la figura es estática. */
  demanda?: readonly number[] | null;
  /** Unidad de la serie, para el tooltip (la caminata no tiene capacidad). */
  unidad?: string;
  /** Capacidad en la misma unidad que `flujo`. */
  capacidad?: number | null;
  capacidadLabel?: string;
  color: string;
  largoKm: number;
  label?: string;
  height?: number;
}

/** Duración del barrido de periferia a CBD. */
const DURACION_MS = 1800;

/**
 * Reconstruye la acumulación con el frente del barrido en la celda `k` (medida
 * desde cada periferia). Las celdas ya barridas muestran su acumulado parcial;
 * las que faltan, su demanda originada. Con `k = cbd` el resultado ES el flujo
 * del corredor.
 *
 * Replica `demora_auto_tramo` / `demora_bici_tramo` del core: cumsum de
 * izquierda a derecha en el lado izquierdo, de derecha a izquierda en el
 * derecho, y el CBD en cero (no genera viajes hacia sí mismo).
 */
export function acumulacionParcial(
  demanda: readonly number[],
  cbd: number,
  k: number,
): number[] {
  const N = demanda.length;
  const out = new Array<number>(N).fill(0);

  let acc = 0;
  for (let i = 0; i < cbd; i++) {
    if (i <= k) {
      acc += demanda[i] ?? 0;
      out[i] = acc;
    } else {
      out[i] = demanda[i] ?? 0;
    }
  }

  acc = 0;
  for (let i = N - 1; i > cbd; i--) {
    if (i >= N - 1 - k) {
      acc += demanda[i] ?? 0;
      out[i] = acc;
    } else {
      out[i] = demanda[i] ?? 0;
    }
  }

  out[cbd] = 0;
  return out;
}

/**
 * Perfil de carga del corredor con animación opcional de cómo se acumula.
 *
 * La figura anterior graficaba la demanda ORIGINADA por celda y la rotulaba con
 * la capacidad del corredor: dos magnitudes que difieren ~60× (52 contra 3.050
 * veh/h en la config por defecto), así que un corredor con v/c = 1,38 se leía
 * como si estuviera al 2%. Acá se grafica el flujo acumulado, que es el
 * numerador correcto del v/c, y la animación explica de dónde sale.
 */
export function CorridorFlowFigure({
  flujo,
  demanda,
  capacidad = null,
  capacidadLabel,
  unidad,
  color,
  largoKm,
  label,
  height,
}: CorridorFlowFigureProps) {
  const { t } = useTranslation("simulator");
  const cbd = Math.floor(flujo.length / 2);
  const animable = !!demanda && demanda.length === flujo.length;

  // `null` = mostrar el resultado final; un número = frente del barrido.
  const [frente, setFrente] = useState<number | null>(null);
  const rafRef = useRef<number | null>(null);

  const detener = useCallback(() => {
    if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;
  }, []);

  // Cortar la animación en curso si cambia la serie (p.ej. el usuario cambió de
  // modo): sus frames pertenecen a la serie vieja.
  useEffect(() => {
    detener();
    setFrente(null);
  }, [flujo, detener]);

  useEffect(() => detener, [detener]);

  const animar = useCallback(() => {
    if (!animable) return;
    detener();
    const reduce = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    )?.matches;
    if (reduce) {
      setFrente(null);
      return;
    }
    const inicio = performance.now();
    const paso = (ahora: number) => {
      const p = Math.min((ahora - inicio) / DURACION_MS, 1);
      if (p >= 1) {
        setFrente(null); // vuelve a la serie final exacta
        rafRef.current = null;
        return;
      }
      setFrente(Math.round(p * cbd));
      rafRef.current = requestAnimationFrame(paso);
    };
    rafRef.current = requestAnimationFrame(paso);
  }, [animable, cbd, detener]);

  const serie = useMemo(() => {
    if (frente == null || !demanda) return flujo as number[];
    return acumulacionParcial(demanda, cbd, frente);
  }, [frente, demanda, flujo, cbd]);

  // Escala fija al máximo final: si se recalculara por frame, las barras se
  // verían del mismo alto durante todo el barrido y la acumulación no se notaría.
  const yMax = useMemo(() => Math.max(...flujo, 1), [flujo]);

  return (
    <div>
      <FlowProfile
        flows={serie}
        largoKm={largoKm}
        color={color}
        label={label}
        yMax={yMax}
        capacity={capacidad}
        capacityLabel={capacidadLabel}
        unidad={unidad}
        height={height}
      />
      {animable && (
        <div className="mt-1.5 flex flex-wrap items-baseline gap-2">
          <button
            type="button"
            onClick={animar}
            className="btn"
            disabled={frente != null}
          >
            {t("sandbox.flow_replay")}
          </button>
          <span className="text-[11px] leading-snug text-muted">
            {t("sandbox.flow_replay_hint")}
          </span>
        </div>
      )}
    </div>
  );
}
