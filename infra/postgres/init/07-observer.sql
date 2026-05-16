-- Observation context: read-models projected from events + OTel.

SET search_path TO observer, public;

CREATE TABLE IF NOT EXISTS pod_state (
    pod_id           TEXT PRIMARY KEY,
    display_role     TEXT NOT NULL,
    image_strategy   TEXT NOT NULL,
    runtime_status   TEXT NOT NULL DEFAULT 'not_yet_spawned',  -- running|stopped|not_yet_spawned
    agent_state      TEXT NOT NULL DEFAULT 'idle',              -- idle|thinking|blocked|stuck
    main_image       TEXT,
    admitted         BOOLEAN NOT NULL DEFAULT FALSE,
    public_url       TEXT,
    last_seen        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- HTTP endpoints observed on a pod.
CREATE TABLE IF NOT EXISTS endpoints (
    pod_id      TEXT NOT NULL,
    method      TEXT NOT NULL,
    path        TEXT NOT NULL,
    annotation  TEXT,
    first_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pod_id, method, path)
);

-- Observed calls (sparse projection of OTel spans; Tempo is the source of truth).
CREATE TABLE IF NOT EXISTS calls (
    id          BIGSERIAL PRIMARY KEY,
    src_pod     TEXT NOT NULL,
    dst_pod     TEXT NOT NULL,
    method      TEXT NOT NULL,
    path        TEXT NOT NULL,
    status      INT,
    latency_ms  INT,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS calls_recent_idx ON calls(observed_at DESC);
CREATE INDEX IF NOT EXISTS calls_pair_idx ON calls(src_pod, dst_pod);

-- Activity feed (named events for the witness perspective digest).
CREATE TABLE IF NOT EXISTS activity (
    id          BIGSERIAL PRIMARY KEY,
    event_id    TEXT NOT NULL UNIQUE,
    event_type  TEXT NOT NULL,
    payload     JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    digested    BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS activity_recent_idx ON activity(occurred_at DESC);

-- Hourly digest rows (J3).
CREATE TABLE IF NOT EXISTS digests (
    hour_bucket  TIMESTAMPTZ PRIMARY KEY,
    summary      TEXT NOT NULL,
    item_count   INT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Agent traces (LLM turn metadata projected from OpenLLMetry spans).
CREATE TABLE IF NOT EXISTS agent_turns (
    pod_id       TEXT NOT NULL,
    turn_id      TEXT NOT NULL,
    started_at   TIMESTAMPTZ NOT NULL,
    ended_at     TIMESTAMPTZ,
    tokens_in    INT,
    tokens_out   INT,
    PRIMARY KEY (pod_id, turn_id)
);
