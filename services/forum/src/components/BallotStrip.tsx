/** Spec/09 §6.7 — Ballot Strip. The proposal's voting row.
 *
 * One pip per eligible voter (filled monogram if cast, hollow if
 * pending, em-dash if abstain, wash if sortition-undrawn).
 * Strategy badge in Cinzel small-caps. Deadline countdown in mono. */

import type { Ballot } from "../api";
import { C, monogram, podHue } from "../theme";
import { EntityLink } from "./EntityLink";

interface Props {
  strategy: string;
  eligibleVoters: string[];
  ballots: Ballot[];
  deadline: string;
}

const STRATEGY_LABEL: Record<string, string> = {
  majority: "MAJORITY",
  supermajority: "SUPERMAJORITY",
  consensus_omnium: "CONSENSUS·OMNIUM",
  sortition: "SORTITION",
};

export function BallotStrip({
  strategy,
  eligibleVoters,
  ballots,
  deadline,
}: Props) {
  const byVoter = new Map<string, Ballot>();
  for (const b of ballots) byVoter.set(b.voter, b);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
        margin: "8px 0",
      }}
    >
      <span className="c-rubric">
        {STRATEGY_LABEL[strategy] ?? strategy.toUpperCase()}
      </span>
      <div style={{ display: "flex", gap: 4 }}>
        {eligibleVoters.length === 0 ? (
          <span className="c-faded" style={{ fontStyle: "italic" }}>
            (sortition pending draw)
          </span>
        ) : (
          eligibleVoters.map((voter) => {
            const ballot = byVoter.get(voter);
            return (
              <EntityLink key={voter} kind="pod" id={voter}>
                <Pip voter={voter} ballot={ballot} />
              </EntityLink>
            );
          })
        )}
      </div>
      <span className="c-mono c-faded" style={{ marginLeft: "auto" }}>
        deadline {formatDeadline(deadline)}
      </span>
    </div>
  );
}

function Pip({ voter, ballot }: { voter: string; ballot: Ballot | undefined }) {
  const base = {
    width: 22,
    height: 22,
    borderRadius: "50%",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "var(--f-display)",
    fontWeight: 600,
    fontSize: 10,
    border: `1px solid ${C.inkFaded}`,
  };
  if (!ballot) {
    return (
      <span
        aria-label={`pending: ${voter}`}
        style={{ ...base, background: C.parchment, color: C.inkFaded }}
      >
        ·
      </span>
    );
  }
  if (ballot.choice === "abstain") {
    return (
      <span
        aria-label={`abstain: ${voter}`}
        style={{ ...base, background: C.wash, color: C.ink }}
      >
        —
      </span>
    );
  }
  // yes / no — filled monogram in pod identity colour. Border
  // hints choice: solid for yes, dashed for no.
  return (
    <span
      aria-label={`${ballot.choice}: ${voter}`}
      title={ballot.comment ?? undefined}
      style={{
        ...base,
        background: podHue(voter),
        color: C.parchment,
        border:
          ballot.choice === "no"
            ? `1.5px dashed ${C.cinnabar}`
            : `1px solid ${C.ink}`,
      }}
    >
      {monogram(voter)}
    </span>
  );
}

function formatDeadline(iso: string): string {
  try {
    const d = new Date(iso).getTime() - Date.now();
    if (d < 0) return "passed";
    const s = Math.round(d / 1000);
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.round(s / 60)}m`;
    return `${Math.round(s / 3600)}h`;
  } catch {
    return iso;
  }
}
