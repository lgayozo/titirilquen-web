import { useTranslation } from "react-i18next";

import { cn } from "@/lib/cn";

interface EsperaMetroProps {
  /** Espera por celda, del snapshot. El CBD vale 0 (es el destino). */
  esperaPorCelda: readonly number[];
  /** Frecuencia operativa del equilibrio (tph). */
  fOp: number;
  /** Saturación del andén: carga máxima / (frec_max · capacidad_tren). */
  rhoAnden: number;
  /** α y β de la BPR de andén, para mostrar el recargo que producen. */
  alphaAnden: number;
  betaAnden: number;
  className?: string;
}

/** Bajo esta variación relativa la espera se considera constante en el espacio
 *  y no se ofrece perfil. 2 % es holgado frente al ruido de coma flotante y muy
 *  por debajo de lo que se distingue en una barra de 200 px. */
const UMBRAL_VARIACION = 0.02;

/** Bajo este recargo el canal de andén se considera inactivo. 1 % es dos órdenes
 *  de magnitud más que el 0,02 % de la ciudad por defecto y sigue muy por debajo
 *  de lo que cambia una decisión de modo. */
const UMBRAL_ANDEN = 0.01;

/**
 * La espera del metro y los dos canales que la producen.
 *
 * Antes esto era un perfil espacial dentro de la cinta del hero, y con la ciudad
 * por defecto dibujaba **una recta**: 201 celdas con dos valores distintos
 * (5,27 y 5,28 min) y 0,0 % de variación. No era un defecto del dibujo sino del
 * modelo — y por eso el dibujo no servía. La espera es
 *
 *     espera = 30/f_op × (1 + α·ρ^β)
 *
 * con una sola frecuencia para toda la línea (el primer término es constante) y
 * un recargo de andén que con la población por defecto vale **1,0002**.
 *
 * Los dos canales se muestran por separado y NO como una resta contra la cifra
 * observada. La razón es concreta: el MSA promedia TIEMPOS entre iteraciones, así
 * que la espera del snapshot arrastra iteraciones con frecuencias menores y no
 * coincide con `30/f_op` de la última. Medido en la corrida por defecto: f_op
 * 5,017 da 5,980 min mientras la espera observada es 6,179. Esos 0,199 min son
 * del promediado, no del andén —que aporta 0,001—, y restarlos se los habría
 * atribuido al canal equivocado.
 */
export function EsperaMetro({
  esperaPorCelda,
  fOp,
  rhoAnden,
  alphaAnden,
  betaAnden,
  className,
}: EsperaMetroProps) {
  const { t } = useTranslation("simulator");

  // El CBD tiene espera 0 por construcción: incluirlo mostraría variación
  // espacial donde solo hay un destino.
  const conEspera = esperaPorCelda.filter((v) => v > 0);
  if (conEspera.length === 0) return null;

  const min = Math.min(...conEspera);
  const max = Math.max(...conEspera);
  const variacion = max > 0 ? (max - min) / max : 0;
  const hayPerfil = variacion > UMBRAL_VARIACION;

  const mediaIntervalo = fOp > 0 ? 30 / fOp : 0;
  const factorAnden = 1 + alphaAnden * Math.pow(rhoAnden, betaAnden);
  const recargoAnden = factorAnden - 1;
  const andenActivo = recargoAnden > UMBRAL_ANDEN;

  return (
    <div className={cn("espera-metro", className)}>
      <div className="espera-cifra">
        <span className="espera-valor">{max.toFixed(1)}</span>
        <span className="espera-unidad">{t("espera.min")}</span>
        <span className="espera-titulo">{t("espera.titulo")}</span>
      </div>

      <div className="espera-desglose">
        <Parte
          etiqueta={t("espera.base")}
          valor={`${mediaIntervalo.toFixed(1)} ${t("espera.min")}`}
          nota={t("espera.base_nota", { f: fOp.toFixed(1) })}
        />
        <Parte
          etiqueta={t("espera.anden")}
          valor={`× ${factorAnden.toFixed(4)}`}
          nota={
            andenActivo
              ? t("espera.anden_activo", {
                  pct: (recargoAnden * 100).toFixed(0),
                  rho: rhoAnden.toFixed(2),
                })
              : t("espera.anden_inactivo", { rho: rhoAnden.toFixed(2) })
          }
          apagado={!andenActivo}
        />
      </div>

      <p className="espera-pie">
        {hayPerfil
          ? t("espera.varia", {
              min: min.toFixed(1),
              max: max.toFixed(1),
              pct: (variacion * 100).toFixed(0),
            })
          : t("espera.constante")}{" "}
        {t("espera.msa_nota")}
      </p>
    </div>
  );
}

function Parte({
  etiqueta,
  valor,
  nota,
  apagado = false,
}: {
  etiqueta: string;
  valor: string;
  nota: string;
  apagado?: boolean;
}) {
  return (
    <div className={cn("espera-parte", apagado && "espera-parte-apagada")}>
      <div className="espera-parte-top">
        <span className="espera-parte-label">{etiqueta}</span>
        <span className="espera-parte-valor">{valor}</span>
      </div>
      <p className="espera-parte-nota">{nota}</p>
    </div>
  );
}
