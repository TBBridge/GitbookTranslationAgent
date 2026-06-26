import { getSql, type SqlClient } from "@/lib/db/client";
import type { JobRow, JobState } from "@/lib/db/types";

export interface CreateJobRecordInput {
  config: Record<string, unknown>;
  createdBy?: string;
  parentJobId?: string | null;
}

export async function createJobRecord(
  input: CreateJobRecordInput,
  sql: SqlClient = getSql()
): Promise<JobRow> {
  const rows = await sql`
    INSERT INTO jobs (parent_job_id, state, config, created_by)
    VALUES (
      ${input.parentJobId ?? null},
      'queued',
      ${JSON.stringify(input.config)}::jsonb,
      ${input.createdBy ?? "admin"}
    )
    RETURNING *
  `;

  return rows[0] as JobRow;
}

export async function listRecentJobs(
  options: { limit?: number; state?: JobState } = {},
  sql: SqlClient = getSql()
): Promise<JobRow[]> {
  const limit = Math.min(Math.max(options.limit ?? 50, 1), 100);
  const rows =
    options.state === undefined
      ? await sql`
          SELECT *
          FROM jobs
          ORDER BY created_at DESC, id DESC
          LIMIT ${limit}
        `
      : await sql`
          SELECT *
          FROM jobs
          WHERE state = ${options.state}
          ORDER BY created_at DESC, id DESC
          LIMIT ${limit}
        `;

  return rows as JobRow[];
}
