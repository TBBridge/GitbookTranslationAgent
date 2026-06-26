import { randomBytes, randomUUID } from "node:crypto";

import { hashSecret } from "@/lib/auth/session";
import { getSql, type SqlClient } from "@/lib/db/client";
import { jobV1Schema, type JobV1 } from "@/lib/schemas/job-v1";
import type { WorkerCapabilitiesV1 } from "@/lib/schemas/worker-v1";
import { isWorkerCompatible } from "@/lib/services/capabilities";
import { sanitizeProgressEvent } from "@/lib/services/progress";

export const LEASE_SECONDS = 60;

export interface ClaimedLease {
  jobId: string;
  leaseId: string;
  leaseExpiresAt: string;
  config: JobV1;
}

export interface WorkerClaimInput {
  workerId: string;
  capabilities: WorkerCapabilitiesV1;
}

export interface AppendUpdatesInput {
  jobId: string;
  leaseId: string;
  firstSequence: number;
  updates: unknown[];
}

export interface CompleteJobInput {
  jobId: string;
  leaseId: string;
  result: { status: string; [key: string]: unknown };
  lastSequence?: number | null;
}

export interface LeaseStore {
  claim(input: WorkerClaimInput): Promise<ClaimedLease | null>;
  renew(jobId: string, leaseId: string): Promise<{ accepted: boolean; leaseExpiresAt?: string }>;
  appendUpdates(input: AppendUpdatesInput): Promise<{ acknowledgedSequence: number }>;
  cancellationState(jobId: string, leaseId: string): Promise<{ cancelled: boolean }>;
  complete(input: CompleteJobInput): Promise<{ accepted: true; acknowledgedSequence?: number }>;
}

export class LeaseConflictError extends Error {}

let leaseStoreForTests: LeaseStore | null = null;

interface MemoryJob {
  id: string;
  state: string;
  config: JobV1;
  cancelRequested: boolean;
  assignedWorkerId: string | null;
  completedAt: Date | null;
}

interface MemoryAttempt {
  id: string;
  jobId: string;
  workerId: string;
  leaseHash: string;
  state: string;
  leaseExpiresAt: Date;
  result: unknown | null;
}

export class MemoryLeaseStore implements LeaseStore {
  private readonly jobs = new Map<string, MemoryJob>();
  private readonly attempts = new Map<string, MemoryAttempt>();

  enqueue(config: JobV1, id = randomUUID()) {
    this.jobs.set(id, {
      id,
      state: "queued",
      config: jobV1Schema.parse(config),
      cancelRequested: false,
      assignedWorkerId: null,
      completedAt: null
    });
    return id;
  }

  async claim(input: WorkerClaimInput) {
    const job = [...this.jobs.values()].find(
      (candidate) =>
        candidate.state === "queued" &&
        !candidate.cancelRequested &&
        isWorkerCompatible(candidate.config, {
          id: input.workerId,
          name: input.capabilities.workerName,
          online: true,
          capabilities: input.capabilities
        })
    );
    if (!job) {
      return null;
    }

    const leaseId = randomToken();
    const leaseExpiresAt = new Date(Date.now() + LEASE_SECONDS * 1000);
    const attemptId = randomUUID();
    job.state = "leased";
    job.assignedWorkerId = input.workerId;
    this.attempts.set(attemptId, {
      id: attemptId,
      jobId: job.id,
      workerId: input.workerId,
      leaseHash: hashSecret(leaseId),
      state: "leased",
      leaseExpiresAt,
      result: null
    });

    return {
      jobId: job.id,
      leaseId,
      leaseExpiresAt: leaseExpiresAt.toISOString(),
      config: job.config
    };
  }

  async renew(jobId: string, leaseId: string) {
    const attempt = this.activeAttempt(jobId, leaseId);
    if (!attempt) {
      return { accepted: false };
    }
    attempt.leaseExpiresAt = new Date(Date.now() + LEASE_SECONDS * 1000);
    attempt.state = "running";
    return { accepted: true, leaseExpiresAt: attempt.leaseExpiresAt.toISOString() };
  }

  async appendUpdates(input: AppendUpdatesInput) {
    const attempt = this.activeAttempt(input.jobId, input.leaseId);
    if (!attempt) {
      throw new LeaseConflictError("stale lease");
    }
    input.updates.map((event) => sanitizeProgressEvent(event));
    return {
      acknowledgedSequence: input.firstSequence + input.updates.length - 1
    };
  }

  async cancellationState(jobId: string, leaseId: string) {
    const attempt = this.activeAttempt(jobId, leaseId);
    if (!attempt) {
      return { cancelled: true };
    }
    return { cancelled: this.jobs.get(jobId)?.cancelRequested ?? true };
  }

  async complete(input: CompleteJobInput) {
    const attempt = this.activeAttempt(input.jobId, input.leaseId);
    if (!attempt) {
      throw new LeaseConflictError("stale lease");
    }
    const job = this.jobs.get(input.jobId);
    if (!job) {
      throw new LeaseConflictError("unknown job");
    }
    const finalState = finalStateFromResult(input.result.status);
    attempt.state = finalState;
    attempt.result = input.result;
    job.state = finalState;
    job.completedAt = new Date();
    return {
      accepted: true as const,
      acknowledgedSequence: input.lastSequence ?? undefined
    };
  }

  private activeAttempt(jobId: string, leaseId: string) {
    const leaseHash = hashSecret(leaseId);
    return [...this.attempts.values()].find(
      (attempt) =>
        attempt.jobId === jobId &&
        attempt.leaseHash === leaseHash &&
        ["leased", "running"].includes(attempt.state) &&
        attempt.leaseExpiresAt > new Date()
    );
  }
}

export class DatabaseLeaseStore implements LeaseStore {
  constructor(private readonly sql: SqlClient = getSql()) {}

  async claim(input: WorkerClaimInput) {
    const leaseId = randomToken();
    const leaseHash = hashSecret(leaseId);
    const leaseExpiresAt = new Date(Date.now() + LEASE_SECONDS * 1000);
    const capabilitiesJson = JSON.stringify(input.capabilities);
    const translateProviders = JSON.stringify(
      input.capabilities.providers
        .filter((provider) => provider.roles.includes("translate"))
        .map((provider) => provider.name)
    );
    const reviewProviders = JSON.stringify(
      input.capabilities.providers
        .filter((provider) => provider.roles.includes("review"))
        .map((provider) => provider.name)
    );

    const rows = await this.sql`
      WITH candidate AS (
        SELECT id
        FROM jobs
        WHERE state = 'queued'
          AND cancel_requested = false
          AND (${capabilitiesJson}::jsonb -> 'dictionarySets') ? (config ->> 'dictionarySet')
          AND (${capabilitiesJson}::jsonb -> 'outputRoots') ? (config ->> 'outputRoot')
          AND ${translateProviders}::jsonb ? (config ->> 'translationProvider')
          AND (
            (config ->> 'reviewProvider') IS NULL
            OR ${reviewProviders}::jsonb ? (config ->> 'reviewProvider')
          )
          AND NOT EXISTS (
            SELECT 1
            FROM jsonb_array_elements_text(config -> 'languages') AS lang(value)
            WHERE NOT (
              (${capabilitiesJson}::jsonb #> ARRAY[
                'dictionarySets',
                config ->> 'dictionarySet',
                'languages'
              ]) ? lang.value
            )
          )
        ORDER BY created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
      ),
      leased AS (
        UPDATE jobs
        SET state = 'leased',
            assigned_worker_id = ${input.workerId},
            updated_at = now()
        WHERE id = (SELECT id FROM candidate)
        RETURNING id, config
      ),
      attempt AS (
        INSERT INTO job_attempts (
          job_id,
          worker_id,
          lease_hash,
          state,
          lease_expires_at
        )
        SELECT id, ${input.workerId}, ${leaseHash}, 'leased', ${leaseExpiresAt.toISOString()}
        FROM leased
        RETURNING lease_expires_at
      )
      SELECT leased.id AS job_id, leased.config, attempt.lease_expires_at
      FROM leased, attempt
    `;
    const row = rows[0];
    if (!row) {
      return null;
    }
    return {
      jobId: String(row.job_id),
      leaseId,
      leaseExpiresAt: new Date(String(row.lease_expires_at)).toISOString(),
      config: jobV1Schema.parse(row.config)
    };
  }

  async renew(jobId: string, leaseId: string) {
    const leaseExpiresAt = new Date(Date.now() + LEASE_SECONDS * 1000);
    const rows = await this.sql`
      UPDATE job_attempts
      SET state = 'running',
          lease_expires_at = ${leaseExpiresAt.toISOString()}
      WHERE job_id = ${jobId}
        AND lease_hash = ${hashSecret(leaseId)}
        AND state IN ('leased', 'running')
        AND lease_expires_at > now()
      RETURNING lease_expires_at
    `;
    if (!rows[0]) {
      return { accepted: false };
    }
    return {
      accepted: true,
      leaseExpiresAt: new Date(String(rows[0].lease_expires_at)).toISOString()
    };
  }

  async appendUpdates(input: AppendUpdatesInput) {
    const attempt = await this.findActiveAttempt(input.jobId, input.leaseId);
    for (const [index, event] of input.updates.entries()) {
      await this.sql`
        INSERT INTO job_logs (job_id, attempt_id, sequence, event)
        VALUES (
          ${input.jobId},
          ${attempt.id},
          ${input.firstSequence + index},
          ${JSON.stringify(sanitizeProgressEvent(event))}::jsonb
        )
        ON CONFLICT (attempt_id, sequence) DO NOTHING
      `;
    }
    return {
      acknowledgedSequence: input.firstSequence + input.updates.length - 1
    };
  }

  async cancellationState(jobId: string, leaseId: string) {
    try {
      await this.findActiveAttempt(jobId, leaseId);
    } catch {
      return { cancelled: true };
    }
    const rows = await this.sql`
      SELECT cancel_requested
      FROM jobs
      WHERE id = ${jobId}
    `;
    return { cancelled: Boolean(rows[0]?.cancel_requested ?? true) };
  }

  async complete(input: CompleteJobInput) {
    const attempt = await this.findActiveAttempt(input.jobId, input.leaseId);
    const finalState = finalStateFromResult(input.result.status);
    await this.sql`
      UPDATE job_attempts
      SET state = ${finalState},
          completed_at = now(),
          result = ${JSON.stringify(input.result)}::jsonb
      WHERE id = ${attempt.id}
    `;
    await this.sql`
      UPDATE jobs
      SET state = ${finalState},
          completed_at = now(),
          updated_at = now()
      WHERE id = ${input.jobId}
    `;
    return {
      accepted: true as const,
      acknowledgedSequence: input.lastSequence ?? undefined
    };
  }

  private async findActiveAttempt(jobId: string, leaseId: string) {
    const rows = await this.sql`
      SELECT id
      FROM job_attempts
      WHERE job_id = ${jobId}
        AND lease_hash = ${hashSecret(leaseId)}
        AND state IN ('leased', 'running')
        AND lease_expires_at > now()
      ORDER BY started_at DESC
      LIMIT 1
    `;
    if (!rows[0]) {
      throw new LeaseConflictError("stale lease");
    }
    return { id: String(rows[0].id) };
  }
}

export function setLeaseStoreForTests(store: LeaseStore | null) {
  leaseStoreForTests = store;
}

export function getLeaseStore() {
  return leaseStoreForTests ?? new DatabaseLeaseStore();
}

function finalStateFromResult(status: string) {
  if (status === "succeeded") {
    return "succeeded";
  }
  if (status === "cancelled") {
    return "cancelled";
  }
  return "failed";
}

function randomToken() {
  return randomBytes(32).toString("base64url");
}
