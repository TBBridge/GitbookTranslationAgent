import { randomUUID } from "node:crypto";

import { getSql, type SqlClient } from "@/lib/db/client";
import type { JobLogRow, JobRow } from "@/lib/db/types";
import { jobV1Schema, type JobV1 } from "@/lib/schemas/job-v1";
import { getLeaseStore, MemoryLeaseStore } from "@/lib/services/leases";

export type AdminJobState =
  | "queued"
  | "leased"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "stale";

export interface AdminJob {
  id: string;
  parentJobId: string | null;
  state: AdminJobState;
  config: JobV1;
  cancelRequested: boolean;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
}

export interface AdminJobLog {
  id: number;
  jobId: string;
  attemptId: string | null;
  sequence: number;
  event: unknown;
  createdAt: string;
}

export interface AdminJobStore {
  create(config: JobV1, parentJobId?: string | null): Promise<AdminJob>;
  get(jobId: string): Promise<AdminJob | null>;
  list(limit?: number): Promise<AdminJob[]>;
  cancel(jobId: string): Promise<AdminJob | null>;
  retry(jobId: string): Promise<AdminJob | null>;
  logs(jobId: string, afterId?: number, limit?: number): Promise<AdminJobLog[]>;
}

let adminJobStoreForTests: AdminJobStore | null = null;

export class MemoryAdminJobStore implements AdminJobStore {
  private readonly jobs = new Map<string, AdminJob>();
  private nextLogId = 1;
  private readonly jobLogs = new Map<string, AdminJobLog[]>();

  async create(config: JobV1, parentJobId: string | null = null) {
    const now = new Date().toISOString();
    const job: AdminJob = {
      id: randomUUID(),
      parentJobId,
      state: "queued",
      config: jobV1Schema.parse(config),
      cancelRequested: false,
      createdAt: now,
      updatedAt: now,
      completedAt: null
    };
    this.jobs.set(job.id, job);
    return job;
  }

  async get(jobId: string) {
    return this.jobs.get(jobId) ?? null;
  }

  async list(limit = 50) {
    return [...this.jobs.values()]
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .slice(0, Math.min(Math.max(limit, 1), 100));
  }

  async cancel(jobId: string) {
    const job = this.jobs.get(jobId);
    if (!job) {
      return null;
    }
    const updated = {
      ...job,
      cancelRequested: true,
      state: job.state === "queued" ? ("cancelled" as const) : job.state,
      updatedAt: new Date().toISOString(),
      completedAt: job.state === "queued" ? new Date().toISOString() : job.completedAt
    };
    this.jobs.set(jobId, updated);
    return updated;
  }

  async retry(jobId: string) {
    const job = this.jobs.get(jobId);
    if (!job) {
      return null;
    }
    return this.create(job.config, job.id);
  }

  async logs(jobId: string, afterId = 0, limit = 100) {
    return (this.jobLogs.get(jobId) ?? [])
      .filter((log) => log.id > afterId)
      .slice(0, Math.min(Math.max(limit, 1), 200));
  }

  appendLog(jobId: string, sequence: number, event: unknown) {
    const log: AdminJobLog = {
      id: this.nextLogId,
      jobId,
      attemptId: null,
      sequence,
      event,
      createdAt: new Date().toISOString()
    };
    this.nextLogId += 1;
    this.jobLogs.set(jobId, [...(this.jobLogs.get(jobId) ?? []), log]);
    return log;
  }

  markCompleted(jobId: string, state: AdminJobState) {
    const job = this.jobs.get(jobId);
    if (!job) {
      return null;
    }
    const updated: AdminJob = {
      ...job,
      state,
      updatedAt: new Date().toISOString(),
      completedAt: new Date().toISOString()
    };
    this.jobs.set(jobId, updated);
    return updated;
  }
}

export class DatabaseAdminJobStore implements AdminJobStore {
  constructor(private readonly sql: SqlClient = getSql()) {}

  async create(config: JobV1, parentJobId: string | null = null) {
    const rows = await this.sql`
      INSERT INTO jobs (parent_job_id, state, config)
      VALUES (${parentJobId}, 'queued', ${JSON.stringify(jobV1Schema.parse(config))}::jsonb)
      RETURNING *
    `;
    return jobFromRow(rows[0] as JobRow);
  }

  async get(jobId: string) {
    const rows = await this.sql`
      SELECT *
      FROM jobs
      WHERE id = ${jobId}
      LIMIT 1
    `;
    return rows[0] ? jobFromRow(rows[0] as JobRow) : null;
  }

  async list(limit = 50) {
    const safeLimit = Math.min(Math.max(limit, 1), 100);
    const rows = await this.sql`
      SELECT *
      FROM jobs
      ORDER BY created_at DESC, id DESC
      LIMIT ${safeLimit}
    `;
    return rows.map((row) => jobFromRow(row as JobRow));
  }

  async cancel(jobId: string) {
    const rows = await this.sql`
      UPDATE jobs
      SET cancel_requested = true,
          state = CASE WHEN state = 'queued' THEN 'cancelled' ELSE state END,
          completed_at = CASE WHEN state = 'queued' THEN now() ELSE completed_at END,
          updated_at = now()
      WHERE id = ${jobId}
      RETURNING *
    `;
    return rows[0] ? jobFromRow(rows[0] as JobRow) : null;
  }

  async retry(jobId: string) {
    const rows = await this.sql`
      INSERT INTO jobs (parent_job_id, state, config)
      SELECT id, 'queued', config
      FROM jobs
      WHERE id = ${jobId}
      RETURNING *
    `;
    return rows[0] ? jobFromRow(rows[0] as JobRow) : null;
  }

  async logs(jobId: string, afterId = 0, limit = 100) {
    const safeLimit = Math.min(Math.max(limit, 1), 200);
    const rows = await this.sql`
      SELECT *
      FROM job_logs
      WHERE job_id = ${jobId}
        AND id > ${afterId}
      ORDER BY id
      LIMIT ${safeLimit}
    `;
    return rows.map((row) => logFromRow(row as JobLogRow));
  }
}

export function setAdminJobStoreForTests(store: AdminJobStore | null) {
  adminJobStoreForTests = store;
}

export function getAdminJobStore() {
  if (process.env.E2E_IN_MEMORY === "1") {
    return e2eMemoryAdminJobStore();
  }
  return adminJobStoreForTests ?? new DatabaseAdminJobStore();
}

export async function createAdminJob(config: unknown) {
  const job = await getAdminJobStore().create(jobV1Schema.parse(config));
  enqueueForE2EWorker(job);
  return job;
}

export async function getJobById(jobId: string) {
  return getAdminJobStore().get(jobId);
}

export async function retryAdminJob(jobId: string) {
  const job = await getAdminJobStore().retry(jobId);
  if (job) {
    enqueueForE2EWorker(job);
  }
  return job;
}

export async function syncE2EJobCompletion(jobId: string, state: AdminJobState) {
  if (process.env.E2E_IN_MEMORY !== "1") {
    return;
  }
  const store = getAdminJobStore();
  if (store instanceof MemoryAdminJobStore) {
    store.markCompleted(jobId, state);
  }
}

function enqueueForE2EWorker(job: AdminJob) {
  if (process.env.E2E_IN_MEMORY !== "1") {
    return;
  }
  const leaseStore = getLeaseStore();
  if (leaseStore instanceof MemoryLeaseStore) {
    leaseStore.enqueue(job.config, job.id);
  }
}

function jobFromRow(row: JobRow): AdminJob {
  return {
    id: row.id,
    parentJobId: row.parent_job_id,
    state: row.state,
    config: jobV1Schema.parse(row.config),
    cancelRequested: row.cancel_requested,
    createdAt: new Date(row.created_at).toISOString(),
    updatedAt: new Date(row.updated_at).toISOString(),
    completedAt: row.completed_at ? new Date(row.completed_at).toISOString() : null
  };
}

function logFromRow(row: JobLogRow): AdminJobLog {
  return {
    id: row.id,
    jobId: row.job_id,
    attemptId: row.attempt_id,
    sequence: row.sequence,
    event: row.event,
    createdAt: new Date(row.created_at).toISOString()
  };
}

function e2eMemoryAdminJobStore() {
  const stores = globalThis as typeof globalThis & {
    __gitbookAdminJobs?: MemoryAdminJobStore;
  };
  stores.__gitbookAdminJobs ??= new MemoryAdminJobStore();
  return stores.__gitbookAdminJobs;
}
