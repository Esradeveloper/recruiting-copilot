-- Recruiting Copilot schema.
-- evaluations and decisions are append-only audit tables.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE jobs (
    id          SERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Scoring criteria per job. Embedding column is added on Day 3 (RAG).
CREATE TABLE criteria (
    id          SERIAL PRIMARY KEY,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    weight      NUMERIC(3,2) NOT NULL CHECK (weight > 0 AND weight <= 1),
    UNIQUE (job_id, name)
);

-- One row per incoming application. No personal data here: the CV is
-- referenced only by its content hash.
CREATE TABLE applications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      INTEGER NOT NULL REFERENCES jobs(id),
    cv_sha256   CHAR(64) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE recommendation AS ENUM ('advance', 'review', 'reject_suggested');
CREATE TYPE evaluation_status AS ENUM ('ok', 'invalid_output', 'error');

-- AI recommendation (never a decision). Failed runs are stored too.
CREATE TABLE evaluations (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    status         evaluation_status NOT NULL,
    model          TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    attempts       SMALLINT NOT NULL DEFAULT 1,
    score          SMALLINT CHECK (score BETWEEN 0 AND 100),
    recommendation recommendation,
    result         JSONB,          -- full validated output (strengths, gaps, reasoning, criteria_scores)
    error          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status <> 'ok' OR (score IS NOT NULL AND recommendation IS NOT NULL AND result IS NOT NULL))
);

CREATE TYPE human_decision AS ENUM ('advance', 'reject');

-- The human decision from Slack.
CREATE TABLE decisions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id),
    evaluation_id  UUID REFERENCES evaluations(id),
    decision       human_decision NOT NULL,
    decided_by     TEXT NOT NULL,  -- Slack user ID, not a name
    decided_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON evaluations (application_id, created_at DESC);
CREATE INDEX ON decisions (application_id, decided_at DESC);

-- Enforce append-only audit tables.
CREATE FUNCTION forbid_audit_change() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER evaluations_append_only
    BEFORE UPDATE OR DELETE ON evaluations
    FOR EACH ROW EXECUTE FUNCTION forbid_audit_change();

CREATE TRIGGER decisions_append_only
    BEFORE UPDATE OR DELETE ON decisions
    FOR EACH ROW EXECUTE FUNCTION forbid_audit_change();
