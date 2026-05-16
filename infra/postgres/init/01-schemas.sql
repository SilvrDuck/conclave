-- Per-bounded-context schemas. No cross-schema FKs.
-- Each schema is owned by exactly one service process (see spec/07-c4.md).

CREATE SCHEMA IF NOT EXISTS operator;     -- Observer process owns
CREATE SCHEMA IF NOT EXISTS observer;     -- Observer process owns (read-models)
CREATE SCHEMA IF NOT EXISTS senate;       -- mcp-senate owns
CREATE SCHEMA IF NOT EXISTS council;      -- mcp-coms owns
CREATE SCHEMA IF NOT EXISTS decisions;    -- mcp-decisions owns
CREATE SCHEMA IF NOT EXISTS pods;         -- mcp-pods owns

-- Grant our single role read/write across all schemas. Auth/authz is out of
-- scope for v2 alpha; everyone shares one user.
GRANT ALL ON SCHEMA operator, observer, senate, council, decisions, pods TO conclave;
ALTER DEFAULT PRIVILEGES IN SCHEMA operator, observer, senate, council, decisions, pods
    GRANT ALL ON TABLES TO conclave;
ALTER DEFAULT PRIVILEGES IN SCHEMA operator, observer, senate, council, decisions, pods
    GRANT ALL ON SEQUENCES TO conclave;
