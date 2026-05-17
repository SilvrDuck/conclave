/** Spec/09 §3 — Witness perspective. Two-column codex spread.
 *
 * Left (≈60%): Codex of Proclamations. Each proclamation rendered
 * through the Proclamation component (only place that owns the drop
 * cap), with indented descendants below (councils, proposals,
 * decisions).
 *
 * Right (≈40%): Focused entity. Per §3 "never becomes empty": if
 * nothing is clicked yet, we show the most-recently-active entity
 * from the current proclamation (latest decision, falling back to
 * latest council, falling back to latest proposal). */

import { useEffect, useState } from "react";
import useSWR from "swr";
import {
  fetcher,
  type Proclamation as ProclamationT,
  type Council,
  type Decision,
  type Proposal,
} from "../api";
import { Proclamation } from "../components/Proclamation";
import { Plate } from "../components/Plate";
import { Phylactery } from "../components/Phylactery";
import { ProposalCartouche } from "../components/ProposalCartouche";
import { EntityLink } from "../components/EntityLink";
import type { EntityRef } from "../folio";
import { C } from "../theme";

export function Witness() {
  const { data: procs } = useSWR<ProclamationT[]>(
    "/state/proclamations",
    fetcher,
    { refreshInterval: 5000 },
  );
  const { data: councils } = useSWR<Council[]>("/state/councils", fetcher, {
    refreshInterval: 5000,
  });
  const { data: decisions } = useSWR<Decision[]>("/state/decisions", fetcher, {
    refreshInterval: 5000,
  });
  const { data: proposals } = useSWR<Proposal[]>("/state/proposals", fetcher, {
    refreshInterval: 5000,
  });

  const [focused, setFocused] = useState<EntityRef | null>(null);

  // §3 — right column never empty: when nothing user-clicked, pick
  // the latest descendant of the most-recent proclamation as the
  // initial focus.
  useEffect(() => {
    if (focused !== null) return;
    const top = (procs ?? [])[0];
    if (!top) return;
    const seqStr = String(top.seq);
    const isFor = (origin: unknown) =>
      typeof origin === "object" &&
      origin !== null &&
      (origin as { kind?: string }).kind === "proclamation" &&
      (origin as { id?: string }).id === seqStr;
    const latestDecision = (decisions ?? []).find((d) => isFor(d.origin));
    if (latestDecision) {
      setFocused({ kind: "decision", id: latestDecision.decision_id });
      return;
    }
    const latestCouncil = (councils ?? [])[0];
    if (latestCouncil) {
      setFocused({ kind: "council", id: latestCouncil.council_id });
      return;
    }
    const latestProposal = (proposals ?? [])[0];
    if (latestProposal) {
      setFocused({ kind: "proposal", id: latestProposal.proposal_id });
    }
  }, [focused, procs, decisions, councils, proposals]);

  return (
    <div
      style={{
        flex: 1,
        display: "grid",
        gridTemplateColumns: "minmax(0, 60fr) minmax(0, 40fr)",
        height: "100%",
        minHeight: 0,
      }}
    >
      {/* Left — Codex */}
      <div
        style={{
          overflowY: "auto",
          padding: "24px 32px",
          borderRight: `0.5px solid ${C.inkFaded}`,
        }}
      >
        {(procs ?? []).length === 0 ? (
          <p
            className="c-faded"
            style={{ fontStyle: "italic", textAlign: "center", marginTop: 64 }}
          >
            the record is bare. proclaim, and pages will fill.
          </p>
        ) : (
          (procs ?? []).map((p, idx) => {
            const seqStr = String(p.seq);
            const isFor = (origin: unknown) =>
              typeof origin === "object" &&
              origin !== null &&
              (origin as { kind?: string }).kind === "proclamation" &&
              (origin as { id?: string }).id === seqStr;
            const ds = (decisions ?? []).filter((d) => isFor(d.origin));
            const cs = (councils ?? []).filter(
              (c) =>
                c.decision_id != null &&
                ds.some((d) => d.decision_id === c.decision_id),
            );
            // Proposals don't carry proclamation_seq yet; surface
            // open proposals only on the latest proclamation. Filed
            // as kanban follow-up.
            const ps = idx === 0 ? (proposals ?? []) : [];
            return (
              <ProclamationPage
                key={p.seq}
                proc={p}
                councils={cs}
                decisions={ds}
                proposals={ps}
                isLast={idx === (procs ?? []).length - 1}
                next={(procs ?? [])[idx + 1] ?? null}
                onFocus={setFocused}
              />
            );
          })
        )}
      </div>

      {/* Right — focused entity */}
      <div
        style={{
          overflowY: "auto",
          padding: "24px 28px",
          background: C.parchment,
        }}
      >
        {focused ? (
          <FocusedEntity target={focused} />
        ) : (
          <p
            className="c-faded"
            style={{ fontStyle: "italic", textAlign: "center", marginTop: 96 }}
          >
            the record's reflection is empty.
          </p>
        )}
      </div>
    </div>
  );
}

function ProclamationPage({
  proc,
  councils,
  decisions,
  proposals,
  isLast,
  next,
  onFocus,
}: {
  proc: ProclamationT;
  councils: Council[];
  decisions: Decision[];
  proposals: Proposal[];
  isLast: boolean;
  next: ProclamationT | null;
  onFocus: (ref: EntityRef) => void;
}) {
  return (
    <section style={{ marginBottom: 48 }}>
      <Proclamation proclamation={proc} fadeIn={false} />

      {(councils.length + decisions.length + proposals.length) > 0 ? (
        <ul
          style={{
            marginTop: 16,
            paddingLeft: 24,
            listStyle: "none",
            borderLeft: `0.5px solid ${C.wash}`,
          }}
        >
          {proposals.map((p) => (
            <li key={p.proposal_id} style={{ padding: "4px 0" }}>
              <button
                type="button"
                onClick={() => onFocus({ kind: "proposal", id: p.proposal_id })}
                className="c-link"
                style={{ background: "transparent", border: "none", padding: 0 }}
              >
                <span className="c-rubric">PROPOSED</span>{" "}
                <span>{p.summary || p.proposal_id}</span>
              </button>
            </li>
          ))}
          {councils.map((c) => (
            <li key={c.council_id} style={{ padding: "4px 0" }}>
              <button
                type="button"
                onClick={() => onFocus({ kind: "council", id: c.council_id })}
                className="c-link"
                style={{ background: "transparent", border: "none", padding: 0 }}
              >
                <span className="c-rubric">CONVENED</span> <span>{c.topic}</span>
              </button>
              {c.needs_augustus ? (
                <span
                  className="c-display-sm c-gold"
                  style={{ marginLeft: 8, fontSize: 10 }}
                >
                  ◆ needs Augustus
                </span>
              ) : null}
            </li>
          ))}
          {decisions.map((d) => (
            <li key={d.decision_id} style={{ padding: "4px 0" }}>
              <button
                type="button"
                onClick={() => onFocus({ kind: "decision", id: d.decision_id })}
                className="c-link"
                style={{ background: "transparent", border: "none", padding: 0 }}
              >
                <span className="c-rubric">
                  {d.status === "sealed" ? "SEALED" : "DRAFTED"}
                </span>{" "}
                <span>{d.title}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {proc.status === "completed" && proc.summary ? (
        <div
          style={{
            marginTop: 12,
            padding: "8px 12px",
            background: C.vellum,
            borderLeft: `2px solid ${C.gold}`,
            fontSize: 13,
          }}
        >
          <span className="c-display-sm c-gold">CONCLUDED</span> {proc.summary}
        </div>
      ) : null}
      {/* §3 catchword — italic first-word of the next proclamation,
       * leading the eye down the codex like a printer's catchword. */}
      {!isLast && next ? (
        <div
          aria-hidden
          style={{
            marginTop: 24,
            paddingTop: 8,
            borderTop: `0.5px dashed ${C.inkFaded}`,
            textAlign: "right",
            fontStyle: "italic",
            fontSize: 13,
            color: C.inkFaded,
          }}
        >
          {next.text.split(/\s+/)[0]} …
        </div>
      ) : null}
    </section>
  );
}

function FocusedEntity({ target }: { target: EntityRef }) {
  if (target.kind === "proposal") return <FocusedProposal id={target.id} />;
  if (target.kind === "decision") return <FocusedDecision id={target.id} />;
  if (target.kind === "council") return <FocusedCouncil id={target.id} />;
  return null;
}

function FocusedProposal({ id }: { id: string }) {
  const { data } = useSWR<Proposal[]>("/state/proposals", fetcher);
  const p = data?.find((r) => r.proposal_id === id);
  if (!p) return <p className="c-faded">Proposal not found.</p>;
  return <ProposalCartouche proposal={p} />;
}

function FocusedDecision({ id }: { id: string }) {
  const { data } = useSWR<Decision[]>("/state/decisions", fetcher);
  const d = data?.find((r) => r.decision_id === id);
  if (!d) return <p className="c-faded">Decision not found.</p>;
  return (
    <Plate
      decisionId={d.decision_id}
      title={d.title}
      body={d.body}
      affected={d.affected}
      status={d.status}
      sealedAt={d.sealed_at}
    />
  );
}

function FocusedCouncil({ id }: { id: string }) {
  const { data: councils } = useSWR<Council[]>("/state/councils", fetcher);
  const { data: msgs } = useSWR<
    Array<{ seq: number; from_pod: string; body: string; sent_at: string }>
  >(`/state/councils/${id}/messages`, fetcher, { refreshInterval: 3000 });
  const c = councils?.find((r) => r.council_id === id);
  if (!c) return <p className="c-faded">Council not found.</p>;
  return (
    <article>
      <header style={{ marginBottom: 12 }}>
        <h3 className="c-display" style={{ margin: 0, fontSize: 14 }}>
          {c.topic}
        </h3>
        {c.needs_augustus ? (
          <div
            className="c-display-sm c-gold"
            style={{ marginTop: 4, fontSize: 11 }}
          >
            ◆ needs Augustus
          </div>
        ) : null}
        <div className="c-faded" style={{ fontSize: 12, marginTop: 4 }}>
          {c.participants.map((podId, i) => (
            <span key={podId}>
              {i > 0 ? ", " : ""}
              <EntityLink kind="pod" id={podId}>
                {podId.slice(0, 12)}
              </EntityLink>
            </span>
          ))}
        </div>
      </header>
      {(msgs ?? []).map((m) => (
        <Phylactery
          key={m.seq}
          sender={m.from_pod}
          body={m.body}
          sentAt={m.sent_at}
        />
      ))}
      {c.summary && c.status === "closed" ? (
        <div
          style={{
            marginTop: 16,
            padding: "10px 14px",
            background: C.vellum,
            borderTop: `1px solid ${C.gold}`,
            borderBottom: `1px solid ${C.gold}`,
          }}
        >
          <span className="c-display-sm c-gold">SEALED</span>
          <p style={{ marginTop: 4 }}>{c.summary}</p>
          {c.decision_id ? (
            <EntityLink kind="decision" id={c.decision_id}>
              {c.decision_id}
            </EntityLink>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
