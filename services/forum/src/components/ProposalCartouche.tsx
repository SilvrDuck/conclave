/** Spec/09 §6.3 — Proposal Cartouche.
 *
 * Senate proposal card — distinct vocabulary from the Pod Cartouche
 * (pod-graph node). Rectangular plate: kind ribbon, summary, payload
 * preview (image-swap shows old → new, contract-change lists
 * endpoints), ballot strip, deadline. */

import type { Proposal } from "../api";
import { EntityLink } from "./EntityLink";
import { BallotStrip } from "./BallotStrip";
import { Linkified } from "./Linkified";
import { C } from "../theme";

const KIND_LABEL: Record<string, string> = {
  admit: "ADMISSION",
  admission: "ADMISSION",
  exile: "EXILE",
  image_swap: "IMAGE·SWAP",
  contract_change: "CONTRACT·CHANGE",
  completion: "COMPLETION",
  charter_overhaul: "CHARTER·OVERHAUL",
};

export function ProposalCartouche({ proposal }: { proposal: Proposal }) {
  const kindLabel =
    KIND_LABEL[proposal.kind] ?? proposal.kind.replace(/_/g, "·").toUpperCase();

  return (
    <article
      style={{
        background: C.vellum,
        border: `0.5px solid ${C.inkFaded}`,
        padding: "12px 16px",
        margin: "12px 0",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: `0.5px solid ${C.inkFaded}`,
          paddingBottom: 6,
          marginBottom: 8,
        }}
      >
        <span className="c-rubric">{kindLabel}</span>
        <span className="c-mono c-faded">
          {proposal.proposal_id} · proposed by{" "}
          <EntityLink kind="pod" id={proposal.proposer}>
            {proposal.proposer}
          </EntityLink>
        </span>
      </header>
      <div style={{ fontFamily: "var(--f-body)" }}>
        {proposal.summary ? (
          <Linkified text={proposal.summary} />
        ) : (
          <span className="c-faded" style={{ fontStyle: "italic" }}>
            (no summary)
          </span>
        )}
      </div>
      <PayloadPreview kind={proposal.kind} payload={proposal.payload} />
      <BallotStrip
        strategy={proposal.strategy}
        eligibleVoters={proposal.eligible_voters}
        ballots={proposal.ballots}
        deadline={proposal.deadline}
      />
      <div className="c-faded" style={{ fontSize: 12, marginTop: 4 }}>
        outcome: <span className="c-display-sm">{proposal.outcome}</span>
      </div>
    </article>
  );
}

function PayloadPreview({ kind, payload }: { kind: string; payload: unknown }) {
  if (!payload || typeof payload !== "object") return null;
  const p = payload as Record<string, unknown>;
  if (kind === "image_swap") {
    return (
      <div
        className="c-mono"
        style={{
          background: C.parchment,
          padding: "4px 8px",
          margin: "6px 0",
          color: C.ink,
        }}
      >
        {String(p.old_image ?? "?")} → {String(p.new_image ?? "?")}
      </div>
    );
  }
  if (kind === "contract_change") {
    const eps = (p.endpoints as Array<Record<string, unknown>> | undefined) ?? [];
    if (eps.length === 0) return null;
    return (
      <div className="c-mono" style={{ margin: "6px 0", color: C.inkFaded }}>
        affected endpoints:{" "}
        {eps
          .map((e) => `${e.method ?? "GET"} ${e.path ?? "?"}`)
          .join(", ")}
      </div>
    );
  }
  if (kind === "admission" || kind === "admit") {
    const pod = p.pod_id;
    if (!pod) return null;
    return (
      <div style={{ margin: "6px 0", color: C.inkFaded, fontSize: 13 }}>
        admit:{" "}
        <EntityLink kind="pod" id={String(pod)}>
          {String(pod)}
        </EntityLink>
      </div>
    );
  }
  return null;
}
