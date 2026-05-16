-- Decisions context: sealed records (placeholder | sealed).

SET search_path TO decisions, public;

CREATE TABLE IF NOT EXISTS decisions (
    decision_id     TEXT PRIMARY KEY,           -- 'adr-NNNN' or uuid
    title           TEXT NOT NULL,
    body            TEXT,                       -- nullable while placeholder
    affected        TEXT[] NOT NULL DEFAULT '{}',
    origin_kind     TEXT NOT NULL,              -- proposal|council|proclamation
    origin_id       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'placeholder',  -- placeholder|sealed
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    sealed_at       TIMESTAMPTZ,
    CONSTRAINT body_required_when_sealed
        CHECK (status = 'placeholder' OR (body IS NOT NULL AND length(trim(body)) > 0))
);

CREATE INDEX IF NOT EXISTS decisions_status_idx ON decisions(status);
CREATE INDEX IF NOT EXISTS decisions_origin_idx ON decisions(origin_kind, origin_id);
