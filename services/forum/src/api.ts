/**
 * Observer HTTP API client. SWR-friendly fetcher + tight types matching
 * the observer's read-paths.
 */

const BASE = import.meta.env.VITE_OBSERVER_URL ?? "/api";

export async function fetcher<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export async function postCommand(body: Record<string, unknown>): Promise<void> {
  const r = await fetch(`${BASE}/commands`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`POST /commands ${r.status}: ${detail}`);
  }
}

// ── types ────────────────────────────────────────────────────────────

export interface Pod {
  pod_id: string;
  display_role: string;
  image_strategy: "code" | "adopted";
  runtime_status: "running" | "stopped" | "not_yet_spawned";
  agent_state: "idle" | "thinking" | "blocked" | "stuck";
  main_image: string | null;
  admitted: boolean;
  public_url: string | null;
  last_seen: string;
}

export interface Proclamation {
  seq: number;
  text: string;
  issued_at: string;
  status: "open" | "completed";
  summary: string | null;
  completed_at: string | null;
  placeholder_decision_id: string | null;
}

export interface Ballot {
  voter: string;
  choice: "yes" | "no" | "abstain";
  comment: string | null;
  cast_at: string;
}

export interface Proposal {
  proposal_id: string;
  kind: string;
  proposer: string;
  strategy: string;
  summary: string;
  payload: unknown;
  eligible_voters: string[];
  deadline: string;
  outcome: "open" | "approved" | "rejected" | "expired";
  opened_at: string;
  closed_at: string | null;
  ballots: Ballot[];
}

export interface Council {
  council_id: string;
  topic: string;
  participants: string[];
  private: boolean;
  needs_augustus: boolean;
  status: "open" | "closed";
  opened_at: string;
  closed_at: string | null;
  summary: string | null;
  decision_id: string | null;
}

export interface CouncilMessage {
  seq: number;
  from_pod: string;
  body: string;
  sent_at: string;
}

export interface Decision {
  decision_id: string;
  title: string;
  body: string | null;
  affected: string[];
  origin: { kind: string; id: string };
  status: "placeholder" | "sealed";
  created_at: string;
  sealed_at: string | null;
}

export interface Call {
  src_pod: string;
  dst_pod: string;
  method: string;
  path: string;
  status: number | null;
  latency_ms: number | null;
  observed_at: string;
}

export interface EndpointRow {
  pod_id: string;
  method: string;
  path: string;
  annotation: string | null;
  first_seen: string;
  last_seen: string;
}

export interface ActivityRow {
  event_id: string;
  event_type: string;
  payload: string;
  occurred_at: string;
}

export interface InboxBallot {
  kind: "ballot";
  proposal_id: string;
  proposal_kind: string;
  summary: string;
  strategy: string;
  deadline: string;
}
export interface InboxStuck {
  kind: "stuck";
  pod_id: string;
  display_role: string;
}
export interface InboxCouncil {
  kind: "council";
  council_id: string;
  topic: string;
  participants: string[];
}
export type InboxItem = InboxBallot | InboxStuck | InboxCouncil;

// ── SSE ──────────────────────────────────────────────────────────────

export function streamUrl(): string {
  return `${BASE}/stream`;
}
