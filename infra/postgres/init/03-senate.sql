-- Senate context: proposals, ballots.

SET search_path TO senate, public;

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id      TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,
    proposer         TEXT NOT NULL,
    strategy         TEXT NOT NULL,
    summary          TEXT NOT NULL,
    payload          JSONB NOT NULL DEFAULT '{}'::jsonb,
    eligible_voters  TEXT[] NOT NULL,
    deadline         TIMESTAMPTZ NOT NULL,
    opened_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at        TIMESTAMPTZ,
    outcome          TEXT NOT NULL DEFAULT 'open'  -- open|approved|rejected|expired
);

CREATE INDEX IF NOT EXISTS proposals_outcome_idx ON proposals(outcome);
CREATE INDEX IF NOT EXISTS proposals_deadline_idx ON proposals(deadline) WHERE outcome = 'open';

CREATE TABLE IF NOT EXISTS ballots (
    proposal_id   TEXT NOT NULL REFERENCES proposals(proposal_id),
    voter         TEXT NOT NULL,
    choice        TEXT NOT NULL,             -- yes|no|abstain
    comment       TEXT,
    cast_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (proposal_id, voter)
);
