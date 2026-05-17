/** Spec/09 §6.6 — Roll entry. One line: timestamp · rubric verb ·
 * summary. The Glance right rail and the Witness left column are
 * the same data typeset two ways. */

import type { ReactNode } from "react";
import { useFolio } from "../folio";
import type { ActivityRow } from "../api";
import { C } from "../theme";

/** Maps event_type → (rubric verb, route-target). Unknown events
 * collapse to their snake_case as-is. */
const RUBRIC: Record<string, string> = {
  ProclamationIssued: "PROCLAIMED",
  ProclamationCompleted: "CONCLUDED",
  ProposalOpened: "PROPOSED",
  ProposalClosed: "BALLOTED",
  BallotCast: "VOTED",
  CouncilOpened: "CONVENED",
  CouncilClosed: "ADJOURNED",
  MessagePosted: "SPOKE",
  DecisionPlaceholderCreated: "DRAFTED",
  DecisionSealed: "SEALED",
  PodContainerStarted: "SPAWNED",
  PodAdmitted: "ADMITTED",
  PodRenamed: "RENAMED",
  PodExited: "EXITED",
  PodImageSwapped: "ADOPTED",
  PodMarkedStuck: "STUCK",
  PodHealthChanged: "WAKED",
  EndpointObserved: "OBSERVED",
  EndpointAnnotated: "ANNOTATED",
  AgentBooted: "BOOTED",
  AgentSessionStarted: "WAKED",
  AgentTurnStarted: "THINKING",
  AgentTurnEnded: "RESTED",
  PodCharterLoaded: "LOADED",
  StateReset: "WIPED",
  PodsNuked: "NUKED",
};

export function RollEntry({ row }: { row: ActivityRow }) {
  const folio = useFolio();
  const payload = parsePayload(row.payload);
  const rubric = RUBRIC[row.event_type] ?? row.event_type.toUpperCase();
  const { summary, target } = render(row.event_type, payload);

  return (
    <button
      type="button"
      onClick={() => target && folio.open(target)}
      disabled={!target}
      style={{
        display: "grid",
        gridTemplateColumns: "56px 100px 1fr",
        gap: 8,
        padding: "4px 6px",
        background: "transparent",
        border: "none",
        textAlign: "left",
        cursor: target ? "pointer" : "default",
        width: "100%",
        color: C.ink,
        fontSize: "var(--t-roll)",
        fontFamily: "var(--f-body)",
        alignItems: "baseline",
        borderBottom: `0.25px solid ${C.wash}`,
      }}
    >
      <span className="c-mono c-faded">{formatTime(row.occurred_at)}</span>
      <span className="c-rubric">{rubric}</span>
      <span>{summary}</span>
    </button>
  );
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function parsePayload(s: string): Record<string, unknown> {
  if (!s) return {};
  if (typeof s === "object") return s as Record<string, unknown>;
  try {
    return JSON.parse(s);
  } catch {
    return {};
  }
}

function render(
  eventType: string,
  p: Record<string, unknown>,
): { summary: ReactNode; target?: import("../folio").EntityRef } {
  const podLabel = p.pod_id ? String(p.pod_id).slice(0, 16) : "";
  switch (eventType) {
    case "ProclamationIssued": {
      const seq = String(p.proclamation_seq ?? p.seq ?? "?");
      const text = String(p.text ?? "");
      return {
        summary: `№ ${seq} — ${truncate(text, 80)}`,
        target: { kind: "proclamation", id: seq },
      };
    }
    case "PodContainerStarted":
    case "PodAdmitted":
    case "AgentBooted":
    case "PodCharterLoaded":
    case "PodMarkedStuck":
    case "AgentTurnStarted":
    case "AgentTurnEnded":
    case "AgentSessionStarted":
      return {
        summary: `${podLabel}${p.reason ? ` — ${p.reason}` : ""}`,
        target: p.pod_id
          ? { kind: "pod", id: String(p.pod_id) }
          : undefined,
      };
    case "ProposalOpened":
    case "ProposalClosed":
    case "BallotCast":
      return {
        summary: String(p.summary ?? p.proposal_id ?? "(proposal)"),
        target: p.proposal_id
          ? { kind: "proposal", id: String(p.proposal_id) }
          : undefined,
      };
    case "CouncilOpened":
    case "CouncilClosed":
    case "MessagePosted":
      return {
        summary: String(p.topic ?? p.council_id ?? p.body ?? "(council)"),
        target: p.council_id
          ? { kind: "council", id: String(p.council_id) }
          : undefined,
      };
    case "DecisionPlaceholderCreated":
    case "DecisionSealed":
      return {
        summary: String(p.title ?? p.decision_id ?? "(decision)"),
        target: p.decision_id
          ? { kind: "decision", id: String(p.decision_id) }
          : undefined,
      };
    case "EndpointObserved":
    case "EndpointAnnotated":
      return {
        summary: `${p.method ?? "GET"} ${p.path ?? "?"} on ${podLabel}`,
        target:
          p.pod_id && p.method && p.path
            ? {
                kind: "endpoint",
                id: `${p.pod_id}|${p.method}|${p.path}`,
                label: `${p.method} ${p.path}`,
              }
            : undefined,
      };
    case "StateReset":
      return { summary: "state wiped" };
    case "PodsNuked":
      return {
        summary: `${p.nuked_count ?? 0} pod(s) torn down`,
      };
    default:
      return { summary: truncate(JSON.stringify(p), 80) };
  }
}

function truncate(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, n - 1) + "…";
}
