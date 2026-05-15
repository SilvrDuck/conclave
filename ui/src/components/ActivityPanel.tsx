import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import {
  listAdrs,
  listMembers,
  listOpenProposals,
} from "../api/observer";
import type { Adr, Member, Proposal } from "../api/observer";

// Poll fast for a heartbeat feel.
const REFRESH_MS = 2000;
const MAX_EVENTS = 30;

type Event = {
  at: string; // local hh:mm:ss
  kind: "member" | "proposal" | "adr" | "system";
  text: string;
};

function snapshot(label: string, map: Map<string, unknown>) {
  return `${label}=${[...map.keys()].sort().join(",")}`;
}

export function ActivityPanel() {
  const { data: members } = useSWR<Member[]>("activity.members", listMembers, {
    refreshInterval: REFRESH_MS,
  });
  const { data: proposals } = useSWR<Proposal[]>(
    "activity.proposals",
    listOpenProposals,
    { refreshInterval: REFRESH_MS },
  );
  const { data: adrs } = useSWR<Adr[]>("activity.adrs", listAdrs, {
    refreshInterval: REFRESH_MS,
  });

  const memberMap = useRef<Map<string, Member>>(new Map());
  const proposalMap = useRef<Map<string, Proposal>>(new Map());
  const adrSet = useRef<Set<string>>(new Set());
  const seeded = useRef<boolean>(false);
  const [events, setEvents] = useState<Event[]>([]);

  function push(kind: Event["kind"], text: string) {
    setEvents((prev) => {
      const at = new Date().toLocaleTimeString();
      const next = [{ at, kind, text }, ...prev];
      return next.slice(0, MAX_EVENTS);
    });
  }

  // Diff members.
  useEffect(() => {
    if (!members) return;
    const next = new Map(members.map((m) => [m.name, m] as const));
    if (!seeded.current) {
      memberMap.current = next;
      return;
    }
    for (const [name, m] of next) {
      const prev = memberMap.current.get(name);
      if (!prev) {
        push(
          "member",
          `${name} admitted` + (m.status === "admitted" ? "" : ` (${m.status})`),
        );
      } else if (prev.status !== m.status) {
        push("member", `${name} → ${m.status}`);
      }
    }
    for (const name of memberMap.current.keys()) {
      if (!next.has(name)) push("member", `${name} removed`);
    }
    memberMap.current = next;
  }, [members]);

  // Diff proposals (open list shrinks/grows).
  useEffect(() => {
    if (!proposals) return;
    const next = new Map(proposals.map((p) => [p.id, p] as const));
    if (!seeded.current) {
      proposalMap.current = next;
      return;
    }
    for (const [id, p] of next) {
      if (!proposalMap.current.has(id)) {
        const target =
          (p.payload["pod_name"] as string | undefined) ?? p.kind;
        push(
          "proposal",
          `${p.proposer} → propose ${p.kind}(${target}) [${p.strategy}]`,
        );
      }
    }
    for (const id of proposalMap.current.keys()) {
      if (!next.has(id)) {
        const old = proposalMap.current.get(id)!;
        const target =
          (old.payload["pod_name"] as string | undefined) ?? old.kind;
        push("proposal", `${old.proposer}'s ${old.kind}(${target}) closed`);
      }
    }
    proposalMap.current = next;
  }, [proposals]);

  // Diff ADRs (new only).
  useEffect(() => {
    if (!adrs) return;
    const ids = new Set(adrs.map((a) => a.id));
    if (!seeded.current) {
      adrSet.current = ids;
      return;
    }
    for (const a of adrs) {
      if (!adrSet.current.has(a.id)) {
        push("adr", `ADR ${a.id}: ${a.title}`);
      }
    }
    adrSet.current = ids;
  }, [adrs]);

  // After first tick of all three sources, start emitting deltas.
  useEffect(() => {
    if (seeded.current) return;
    if (members !== undefined && proposals !== undefined && adrs !== undefined) {
      seeded.current = true;
      push("system", "watching…");
    }
  }, [members, proposals, adrs]);

  const styles = colorFor;

  return (
    <aside
      style={{
        marginTop: "1rem",
        padding: "0.75rem 1rem",
        background: "#f7f0dc",
        border: "1px solid var(--stone)",
        borderRadius: "4px",
        maxHeight: "260px",
        overflowY: "auto",
        fontFamily: '"JetBrains Mono", "Fira Code", monospace',
        fontSize: "0.82rem",
        lineHeight: 1.5,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "0.5rem",
        }}
      >
        <strong style={{ color: "var(--ink)" }}>Recent activity</strong>
        <span style={{ color: "var(--stone)", fontSize: "0.78rem" }}>
          {members?.length ?? 0} members · {proposals?.length ?? 0} open ·{" "}
          {adrs?.length ?? 0} ADRs · polling {REFRESH_MS / 1000}s
        </span>
      </div>
      {events.length === 0 ? (
        <div style={{ color: "var(--stone)", fontStyle: "italic" }}>
          {snapshot("members", memberMap.current)} ·{" "}
          {snapshot("open", proposalMap.current)} · {adrSet.current.size} ADRs
          — issue a proclamation to start.
        </div>
      ) : (
        <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
          {events.map((e, i) => (
            <li
              key={i}
              style={{
                color: styles(e.kind),
                opacity: i === 0 ? 1 : Math.max(0.55, 1 - i * 0.025),
              }}
            >
              <span style={{ color: "var(--stone)" }}>{e.at}</span>{" "}
              <span style={{ fontWeight: 600 }}>[{e.kind}]</span> {e.text}
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}

function colorFor(kind: Event["kind"]): string {
  switch (kind) {
    case "member":
      return "var(--ochre)";
    case "proposal":
      return "var(--ink)";
    case "adr":
      return "var(--gold)";
    case "system":
      return "var(--stone)";
  }
}
