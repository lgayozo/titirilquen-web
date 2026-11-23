import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fmtDecimal } from "@/lib/modos";
import type { AprendizajeDict } from "@/lib/types";

interface AprendizajeTrayectoriaProps {
  resultado: AprendizajeDict;
  /** Índice de la réplica a dibujar, o `null` para el promedio. */
  replica?: number | null;
  className?: string;
}

const AXIS_STYLE = {
  fontFamily: "var(--font-fig)",
  fontSize: 12,
  letterSpacing: "0.04em",
};

/** Cuota del modo mejor, día a día: el promedio de las réplicas o una sola.
 *
 *  Las dos referencias son las que dan sentido a la curva: P* es lo que
 *  elegiría quien conoce los tiempos —el techo— y ½ es tirar una moneda. Una
 *  trayectoria que baja de ½ significa que la persona aprendió al revés.
 *
 *  **Por qué el promedio es suave y una réplica no.** Cada historia es una
 *  función escalonada: la creencia sólo cambia los días en que la persona usa
 *  el modo, y el tratamiento de E1 cae la primera vez que lo ELIGE, que no es
 *  el mismo día en todas. El promedio mezcla escalones desfasados y sale
 *  continuo. Por eso la réplica se dibuja con `stepAfter`: con `monotone`
 *  recharts interpolaría el salto y la figura sugeriría un ajuste gradual que
 *  el modelo no tiene. */
export function AprendizajeTrayectoria({
  resultado,
  replica = null,
  className,
}: AprendizajeTrayectoriaProps) {
  const { t } = useTranslation("simulator");

  const datos = useMemo(() => {
    const serie =
      replica === null
        ? resultado.s_por_dia
        : (resultado.p_replicas[replica] ?? resultado.s_por_dia);
    return serie.map((s, i) => ({ dia: i + 1, s }));
  }, [resultado.s_por_dia, resultado.p_replicas, replica]);
  const { corto, medio } = resultado.ventanas;
  const pEstrella = resultado.caso.p_verdadera;

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart
          data={datos}
          margin={{ top: 8, right: 16, bottom: 28, left: 8 }}
        >
          {/* Las ventanas de análisis, para leer la curva por tramos. */}
          <ReferenceArea
            x1={1}
            x2={corto.hasta}
            fill="var(--accent)"
            fillOpacity={0.05}
          />
          <ReferenceArea
            x1={medio.desde}
            x2={medio.hasta}
            fill="var(--accent)"
            fillOpacity={0.025}
          />
          <CartesianGrid stroke="var(--rule)" strokeDasharray="2 4" />
          <XAxis
            dataKey="dia"
            tick={AXIS_STYLE}
            stroke="var(--muted)"
            label={{
              value: t("aprendizaje.fig.eje_dia"),
              position: "insideBottom",
              offset: -16,
              style: AXIS_STYLE,
            }}
          />
          <YAxis
            domain={[0, 1]}
            tick={AXIS_STYLE}
            stroke="var(--muted)"
            tickFormatter={(v: number) => fmtDecimal(v, 1)}
            label={{
              value: t("aprendizaje.fig.eje_cuota"),
              angle: -90,
              position: "insideLeft",
              style: AXIS_STYLE,
            }}
          />
          {/* P*: el techo informado. */}
          <ReferenceLine
            y={pEstrella}
            stroke="var(--muted)"
            strokeDasharray="5 4"
            label={{
              value: `P* = ${fmtDecimal(pEstrella, 3)}`,
              position: "right",
              style: AXIS_STYLE,
            }}
          />
          {/* ½: la moneda al aire. */}
          <ReferenceLine y={0.5} stroke="var(--ink)" strokeDasharray="1 4" />
          <Tooltip
            formatter={(v: number) => [
              fmtDecimal(v, 3),
              replica === null
                ? t("aprendizaje.fig.cuota")
                : t("aprendizaje.fig.cuota_una"),
            ]}
            labelFormatter={(d: number) => `${t("aprendizaje.fig.dia")} ${d}`}
            contentStyle={{
              border: "1px solid var(--rule)",
              borderRadius: 8,
              background: "var(--panel)",
              fontFamily: "var(--font-fig)",
              fontSize: 12,
            }}
          />
          <Line
            type={replica === null ? "monotone" : "stepAfter"}
            dataKey="s"
            stroke="var(--accent)"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
