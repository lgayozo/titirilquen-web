/**
 * Oferta de vivienda S(i) para las visualizaciones del frontend — **espejo de
 * presentación** de `land_use/supply.py:generar_oferta` (+ `_discretizar`).
 *
 * El vector S entero que realmente se resuelve lo genera el core Python; acá
 * reproducimos la *forma* para que la vista previa (`CityShapePreview`) y la
 * distribución de resultados (`StratumDistribution`) compartan exactamente la
 * misma envolvente. Antes el resultado ignoraba S y dibujaba una ciudad plana
 * que no coincidía con la figura de la forma elegida.
 */

import type { FormaOferta } from "@/lib/types-v2";

/** Pesos w(d) del perfil de oferta (sin discretizar). Mismo modelo que el core. */
export function cityShapeWeights(
  forma: FormaOferta,
  L: number,
  CBD: number,
  sigmaFrac: number,
  formaParam: number,
): number[] {
  const semi = Math.max(1, Math.min(CBD, L - 1 - CBD));
  const sigma = Math.max(sigmaFrac * semi, 1e-6);
  const w = new Array<number>(L).fill(0);
  for (let i = 0; i < L; i++) {
    const d = Math.abs(i - CBD);
    let v = 0;
    switch (forma) {
      case "normal":
        v = Math.exp(-0.5 * (d / sigma) ** 2);
        break;
      case "uniforme":
        v = 1;
        break;
      case "exponencial":
        v = Math.exp(-d / sigma);
        break;
      case "meseta":
        v = Math.exp(-((d / sigma) ** 8));
        break;
      case "bimodal": {
        const sp = sigma * 0.5;
        const sep = formaParam * semi;
        v =
          Math.exp(-0.5 * ((i - (CBD - sep)) / sp) ** 2) +
          Math.exp(-0.5 * ((i - (CBD + sep)) / sp) ** 2);
        break;
      }
      case "valle":
        v = (d / semi) ** (2 * sigmaFrac);
        break;
    }
    w[i] = v;
  }
  w[CBD] = 0; // no se construye sobre el CBD
  return w;
}

/**
 * Vector de oferta entero S(i) con Σ S = N y CBD vacío, por el método del mayor
 * residuo. Espejo de `_discretizar` del core. Para uso en visualizaciones.
 */
export function supplyVector(
  forma: FormaOferta,
  L: number,
  CBD: number,
  sigmaFrac: number,
  formaParam: number,
  N: number,
): number[] {
  const w = cityShapeWeights(forma, L, CBD, sigmaFrac, formaParam);
  let total = w.reduce((a, b) => a + b, 0);
  if (total <= 0) {
    for (let i = 0; i < L; i++) w[i] = i === CBD ? 0 : 1;
    total = w.reduce((a, b) => a + b, 0);
  }
  const target = w.map((x) => (x / total) * N);
  const S = target.map((x) => Math.floor(x));
  let resto = N - S.reduce((a, b) => a + b, 0);
  const orden = target
    .map((x, i) => ({ frac: i === CBD ? -1 : x - Math.floor(x), i }))
    .sort((a, b) => b.frac - a.frac);
  for (let k = 0; resto > 0 && k < orden.length; k++, resto--) {
    S[orden[k]!.i] = (S[orden[k]!.i] ?? 0) + 1;
  }
  return S;
}

/**
 * Distribución espacial de hogares por estrato: N[h,i] = round(S_i · Q[h,i]).
 * Devuelve, por celda, la lista de estratos presentes (1..H) repetida según el
 * conteo — el formato que consume `StratumDistribution`. Reproduce la
 * envolvente real de la ciudad (oferta × asignación), no una ciudad plana.
 */
export function reconstructParcelas(
  Q: readonly (readonly number[])[],
  S: readonly number[],
): number[][] {
  const nStrata = Q.length;
  const I = S.length;
  const parcelas: number[][] = Array.from({ length: I }, () => []);
  for (let i = 0; i < I; i++) {
    for (let h = 0; h < nStrata; h++) {
      const cnt = Math.round((S[i] ?? 0) * (Q[h]?.[i] ?? 0));
      for (let k = 0; k < cnt; k++) parcelas[i]!.push(h + 1);
    }
  }
  return parcelas;
}
