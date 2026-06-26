import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { POST as claim } from "@/app/api/worker/v1/claim/route";
import { POST as complete } from "@/app/api/worker/v1/jobs/[jobId]/complete/route";
import { validJobFixture } from "@/lib/schemas/job-v1";
import { workerCapabilitiesFixture } from "@/lib/schemas/worker-v1";
import { MemoryLeaseStore, setLeaseStoreForTests } from "@/lib/services/leases";

describe("worker lease lifecycle", () => {
  let leaseStore: MemoryLeaseStore;

  beforeEach(() => {
    process.env.WORKER_TOKEN = "worker-secret";
    leaseStore = new MemoryLeaseStore();
    leaseStore.enqueue(validJobFixture());
    setLeaseStoreForTests(leaseStore);
  });

  afterEach(() => {
    delete process.env.WORKER_TOKEN;
    setLeaseStoreForTests(null);
  });

  it("allows only one concurrent claim for a queued job", async () => {
    const [a, b] = await Promise.all([claimJob(), claimJob()]);

    expect([a.status, b.status].sort()).toEqual([200, 204]);
  });

  it("rejects completion with a stale lease token", async () => {
    const claimResponse = await claimJob();
    const { job } = await claimResponse.json();

    const response = await complete(
      workerRequest(`/api/worker/v1/jobs/${job.jobId}/complete`, {
        leaseId: "expired",
        result: { status: "succeeded", results: [], issues: [] }
      }),
      { params: Promise.resolve({ jobId: job.jobId }) }
    );

    expect(response.status).toBe(409);
  });
});

function claimJob() {
  return claim(
    workerRequest("/api/worker/v1/claim", {
      workerId: "worker-1",
      capabilities: workerCapabilitiesFixture()
    })
  );
}

function workerRequest(path: string, body: Record<string, unknown>) {
  return new Request(`https://control.test${path}`, {
    method: "POST",
    headers: {
      authorization: "Bearer worker-secret",
      "content-type": "application/json",
      "x-worker-version": "test-version"
    },
    body: JSON.stringify({
      schemaVersion: 1,
      ...body
    })
  });
}
