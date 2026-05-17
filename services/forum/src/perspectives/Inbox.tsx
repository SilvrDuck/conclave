/** Spec/09 §4.5 — /inbox. Two stacked sections: pending imperial
 * ballots + stuck things. Never tabs; a single full-width page. */

import useSWR from "swr";
import { fetcher, postCommand, type Pod, type Proposal } from "../api";
import { ProposalCartouche } from "../components/ProposalCartouche";
import { StuckTray } from "../components/StuckTray";
import { WaxSeal } from "../components/WaxSeal";
import { C } from "../theme";

export function Inbox() {
  const { data: pods } = useSWR<Pod[]>("/state/pods", fetcher, {
    refreshInterval: 5000,
  });
  const { data: proposals } = useSWR<Proposal[]>("/state/proposals", fetcher, {
    refreshInterval: 5000,
  });

  const ballots = (proposals ?? []).filter(
    (p) => p.outcome === "open" && p.eligible_voters.includes("__augustus__"),
  );

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "24px 48px",
        maxWidth: 960,
        margin: "0 auto",
      }}
    >
      <section style={{ marginBottom: 32 }}>
        <h2
          className="c-display"
          style={{ margin: "0 0 12px", fontSize: 13 }}
        >
          Pending ballots
        </h2>
        {ballots.length === 0 ? (
          <p className="c-faded" style={{ fontStyle: "italic" }}>
            no imperial business awaits.
          </p>
        ) : (
          ballots.map((p) => <BallotRow key={p.proposal_id} proposal={p} />)
        )}
      </section>

      <section>
        <h2
          className="c-display"
          style={{ margin: "0 0 12px", fontSize: 13 }}
        >
          Stuck things
        </h2>
        <StuckTray pods={pods ?? []} fullPage />
      </section>
    </div>
  );
}

function BallotRow({ proposal }: { proposal: Proposal }) {
  return (
    <div style={{ position: "relative" }}>
      <ProposalCartouche proposal={proposal} />
      <div
        style={{
          display: "flex",
          gap: 12,
          justifyContent: "flex-end",
          marginTop: -4,
          marginBottom: 12,
        }}
      >
        <Vote proposalId={proposal.proposal_id} choice="yes" letter="A" />
        <Vote proposalId={proposal.proposal_id} choice="no" letter="N" />
        <Vote proposalId={proposal.proposal_id} choice="abstain" letter="—" />
      </div>
    </div>
  );
}

function Vote({
  proposalId,
  choice,
  letter,
}: {
  proposalId: string;
  choice: "yes" | "no" | "abstain";
  letter: string;
}) {
  return (
    <WaxSeal
      letter={letter}
      label={`Cast ${choice}`}
      variant={choice === "abstain" ? "wash" : choice === "no" ? "gold" : "cinnabar"}
      onClick={async () => {
        await postCommand({
          kind: "CastBallot",
          proposal_id: proposalId,
          voter: "__augustus__",
          choice,
        });
      }}
    />
  );
}

// keep the palette referenced — otherwise tsc complains about an unused import.
void C;
