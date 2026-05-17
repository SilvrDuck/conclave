/** Spec/09 §6.7 — Ballot Strip. The proposal's voting row.
 *
 * One pip per eligible voter (filled monogram if cast, hollow if
 * pending, em-dash if abstain, wash if sortition-undrawn).
 * Strategy badge in Cinzel small-caps. Deadline countdown in mono.
 *
 * Each pip is itself the clickable affordance — opening the voter's
 * pod folio. No nested button-in-button. */

import type { Ballot } from "../api";
import { useFolio } from "../folio";
import { C, monogram, podHue } from "../theme";

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
  const folio = useFolio();
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
              <Pip
                key={voter}
                voter={voter}
                ballot={ballot}
                onClick={() => folio.open({ kind: "pod", id: voter })}
              />
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

function Pip({
  voter,
  ballot,
  onClick,
}: {
  voter: string;
  ballot: Ballot | undefined;
  onClick: () => void;
}) {
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
    cursor: "pointer",
    padding: 0,
  } as const;
  const title = ballot?.comment ?? `${voter} — ${ballot?.choice ?? "pending"}`;
  if (!ballot) {
    return (
      <button
        type="button"
        aria-label={`pending: ${voter}`}
        title={title}
        onClick={onClick}
        style={{ ...base, background: C.parchment, color: C.inkFaded }}
      >
        ·
      </button>
    );
  }
  if (ballot.choice === "abstain") {
    return (
      <button
        type="button"
        aria-label={`abstain: ${voter}`}
        title={title}
        onClick={onClick}
        style={{ ...base, background: C.wash, color: C.ink }}
      >
        —
      </button>
    );
  }
  return (
    <button
      type="button"
      aria-label={`${ballot.choice}: ${voter}`}
      title={title}
      onClick={onClick}
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
    </button>
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
