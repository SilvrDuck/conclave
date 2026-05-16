-- Council context: meetings, messages, DMs (private 2-party councils).

SET search_path TO council, public;

CREATE TABLE IF NOT EXISTS councils (
    council_id        TEXT PRIMARY KEY,
    topic             TEXT NOT NULL,
    participants      TEXT[] NOT NULL,
    private           BOOLEAN NOT NULL DEFAULT FALSE,
    needs_augustus    BOOLEAN NOT NULL DEFAULT FALSE,
    status            TEXT NOT NULL DEFAULT 'open',   -- open|closed
    opened_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at         TIMESTAMPTZ,
    summary           TEXT,
    decision_id       TEXT
);

CREATE INDEX IF NOT EXISTS councils_status_idx ON councils(status);
CREATE INDEX IF NOT EXISTS councils_needs_augustus_idx ON councils(needs_augustus) WHERE status = 'open';

CREATE TABLE IF NOT EXISTS messages (
    council_id   TEXT NOT NULL REFERENCES councils(council_id),
    seq          BIGINT NOT NULL,
    from_pod     TEXT NOT NULL,
    body         TEXT NOT NULL,
    sent_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (council_id, seq)
);
