import { useMemo } from "react";
import useSWR from "swr";
import { ReactFlow, Background, Controls, Edge, Node, MarkerType } from "@xyflow/react";
import { Box, Flex, Heading, Text, Badge, Separator } from "@radix-ui/themes";
import { Call, Pod, ActivityRow, fetcher } from "../api";
import { usePeek, type EntityRef } from "../components/PeekContext";
import { Linkified } from "../components/Linkified";

export function Glance({ onPodClick }: { onPodClick: (pod_id: string) => void }) {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher, { refreshInterval: 5000 });
  const { data: calls } = useSWR<Call[]>("/state/calls?since_seconds=120", fetcher, {
    refreshInterval: 5000,
  });
  const { data: activity } = useSWR<ActivityRow[]>("/state/activity?limit=40", fetcher, {
    refreshInterval: 5000,
  });
  const { push } = usePeek();

  const { nodes, edges } = useMemo(() => buildGraph(pods ?? [], calls ?? []), [pods, calls]);

  return (
    <Flex className="h-full">
      <Box className="flex-1 relative">
        {nodes.length === 0 ? (
          <EmptyGlance />
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            onNodeClick={(_, n) => onPodClick(n.id)}
            colorMode="dark"
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
        <NodeLegend />
      </Box>
      <Box className="w-80 border-l border-slate-800 p-3 overflow-y-auto">
        <Heading size="3" mb="2">
          Activity
        </Heading>
        {(activity ?? []).length === 0 ? (
          <Text size="2" color="gray">
            (quiet)
          </Text>
        ) : (
          <Flex direction="column" gap="2">
            {(activity ?? []).map((a) => {
              const target = activityTarget(a);
              const onClick = target ? () => push(target) : undefined;
              return (
                <Box
                  key={a.event_id}
                  role={onClick ? "button" : undefined}
                  tabIndex={onClick ? 0 : undefined}
                  className={
                    "border-b border-slate-800 pb-2" +
                    (onClick ? " cursor-pointer hover:bg-slate-800/50 -mx-2 px-2 rounded focus:outline-none focus:ring-1 focus:ring-amber-500" : "")
                  }
                  onClick={onClick}
                  onKeyDown={
                    onClick
                      ? (e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            onClick();
                          }
                        }
                      : undefined
                  }
                >
                  <Flex gap="2" align="center">
                    <Badge color={badgeColor(a.event_type)} size="1">
                      {a.event_type}
                    </Badge>
                    <Text size="1" color="gray">
                      {formatTime(a.occurred_at)}
                    </Text>
                  </Flex>
                  <Text size="2" className="break-words">
                    <Linkified text={summarise(a)} />
                  </Text>
                </Box>
              );
            })}
          </Flex>
        )}
      </Box>
    </Flex>
  );
}

/** Pop-up legend for the pod-node colour code. Renders fixed inside
 * the graph viewport so the user can decode the colours without
 * leaving the Glance tab. (kanban #39) */
function NodeLegend() {
  return (
    <Box
      className="absolute right-3 bottom-3 z-10 rounded-md bg-slate-900/95 border border-slate-700 px-3 py-2 text-xs"
    >
      <Text size="1" weight="bold" as="div" className="mb-1">
        legend
      </Text>
      <Flex direction="column" gap="1">
        <Flex align="center" gap="2">
          <span style={legendSwatch("#22c55e")} /> running
        </Flex>
        <Flex align="center" gap="2">
          <span style={legendSwatch("#ef4444")} /> stopped
        </Flex>
        <Flex align="center" gap="2">
          <span style={legendSwatch("#f59e0b")} /> stuck (block-detector)
        </Flex>
        <Flex align="center" gap="2">
          <span style={legendSwatch("#475569", 0.6)} /> not yet spawned
        </Flex>
        <Separator size="2" my="1" />
        <Flex align="center" gap="2">
          <span style={legendDot("yellow")} /> thinking
        </Flex>
        <Flex align="center" gap="2">
          <span style={legendDot("orange")} /> blocked
        </Flex>
        <Flex align="center" gap="2">
          <span style={legendDot("green")} /> idle
        </Flex>
      </Flex>
    </Box>
  );
}

function legendSwatch(color: string, opacity = 1): React.CSSProperties {
  return {
    display: "inline-block",
    width: 10,
    height: 10,
    border: `2px solid ${color}`,
    borderRadius: 3,
    opacity,
  };
}

function legendDot(color: string): React.CSSProperties {
  const bg =
    color === "yellow"
      ? "#fbbf24"
      : color === "green"
        ? "#22c55e"
        : color === "orange"
          ? "#fb923c"
          : "#94a3b8";
  return {
    display: "inline-block",
    width: 8,
    height: 8,
    background: bg,
    borderRadius: 999,
  };
}

/** Derive the entity the user wants to peek when they click an
 * activity-feed row. Each event_type maps to its primary target. */
function activityTarget(a: ActivityRow): EntityRef | null {
  try {
    const p = JSON.parse(a.payload);
    switch (a.event_type) {
      case "ProclamationIssued":
      case "ProclamationCompleted":
        return p.proclamation_seq != null
          ? { kind: "proclamation", id: String(p.proclamation_seq) }
          : null;
      case "ProposalOpened":
      case "ProposalClosed":
      case "BallotCast":
        return p.proposal_id ? { kind: "proposal", id: p.proposal_id } : null;
      case "CouncilOpened":
      case "CouncilClosed":
        return p.council_id ? { kind: "council", id: p.council_id } : null;
      case "DecisionSealed":
        return p.decision_id ? { kind: "decision", id: p.decision_id } : null;
      case "PodContainerStarted":
      case "PodAdmitted":
      case "PodRenamed":
      case "PodExited":
      case "PodImageSwapped":
      case "PodMarkedStuck":
      case "AgentBooted":
      case "AgentSessionStarted":
      case "PodCharterLoaded":
        return p.pod_id ? { kind: "pod", id: p.pod_id } : null;
      default:
        return null;
    }
  } catch {
    return null;
  }
}

function EmptyGlance() {
  return (
    <Flex
      direction="column"
      align="center"
      justify="center"
      className="h-full text-slate-500"
    >
      <Heading size="4" weight="medium">
        Empty conclave
      </Heading>
      <Text size="2">Proclaim something above and the swarm begins.</Text>
    </Flex>
  );
}

function buildGraph(pods: Pod[], calls: Call[]): { nodes: Node[]; edges: Edge[] } {
  const radius = Math.max(160, pods.length * 30);
  const nodes: Node[] = pods.map((p, i) => {
    const angle = (i / Math.max(pods.length, 1)) * 2 * Math.PI;
    return {
      id: p.pod_id,
      type: "default",
      position: { x: Math.cos(angle) * radius + 320, y: Math.sin(angle) * radius + 240 },
      data: {
        label: (
          <Flex direction="column" align="center" gap="1">
            <Text size="2" weight="bold">
              {p.display_role}
            </Text>
            <Text size="1" color="gray">
              {p.image_strategy}
              {p.main_image ? ` • ${p.main_image}` : ""}
            </Text>
            <Badge color={agentBadgeColor(p.agent_state)} size="1">
              {p.agent_state}
            </Badge>
          </Flex>
        ),
      },
      style: nodeStyle(p),
    };
  });

  // Bucket calls into unique (src, dst) edges with counts.
  const counts = new Map<string, number>();
  for (const c of calls) {
    if (!c.src_pod || !c.dst_pod || c.src_pod === c.dst_pod) continue;
    const key = `${c.src_pod}→${c.dst_pod}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  const edges: Edge[] = [];
  for (const [key, count] of counts) {
    const [src, dst] = key.split("→");
    edges.push({
      id: key,
      source: src,
      target: dst,
      animated: true,
      label: `${count}`,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { strokeWidth: Math.min(1 + count / 4, 4) },
    });
  }
  return { nodes, edges };
}

function nodeStyle(p: Pod): React.CSSProperties {
  const base: React.CSSProperties = {
    padding: 8,
    borderRadius: 12,
    borderWidth: 2,
    width: 140,
    background: p.admitted ? "#1e293b" : "#0f172a",
    color: "#e2e8f0",
    borderColor: p.runtime_status === "running" ? "#22c55e" : "#475569",
  };
  if (p.runtime_status === "stopped") base.borderColor = "#ef4444";
  if (p.agent_state === "stuck") base.borderColor = "#f59e0b";
  if (!p.admitted) base.opacity = 0.6;
  return base;
}

function agentBadgeColor(s: Pod["agent_state"]): "green" | "yellow" | "orange" | "red" | "gray" {
  switch (s) {
    case "thinking":
      return "yellow";
    case "blocked":
      return "orange";
    case "stuck":
      return "red";
    case "idle":
      return "green";
    default:
      return "gray";
  }
}

function badgeColor(t: string): "green" | "red" | "blue" | "purple" | "gray" {
  if (t.includes("Sealed") || t === "PodAdmitted" || t.includes("Approved")) return "green";
  if (t.includes("Stuck") || t.includes("Exited")) return "red";
  if (t.includes("Proposal") || t.includes("Council")) return "blue";
  if (t.includes("Proclamation")) return "purple";
  return "gray";
}

function summarise(a: ActivityRow): string {
  try {
    const p = JSON.parse(a.payload);
    if (a.event_type === "ProclamationIssued") return p.text ?? "";
    if (a.event_type === "ProposalOpened")
      return `${p.kind} via ${p.strategy} — ${p.summary}`;
    if (a.event_type === "ProposalClosed") return `${p.outcome} — ${p.summary}`;
    if (a.event_type === "DecisionSealed") return p.title ?? p.decision_id;
    if (a.event_type === "PodAdmitted") return `${p.display_role} (${p.pod_id})`;
    if (a.event_type === "PodRenamed")
      return `${p.old_display_role ?? "?"} → ${p.new_display_role}`;
    if (a.event_type === "PodContainerStarted") return `${p.pod_id} (${p.mode})`;
    if (a.event_type === "CouncilOpened") return p.topic ?? "";
    if (a.event_type === "MessagePosted") return `${p.from_pod}: ${p.body}`;
    if (a.event_type === "BallotCast") return `${p.voter} → ${p.choice}`;
    return JSON.stringify(p).slice(0, 100);
  } catch {
    return a.payload.slice(0, 100);
  }
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString();
}
