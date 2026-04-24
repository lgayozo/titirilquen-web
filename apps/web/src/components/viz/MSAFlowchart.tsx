import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Flowchart, type FlowEdge, type FlowNode } from "@/components/viz/Flowchart";

const CENTER_X = 220;
const NODE_W = 300;
const NODE_H = 52;
const Y0 = 40;
const DY = 88;

/**
 * Diagrama interactivo del Método de Promedios Sucesivos (MSA).
 * Hover sobre cada nodo muestra la fórmula correspondiente.
 * Botón ▶ reproduce el ciclo paso a paso.
 */
export function MSAFlowchart() {
  const { t } = useTranslation("simulator");

  const nodes: FlowNode[] = useMemo(
    () => [
      {
        id: "initial",
        num: 1,
        label: t("flowchart.msa.initial"),
        x: CENTER_X,
        y: Y0,
        w: NODE_W,
        h: NODE_H,
        kind: "start",
        tooltip: {
          title: t("flowchart.msa.initial_title"),
          description: t("flowchart.msa.initial_desc"),
          formula: String.raw`t^{(0)}_m = d / v_m`,
          ref: { path: "equilibrium/msa.py", label: "run_msa · iter=0" },
        },
      },
      {
        id: "logit",
        num: 2,
        label: t("flowchart.msa.logit"),
        x: CENTER_X,
        y: Y0 + DY,
        w: NODE_W,
        h: NODE_H,
        tooltip: {
          title: t("flowchart.msa.logit_title"),
          description: t("flowchart.msa.logit_desc"),
          formula: String.raw`P(m) = \frac{e^{V_m}}{\sum_j e^{V_j}}`,
          ref: { path: "demand/choice.py", label: "logit_multinomial" },
        },
      },
      {
        id: "congestion",
        num: 3,
        label: t("flowchart.msa.congestion"),
        x: CENTER_X,
        y: Y0 + 2 * DY,
        w: NODE_W,
        h: NODE_H,
        tooltip: {
          title: t("flowchart.msa.congestion_title"),
          description: t("flowchart.msa.congestion_desc"),
          formula: String.raw`t_i = t_0 \left(1 + \alpha \left(\frac{q_i}{N_p \cdot Q}\right)^\beta\right)`,
          ref: { path: "supply/car.py", label: "bpr_time" },
        },
      },
      {
        id: "smooth",
        num: 4,
        label: t("flowchart.msa.smooth"),
        x: CENTER_X,
        y: Y0 + 3 * DY,
        w: NODE_W,
        h: NODE_H,
        tooltip: {
          title: t("flowchart.msa.smooth_title"),
          description: t("flowchart.msa.smooth_desc"),
          formula: String.raw`T^{(n+1)} = \frac{1}{n+1} T_{\text{obs}}^{(n)} + \frac{n}{n+1} T^{(n)}`,
          ref: { path: "equilibrium/msa.py", label: "iter_msa" },
        },
      },
      {
        id: "check",
        num: 5,
        label: t("flowchart.msa.check"),
        x: CENTER_X,
        y: Y0 + 4 * DY,
        w: NODE_W,
        h: 56,
        kind: "decision",
        tooltip: {
          title: t("flowchart.msa.check_title"),
          description: t("flowchart.msa.check_desc"),
          formula: String.raw`\|T^{(n+1)} - T^{(n)}\|_\infty < \epsilon`,
        },
      },
      {
        id: "done",
        num: 6,
        label: t("flowchart.msa.done"),
        x: CENTER_X,
        y: Y0 + 5 * DY,
        w: NODE_W,
        h: NODE_H,
        kind: "end",
        tooltip: {
          title: t("flowchart.msa.done_title"),
          description: t("flowchart.msa.done_desc"),
        },
      },
    ],
    [t]
  );

  const edges: FlowEdge[] = useMemo(() => {
    const rightEdgeX = CENTER_X + NODE_W / 2; // 370
    const feedbackX = rightEdgeX + 38; // 408
    const checkY = Y0 + 4 * DY;
    const logitY = Y0 + DY;
    return [
      { from: "initial", to: "logit" },
      { from: "logit", to: "congestion" },
      { from: "congestion", to: "smooth" },
      { from: "smooth", to: "check" },
      {
        from: "check",
        to: "done",
        label: t("flowchart.msa.yes"),
        labelX: CENTER_X + 14,
        labelY: checkY + 64,
      },
      // Feedback NO: desde lado derecho del decision, sube, vuelve a logit
      {
        from: "check",
        to: "logit",
        feedback: true,
        d: `M ${rightEdgeX} ${checkY} L ${feedbackX} ${checkY} L ${feedbackX} ${logitY} L ${rightEdgeX} ${logitY}`,
        label: t("flowchart.msa.no"),
        labelX: feedbackX + 16,
        labelY: (checkY + logitY) / 2,
      },
    ];
  }, [t]);

  const playback = ["initial", "logit", "congestion", "smooth", "check", "done"];

  return (
    <Flowchart
      nodes={nodes}
      edges={edges}
      width={460}
      height={Y0 + 5 * DY + 40}
      playbackSteps={playback}
      ariaLabel={t("flowchart.msa.aria")}
    />
  );
}
