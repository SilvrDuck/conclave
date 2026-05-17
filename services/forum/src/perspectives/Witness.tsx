/** Spec/09 §3 — Witness perspective. Two-column codex spread.
 *
 * Left (≈60%): Codex of Proclamations. Each proclamation is a real
 * page with a drop cap on its first paragraph, scribal numeral in the
 * gutter, body justified, and indented descendants below (councils,
 * proposals, decisions).
 *
 * Right (≈40%): Focused entity — whichever council, decision, or
 * proposal the user clicked from the left column. */

import { useState } from "react";
import useSWR from "swr";
import {
  fetcher,
  type Proclamation,
  type Council,
  type Decision,
  type Proposal,
} from "../api";
import { Linkified } from "../components/Linkified";
import { Plate } from "../components/Plate";
import { Phylactery } from "../components/Phylactery";
import { ProposalCartouche } from "../components/ProposalCartouche";
import { EntityLink } from "../components/EntityLink";
import type { EntityRef } from "../folio";
import { C } from "../theme";

export function Witness() {
  const { data: procs } = useSWR<Proclamation[]>(
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
          (procs ?? []).map((p) => (
            <ProclamationPage
              key={p.seq}
              proc={p}
              councils={(councils ?? []).filter(
                (c) =>
                  c.decision_id != null &&
                  decisions?.some(
                    (d) =>
                      d.decision_id === c.decision_id &&
                      (d.origin as { id?: string })?.id === String(p.seq),
                  ),
              )}
              decisions={(decisions ?? []).filter(
                (d) => (d.origin as { id?: string })?.id === String(p.seq),
              )}
              proposals={(proposals ?? []).filter(
                () =>
                  // Proposals don't yet carry proclamation_seq directly;
                  // include all open proposals on the most recent
                  // proclamation only.
                  p === procs?.[0],
              )}
              onFocus={setFocused}
            />
          ))
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
          <FocusedEntity ref={focused} />
        ) : (
          <p
            className="c-faded"
            style={{ fontStyle: "italic", textAlign: "center", marginTop: 96 }}
          >
            click a council, decision, or proposal in the codex to read it
            here.
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
  onFocus,
}: {
  proc: Proclamation;
  councils: Council[];
  decisions: Decision[];
  proposals: Proposal[];
  onFocus: (ref: EntityRef) => void;
}) {
  return (
    <article style={{ position: "relative", marginBottom: 48 }}>
      <header style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
        <span className="c-numeral c-gold">№ {toRoman(proc.seq)}</span>
        <time
          className="c-mono c-faded"
          style={{ fontSize: 12 }}
          dateTime={proc.issued_at}
        >
          {formatDate(proc.issued_at)}
        </time>
      </header>
      <p
        className="c-dropcap c-fade-in"
        style={{
          fontFamily: "var(--f-body)",
          fontSize: "var(--t-proclamation)",
          textAlign: "justify",
          lineHeight: 1.55,
          marginTop: 8,
        }}
      >
        <Linkified text={proc.text} />
      </p>
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
                onClick={() =>
                  onFocus({ kind: "proposal", id: p.proposal_id })
                }
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
    </article>
  );
}

function FocusedEntity({ ref }: { ref: EntityRef }) {
  if (ref.kind === "proposal") return <FocusedProposal id={ref.id} />;
  if (ref.kind === "decision") return <FocusedDecision id={ref.id} />;
  if (ref.kind === "council") return <FocusedCouncil id={ref.id} />;
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

function toRoman(n: number): string {
  const table: Array<[number, string]> = [
    [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"],
    [100, "C"], [90, "XC"], [50, "L"], [40, "XL"],
    [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
  ];
  let out = "";
  for (const [v, sym] of table) {
    while (n >= v) {
      out += sym;
      n -= v;
    }
  }
  return out;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
