-- Operator context: proclamations + DMs from the user.

SET search_path TO operator, public;

CREATE TABLE IF NOT EXISTS proclamations (
    seq             BIGSERIAL PRIMARY KEY,
    text            TEXT NOT NULL,
    issued_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    status          TEXT NOT NULL DEFAULT 'open',  -- 'open' | 'completed'
    summary         TEXT,
    completed_at    TIMESTAMPTZ,
    -- Derived placeholder decision (see spec/05-ddd-contexts.md C1 — the
    -- placeholder lives in `decisions.decisions` and is created the moment a
    -- proclamation lands). No FK across schemas; the join key is here only
    -- as a denormalised pointer.
    placeholder_decision_id  TEXT
);

-- DMs are tracked as council messages (in the council schema); operator does
-- not duplicate them. The operator owns only the proclamation table.
