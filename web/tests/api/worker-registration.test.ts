import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { POST as heartbeat } from "@/app/api/worker/v1/heartbeat/route";
import { POST as register } from "@/app/api/worker/v1/register/route";
import { workerCapabilitiesFixture } from "@/lib/schemas/worker-v1";
import {
  getWorkerByName,
  MemoryWorkerStore,
  setWorkerStoreForTests
} from "@/lib/services/workers";

describe("worker registration", () => {
  beforeEach(() => {
    process.env.WORKER_TOKEN = "worker-secret";
    setWorkerStoreForTests(new MemoryWorkerStore());
  });

  afterEach(() => {
    delete process.env.WORKER_TOKEN;
    setWorkerStoreForTests(null);
  });

  it("rejects an invalid worker bearer token", async () => {
    const response = await registerWorker({ authorization: "Bearer wrong" });

    expect(response.status).toBe(401);
  });

  it("stores capabilities without local paths", async () => {
    const response = await registerWorker();
    const body = await response.json();
    const worker = await getWorkerByName("office-mac");

    expect(response.status).toBe(200);
    expect(body.workerId).toEqual(expect.any(String));
    expect(JSON.stringify(worker?.capabilities)).not.toContain("/Users/");
  });

  it("refreshes an existing worker heartbeat", async () => {
    const registerResponse = await registerWorker();
    const { workerId } = await registerResponse.json();

    const response = await heartbeat(
      workerRequest("/api/worker/v1/heartbeat", {
        body: {
          schemaVersion: 1,
          workerId,
          capabilities: workerCapabilitiesFixture()
        }
      })
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ accepted: true });
  });

  it("rejects path-like capability payloads", async () => {
    const response = await registerWorker({
      body: {
        schemaVersion: 1,
        capabilities: {
          ...workerCapabilitiesFixture(),
          workerName: "/Users/charles/worker"
        }
      }
    });

    expect(response.status).toBe(400);
  });
});

function registerWorker(
  options: {
    authorization?: string;
    body?: unknown;
  } = {}
) {
  return register(
    workerRequest("/api/worker/v1/register", {
      authorization: options.authorization,
      body:
        options.body ??
        {
          schemaVersion: 1,
          capabilities: workerCapabilitiesFixture()
        }
    })
  );
}

function workerRequest(
  path: string,
  options: {
    authorization?: string;
    body?: unknown;
  } = {}
) {
  return new Request(`https://control.test${path}`, {
    method: "POST",
    headers: {
      authorization: options.authorization ?? "Bearer worker-secret",
      "content-type": "application/json",
      "x-worker-version": "test-version"
    },
    body: JSON.stringify(options.body)
  });
}
