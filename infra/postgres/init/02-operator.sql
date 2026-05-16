-- Operator context: proclamations + DMs from the user.

SET search_path TO operator, public;

CREATE TABLE IF NOT EXISTS proclamations (
    seq         BIGSERIAL PRIMARY KEY,
    text        TEXT NOT NULL,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    status      TEXT NOT NULL DEFAULT 'open',  -- 'open' | 'completed'
    summary     TEXT,
    completed_at TIMESTAMPTZ
);

-- DMs are tracked as council messages (in the council schema); operator does
-- not duplicate them. The operator owns only the proclamation table.
