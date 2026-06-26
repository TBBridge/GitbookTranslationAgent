CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS schema_migrations (
  filename TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_sessions (
  session_hash TEXT PRIMARY KEY,
  csrf_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_login_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ip_hash TEXT NOT NULL,
  succeeded BOOLEAN NOT NULL DEFAULT false,
  attempted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  token_fingerprint TEXT NOT NULL,
  version TEXT NOT NULL,
  capabilities JSONB NOT NULL CHECK (jsonb_typeof(capabilities) = 'object'),
  last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
  state TEXT NOT NULL CHECK (
    state IN (
      'queued',
      'leased',
      'running',
      'succeeded',
      'failed',
      'cancelled',
      'stale'
    )
  ),
  config JSONB NOT NULL CHECK (jsonb_typeof(config) = 'object'),
  cancel_requested BOOLEAN NOT NULL DEFAULT false,
  assigned_worker_id UUID REFERENCES workers(id) ON DELETE SET NULL,
  created_by TEXT NOT NULL DEFAULT 'admin',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS job_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE RESTRICT,
  lease_hash TEXT NOT NULL,
  state TEXT NOT NULL CHECK (
    state IN ('leased', 'running', 'succeeded', 'failed', 'cancelled', 'stale')
  ),
  lease_expires_at TIMESTAMPTZ NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ,
  result JSONB CHECK (result IS NULL OR jsonb_typeof(result) = 'object')
);

CREATE TABLE IF NOT EXISTS job_logs (
  id BIGSERIAL PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  attempt_id UUID REFERENCES job_attempts(id) ON DELETE SET NULL,
  sequence INTEGER NOT NULL CHECK (sequence > 0),
  event JSONB NOT NULL CHECK (jsonb_typeof(event) = 'object'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (attempt_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_ip_time
  ON admin_login_attempts (ip_hash, attempted_at DESC);

CREATE INDEX IF NOT EXISTS idx_workers_last_heartbeat
  ON workers (last_heartbeat_at DESC);

CREATE INDEX IF NOT EXISTS idx_jobs_queued
  ON jobs (created_at, id)
  WHERE state = 'queued' AND cancel_requested = false;

CREATE INDEX IF NOT EXISTS idx_jobs_state_updated
  ON jobs (state, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_job_attempts_active_lease
  ON job_attempts (job_id, worker_id, lease_expires_at)
  WHERE state IN ('leased', 'running');

CREATE INDEX IF NOT EXISTS idx_job_logs_job_id
  ON job_logs (job_id, id);
