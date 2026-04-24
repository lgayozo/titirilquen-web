import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { Flowchart, type FlowEdge, type FlowNode } from "@/components/viz/Flowchart";

const CENTER_X = 220;
const NODE_W = 300;
const NODE_H = 52;
const Y0 = 40;
const DY = 88;

/**
 * Diagrama del loop exterior suelo↔transporte. Cada iteración exterior
 * alterna la asignación de hogares (uso de suelo) con la corrida completa
 * de MSA (transporte). El criterio de parada compara `T` entre iteraciones.
 */
export function CoupledFlowchart() {
  const { t } = useTranslation("simulator");

  const nodes: FlowNode[] = useMemo(
    () => [
      {
        id: "config",
        num: 1,
        label: t("flowchart.coupled.config"),
        x: CENTER_X,
        y: Y0,
        w: NODE_W,
        h: NODE_H,
        kind: "start",
        tooltip: {
          title: t("flowchart.coupled.config_title"),
          description: t("flowchart.coupled.config_desc"),
        },
      },
      {
        id: "landuse",
        num: 2,
        label: t("flowchart.coupled.landuse"),
        x: CENTER_X,
        y: Y0 + DY,
        w: NODE_W,
        h: NODE_H,
        tooltip: {
          title: t("flowchart.coupled.landuse_title"),
          description: t("flowchart.coupled.landuse_desc"),
          formula: String.raw`Q_{h,i} = \frac{S_i \cdot e^{\beta \cdot u_{h,i}}}{\sum_h H_h \cdot e^{\beta \cdot u_{h,i}}}`,
          ref: { path: "land_use/equilibrium.py", label: "solve_logit" },
        },
      },
      {
        id: "assign",
        num: 3,
        label: t("flowchart.coupled.assign"),
        x: CENTER_X,
        y: Y0 + 2 * DY,
        w: NODE_W,
        h: NODE_H,
        tooltip: {
          title: t("flowchart.coupled.assign_title"),
          description: t("flowchart.coupled.assign_desc"),
          ref: { path: "land_use/allocation.py", label: "asignar_hogares_simple" },
        },
      },
      {
        id: "transport",
        num: 4,
        label: t("flowchart.coupled.transport"),
        x: CENTER_X,
        y: Y0 + 3 * DY,
        w: NODE_W,
        h: NODE_H,
        tooltip: {
          title: t("flowchart.coupled.transport_title"),
          description: t("flowchart.coupled.transport_desc"),
          formula: String.raw`T^{(k)} = \text{run\_msa}(\text{pop}^{(k)})`,
          ref: { path: "equilibrium/msa.py", label: "run_msa" },
        },
      },
      {
        id: "check",
        num: 5,
        label: t("flowchart.coupled.check"),
        x: CENTER_X,
        y: Y0 + 4 * DY,
        w: NODE_W,
        h: 56,
        kind: "decision",
        tooltip: {
          title: t("flowchart.coupled.check_title"),
          description: t("flowchart.coupled.check_desc"),
          formula: String.raw`\|T^{(k)} - T^{(k-1)}\|_\infty < \tau`,
        },
      },
      {
        id: "done",
        num: 6,
        label: t("flowchart.coupled.done"),
        x: CENTER_X,
        y: Y0 + 5 * DY,
        w: NODE_W,
        h: NODE_H,
        kind: "end",
        tooltip: {
          title: t("flowchart.coupled.done_title"),
          description: t("flowchart.coupled.done_desc"),
        },
      },
    ],
    [t]
  );

  const edges: FlowEdge[] = useMemo(() => {
    const rightEdgeX = CENTER_X + NODE_W / 2;
    const feedbackX = rightEdgeX + 38;
    const checkY = Y0 + 4 * DY;
    const landuseY = Y0 + DY;
    return [
      { from: "config", to: "landuse" },
      { from: "landuse", to: "assign" },
      { from: "assign", to: "transport" },
      { from: "transport", to: "check" },
      {
        from: "check",
        to: "done",
        label: t("flowchart.msa.yes"),
        labelX: CENTER_X + 14,
        labelY: checkY + 64,
      },
      {
        from: "check",
        to: "landuse",
        feedback: true,
        d: `M ${rightEdgeX} ${checkY} L ${feedbackX} ${checkY} L ${feedbackX} ${landuseY} L ${rightEdgeX} ${landuseY}`,
        label: t("flowchart.msa.no"),
        labelX: feedbackX + 16,
        labelY: (checkY + landuseY) / 2,
      },
    ];
  }, [t]);

  const playback = ["config", "landuse", "assign", "transport", "check", "done"];

  return (
    <Flowchart
      nodes={nodes}
      edges={edges}
      width={460}
      height={Y0 + 5 * DY + 40}
      playbackSteps={playback}
      ariaLabel={t("flowchart.coupled.aria")}
    />
  );
}
