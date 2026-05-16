-- Pod Lifecycle context: pods + spawn attempts.

SET search_path TO pods, public;

CREATE TABLE IF NOT EXISTS pods (
    pod_id            TEXT PRIMARY KEY,            -- stable
    display_role      TEXT NOT NULL,               -- mutable
    image_strategy    TEXT NOT NULL,               -- code | adopted
    main_image        TEXT,                        -- adopted only
    charter_path      TEXT,                        -- repo-relative path to charter.md
    admitted          BOOLEAN NOT NULL DEFAULT FALSE,
    admitted_at       TIMESTAMPTZ,
    exiled            BOOLEAN NOT NULL DEFAULT FALSE,
    exiled_at         TIMESTAMPTZ,
    spawned_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS pods_admitted_idx ON pods(admitted);
CREATE INDEX IF NOT EXISTS pods_role_idx ON pods(display_role);

CREATE TABLE IF NOT EXISTS spawns (
    spawn_id    TEXT PRIMARY KEY,
    pod_id      TEXT NOT NULL,
    image       TEXT NOT NULL,
    mode        TEXT NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    succeeded   BOOLEAN,
    error       TEXT
);
