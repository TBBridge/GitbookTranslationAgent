import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { POST as createJob } from "@/app/api/admin/jobs/route";
import { POST as retryJob } from "@/app/api/admin/jobs/[jobId]/retry/route";
import {
  buildSessionCookie,
  createAdminSession,
  MemorySessionStore,
  setSessionStoreForTests
} from "@/lib/auth/session";
import { validJobFixture } from "@/lib/schemas/job-v1";
import {
  getJobById,
  MemoryAdminJobStore,
  setAdminJobStoreForTests
} from "@/lib/services/jobs";

describe("administrator job APIs", () => {
  let csrfToken: string;
  let cookie: string;
  let jobStore: MemoryAdminJobStore;

  beforeEach(async () => {
    const sessionStore = new MemorySessionStore();
    setSessionStoreForTests(sessionStore);
    const session = await createAdminSession(sessionStore);
    csrfToken = session.csrfToken;
    cookie = buildSessionCookie(session);
    jobStore = new MemoryAdminJobStore();
    setAdminJobStoreForTests(jobStore);
  });

  afterEach(() => {
    setSessionStoreForTests(null);
    setAdminJobStoreForTests(null);
  });

  it("creates an immutable queued job", async () => {
    const response = await createJob(adminRequest("/api/admin/jobs", validJobFixture()));
    const body = await response.json();

    expect(response.status).toBe(201);
    expect(body.state).toBe("queued");
    expect(body.config.repoUrl).toBe("https://github.com/acme/docs");
  });

  it("retry creates a child job", async () => {
    const original = await jobStore.create(validJobFixture());

    const response = await retryJob(adminRequest(`/api/admin/jobs/${original.id}/retry`), {
      params: Promise.resolve({ jobId: original.id })
    });
    const body = await response.json();
    const child = await getJobById(body.id);

    expect(response.status).toBe(201);
    expect(body.parentJobId).toBe(original.id);
    expect(body.id).not.toBe(original.id);
    expect(child?.config).toEqual(original.config);
  });

  function adminRequest(path: string, body: unknown = {}) {
    return new Request(`https://control.test${path}`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        cookie,
        origin: "https://control.test",
        "x-csrf-token": csrfToken
      },
      body: JSON.stringify(body)
    });
  }
});
