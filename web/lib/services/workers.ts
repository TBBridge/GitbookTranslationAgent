import { randomUUID } from "node:crypto";

import { getSql, type SqlClient } from "@/lib/db/client";
import type { WorkerRow } from "@/lib/db/types";
import {
  workerCapabilitiesV1Schema,
  type WorkerCapabilitiesV1
} from "@/lib/schemas/worker-v1";

export interface WorkerRecord {
  id: string;
  name: string;
  tokenFingerprint: string;
  version: string;
  capabilities: WorkerCapabilitiesV1;
  lastHeartbeatAt: Date;
}

export interface UpsertWorkerInput {
  capabilities: WorkerCapabilitiesV1;
  tokenFingerprint: string;
  version: string;
}

export interface WorkerStore {
  upsert(input: UpsertWorkerInput): Promise<WorkerRecord>;
  heartbeat(input: UpsertWorkerInput & { workerId: string }): Promise<WorkerRecord>;
  findByName(name: string): Promise<WorkerRecord | null>;
  list(): Promise<WorkerRecord[]>;
}

let workerStoreForTests: WorkerStore | null = null;

export class DatabaseWorkerStore implements WorkerStore {
  constructor(private readonly sql: SqlClient = getSql()) {}

  async upsert(input: UpsertWorkerInput) {
    const rows = await this.sql`
      INSERT INTO workers (name, token_fingerprint, version, capabilities)
      VALUES (
        ${input.capabilities.workerName},
        ${input.tokenFingerprint},
        ${input.version},
        ${JSON.stringify(input.capabilities)}::jsonb
      )
      ON CONFLICT (name) DO UPDATE
        SET token_fingerprint = EXCLUDED.token_fingerprint,
            version = EXCLUDED.version,
            capabilities = EXCLUDED.capabilities,
            last_heartbeat_at = now(),
            updated_at = now()
      RETURNING *
    `;
    return workerFromRow(rows[0] as WorkerRow);
  }

  async heartbeat(input: UpsertWorkerInput & { workerId: string }) {
    const rows = await this.sql`
      UPDATE workers
      SET token_fingerprint = ${input.tokenFingerprint},
          version = ${input.version},
          capabilities = ${JSON.stringify(input.capabilities)}::jsonb,
          last_heartbeat_at = now(),
          updated_at = now()
      WHERE id = ${input.workerId}
      RETURNING *
    `;
    if (rows[0]) {
      return workerFromRow(rows[0] as WorkerRow);
    }
    return this.upsert(input);
  }

  async findByName(name: string) {
    const rows = await this.sql`
      SELECT *
      FROM workers
      WHERE name = ${name}
      LIMIT 1
    `;
    return rows[0] ? workerFromRow(rows[0] as WorkerRow) : null;
  }

  async list() {
    const rows = await this.sql`
      SELECT *
      FROM workers
      ORDER BY last_heartbeat_at DESC, name ASC
      LIMIT 100
    `;
    return rows.map((row) => workerFromRow(row as WorkerRow));
  }
}

export class MemoryWorkerStore implements WorkerStore {
  private readonly workers = new Map<string, WorkerRecord>();

  async upsert(input: UpsertWorkerInput) {
    const existing = this.workers.get(input.capabilities.workerName);
    const worker: WorkerRecord = {
      id: existing?.id ?? randomUUID(),
      name: input.capabilities.workerName,
      tokenFingerprint: input.tokenFingerprint,
      version: input.version,
      capabilities: input.capabilities,
      lastHeartbeatAt: new Date()
    };
    this.workers.set(worker.name, worker);
    return worker;
  }

  async heartbeat(input: UpsertWorkerInput & { workerId: string }) {
    const existing = [...this.workers.values()].find(
      (worker) => worker.id === input.workerId
    );
    if (!existing) {
      return this.upsert(input);
    }
    const worker: WorkerRecord = {
      ...existing,
      tokenFingerprint: input.tokenFingerprint,
      version: input.version,
      capabilities: input.capabilities,
      lastHeartbeatAt: new Date()
    };
    this.workers.set(worker.name, worker);
    return worker;
  }

  async findByName(name: string) {
    return this.workers.get(name) ?? null;
  }

  async list() {
    return [...this.workers.values()].sort((a, b) => a.name.localeCompare(b.name));
  }
}

export function setWorkerStoreForTests(store: WorkerStore | null) {
  workerStoreForTests = store;
}

export function getWorkerStore() {
  if (process.env.E2E_IN_MEMORY === "1") {
    return e2eMemoryWorkerStore();
  }
  return workerStoreForTests ?? new DatabaseWorkerStore();
}

export async function registerWorker(
  input: UpsertWorkerInput,
  store: WorkerStore = getWorkerStore()
) {
  return store.upsert({
    ...input,
    capabilities: workerCapabilitiesV1Schema.parse(input.capabilities)
  });
}

export async function heartbeatWorker(
  input: UpsertWorkerInput & { workerId: string },
  store: WorkerStore = getWorkerStore()
) {
  return store.heartbeat({
    ...input,
    capabilities: workerCapabilitiesV1Schema.parse(input.capabilities)
  });
}

export async function getWorkerByName(
  name: string,
  store: WorkerStore = getWorkerStore()
) {
  return store.findByName(name);
}

function workerFromRow(row: WorkerRow): WorkerRecord {
  return {
    id: row.id,
    name: row.name,
    tokenFingerprint: row.token_fingerprint,
    version: row.version,
    capabilities: workerCapabilitiesV1Schema.parse(row.capabilities),
    lastHeartbeatAt: new Date(row.last_heartbeat_at)
  };
}

function e2eMemoryWorkerStore() {
  const stores = globalThis as typeof globalThis & {
    __gitbookWorkers?: MemoryWorkerStore;
  };
  stores.__gitbookWorkers ??= new MemoryWorkerStore();
  return stores.__gitbookWorkers;
}
