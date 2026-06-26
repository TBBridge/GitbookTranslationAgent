export type JobState =
  | "queued"
  | "leased"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "stale";

export type AttemptState = Exclude<JobState, "queued">;

export interface WorkerRow {
  id: string;
  name: string;
  token_fingerprint: string;
  version: string;
  capabilities: unknown;
  last_heartbeat_at: string;
  created_at: string;
  updated_at: string;
}

export interface JobRow {
  id: string;
  parent_job_id: string | null;
  state: JobState;
  config: unknown;
  cancel_requested: boolean;
  assigned_worker_id: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface JobAttemptRow {
  id: string;
  job_id: string;
  worker_id: string;
  lease_hash: string;
  state: AttemptState;
  lease_expires_at: string;
  started_at: string;
  completed_at: string | null;
  result: unknown | null;
}

export interface JobLogRow {
  id: number;
  job_id: string;
  attempt_id: string | null;
  sequence: number;
  event: unknown;
  created_at: string;
}
