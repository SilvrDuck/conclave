/** Spec/09 §2 — Glance perspective. Full-bleed ReactFlow canvas
 * with Pod Cartouches, the Roll right rail (last 200 named events),
 * and the Stuck Tray fold-out bottom-left.
 *
 * Empty state: a single torn-leaf insert in EB Garamond italic
 * 20px sits vertically centred on parchment. No counters, no
 * first-run wizard. */

import { useMemo } from "react";
import useSWR from "swr";
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import { fetcher, postCommand, type Pod, type Call, type ActivityRow } from "../api";
import { PodCartouche } from "../components/PodCartouche";
import { RollEntry } from "../components/RollEntry";
import { StuckTray } from "../components/StuckTray";
import { WaxSeal } from "../components/WaxSeal";
import { useFolio } from "../folio";
import { C } from "../theme";
import { useState } from "react";

const nodeTypes = { cartouche: PodCartoucheNode };

interface PodCartoucheData extends Record<string, unknown> {
  pod: Pod;
  simulator: boolean;
}

function PodCartoucheNode(props: NodeProps) {
  const data = props.data as PodCartoucheData;
  return (
    <>
      <Handle type="target" position={Position.Left} />
      <PodCartouche pod={data.pod} simulator={data.simulator} />
      <Handle type="source" position={Position.Right} />
    </>
  );
}

export function Glance() {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher, {
    refreshInterval: 3000,
  });
  const { data: calls } = useSWR<Call[]>("/state/calls", fetcher, {
    refreshInterval: 4000,
  });
  const { data: activity } = useSWR<ActivityRow[]>("/state/activity", fetcher, {
    refreshInterval: 4000,
  });

  const { nodes, edges } = useMemo(
    () => buildGraph(pods ?? [], calls ?? []),
    [pods, calls],
  );

  const folio = useFolio();
  const empty = (pods ?? []).length === 0;

  return (
    <div
      style={{
        position: "relative",
        flex: 1,
        display: "grid",
        gridTemplateColumns: "1fr 240px",
        height: "100%",
        minHeight: 0,
      }}
    >
      <div style={{ position: "relative", borderRight: `0.5px solid ${C.inkFaded}` }}>
        {empty ? (
          <EmptyTornLeaf />
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
            onNodeClick={(_, node) =>
              folio.open({ kind: "pod", id: (node.data as PodCartoucheData).pod.pod_id })
            }
          >
            <Background color={C.wash} gap={24} />
            <Controls position="bottom-right" />
          </ReactFlow>
        )}
        <StuckTray pods={pods ?? []} />
      </div>

      <aside
        style={{
          background: C.parchment,
          borderLeft: `0.5px solid ${C.inkFaded}`,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <header
          style={{
            padding: "10px 12px",
            borderBottom: `0.5px solid ${C.inkFaded}`,
          }}
        >
          <h2 className="c-display" style={{ margin: 0, fontSize: 13 }}>
            The Roll
          </h2>
        </header>
        <div style={{ flex: 1, overflowY: "auto", padding: "4px 8px" }}>
          {(activity ?? []).slice(0, 200).map((row) => (
            <RollEntry key={row.event_id} row={row} />
          ))}
          {(activity ?? []).length === 0 ? (
            <p className="c-faded" style={{ fontStyle: "italic", margin: 12 }}>
              the record is bare.
            </p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

function buildGraph(pods: Pod[], calls: Call[]): { nodes: Node[]; edges: Edge[] } {
  if (pods.length === 0) return { nodes: [], edges: [] };
  // Simple circular layout — ReactFlow's auto-layout is left out
  // intentionally; force-directed shifting on every refresh is a
  // motion violation per §9.
  const r = 220;
  const cx = 360;
  const cy = 280;
  const simulatorRe = /sim|oracle|environment/i;
  const nodes: Node[] = pods.map((p, i) => {
    const theta = (2 * Math.PI * i) / pods.length;
    return {
      id: p.pod_id,
      type: "cartouche",
      position: { x: cx + r * Math.cos(theta), y: cy + r * Math.sin(theta) },
      data: { pod: p, simulator: simulatorRe.test(p.display_role) },
    };
  });
  const seen = new Set<string>();
  const edges: Edge[] = [];
  // dedupe by (src,dst) — Roll keeps the temporal detail
  for (const c of calls) {
    const key = `${c.src_pod}|${c.dst_pod}`;
    if (seen.has(key)) continue;
    seen.add(key);
    if (c.src_pod === c.dst_pod) continue;
    edges.push({
      id: key,
      source: c.src_pod,
      target: c.dst_pod,
      animated: false,
    });
  }
  return { nodes, edges };
}

function EmptyTornLeaf() {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(false);
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        gap: 16,
        padding: 24,
      }}
    >
      <p
        style={{
          fontFamily: "var(--f-body)",
          fontStyle: "italic",
          fontSize: 20,
          color: C.inkFaded,
          margin: 0,
          textAlign: "center",
        }}
      >
        Speak, and the conclave begins.
      </p>
      <textarea
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Issue a proclamation…"
        rows={4}
        style={{
          width: 640,
          maxWidth: "80vw",
          background: C.vellum,
          color: C.ink,
          border: `0.5px solid ${C.inkFaded}`,
          padding: 16,
          fontFamily: "var(--f-body)",
          fontSize: 16,
          lineHeight: 1.5,
        }}
      />
      <WaxSeal
        letter="P"
        label="Proclaim"
        disabled={pending || !text.trim()}
        onClick={async () => {
          setPending(true);
          try {
            await postCommand({
              kind: "IssueProclamation",
              text: text.trim(),
            });
            setText("");
          } finally {
            setPending(false);
          }
        }}
      />
    </div>
  );
}
