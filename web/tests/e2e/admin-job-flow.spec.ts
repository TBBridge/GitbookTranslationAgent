import { expect, test } from "@playwright/test";

const capabilities = {
  schemaVersion: 1,
  workerName: "office-mac",
  dictionarySets: {
    default: {
      languages: ["en"]
    }
  },
  outputRoots: ["default"],
  providers: [
    {
      name: "ollama-local",
      provider: "ollama",
      model: "qwen3",
      roles: ["translate", "review"]
    }
  ]
};

const job = {
  schemaVersion: 1,
  repoUrl: "https://github.com/acme/docs",
  branch: "main",
  targetPaths: ["docs/**/*.md"],
  languages: ["en"],
  dictionarySet: "default",
  outputRoot: "default",
  translationProvider: "ollama-local",
  reviewProvider: null,
  pushStrategy: "none",
  confirmDirectPush: false
};

test("admin creates, worker completes, and admin cancels jobs", async ({
  baseURL,
  context,
  page,
  request
}) => {
  await page.goto("/login");
  const csrfToken = await login(request, context, baseURL ?? "http://127.0.0.1:3100");
  const workerId = await registerWorker(page);

  const created = await createJob(page, csrfToken);
  expect(created.state).toBe("queued");

  const claim = await claimJob(page, workerId);
  expect(claim.job.config.schemaVersion).toBe(1);

  const completed = await completeJob(page, claim.job.jobId, claim.job.leaseId);
  expect(completed.accepted).toBe(true);

  const cancellable = await createJob(page, csrfToken);
  const cancelled = await cancelJob(page, csrfToken, cancellable.id);
  expect(cancelled.state).toBe("cancelled");

  await page.goto("/jobs");
  await expect(page.getByText("https://github.com/acme/docs").first()).toBeVisible();
});

async function login(
  request: import("@playwright/test").APIRequestContext,
  context: import("@playwright/test").BrowserContext,
  baseURL: string
) {
  const response = await request.post("/api/admin/login", {
    data: { password: "correct-password" },
    headers: { origin: baseURL }
  });
  const setCookie = response.headers()["set-cookie"] ?? "";
  const session = /admin_session=([^;]+)/.exec(setCookie)?.[1];
  if (!session) {
    throw new Error("login did not set an admin session");
  }
  await context.addCookies([
    {
      name: "admin_session",
      value: session,
      url: baseURL,
      sameSite: "Strict"
    }
  ]);
  const body = await response.json();
  return body.csrfToken as string;
}

async function registerWorker(page: import("@playwright/test").Page) {
  return page.evaluate(async (capabilityPayload) => {
    const response = await fetch("/api/worker/v1/register", {
      method: "POST",
      headers: {
        authorization: "Bearer worker-secret",
        "content-type": "application/json",
        "x-worker-version": "e2e"
      },
      body: JSON.stringify({
        schemaVersion: 1,
        capabilities: capabilityPayload
      })
    });
    return ((await response.json()) as { workerId: string }).workerId;
  }, capabilities);
}

async function createJob(page: import("@playwright/test").Page, csrfToken: string) {
  return page.evaluate(
    async ({ csrfToken: token, jobPayload }) => {
      const response = await fetch("/api/admin/jobs", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-csrf-token": token
        },
        body: JSON.stringify(jobPayload)
      });
      return response.json();
    },
    { csrfToken, jobPayload: job }
  );
}

async function claimJob(page: import("@playwright/test").Page, workerId: string) {
  return page.evaluate(
    async ({ capabilityPayload, workerId: id }) => {
      const response = await fetch("/api/worker/v1/claim", {
        method: "POST",
        headers: {
          authorization: "Bearer worker-secret",
          "content-type": "application/json",
          "x-worker-version": "e2e"
        },
        body: JSON.stringify({
          schemaVersion: 1,
          workerId: id,
          capabilities: capabilityPayload
        })
      });
      return response.json();
    },
    { capabilityPayload: capabilities, workerId }
  );
}

async function completeJob(
  page: import("@playwright/test").Page,
  jobId: string,
  leaseId: string
) {
  return page.evaluate(
    async ({ jobId: id, leaseId: lease }) => {
      const response = await fetch(`/api/worker/v1/jobs/${id}/complete`, {
        method: "POST",
        headers: {
          authorization: "Bearer worker-secret",
          "content-type": "application/json",
          "x-worker-version": "e2e"
        },
        body: JSON.stringify({
          schemaVersion: 1,
          leaseId: lease,
          lastSequence: 0,
          result: { status: "succeeded", results: [], issues: [] }
        })
      });
      return response.json();
    },
    { jobId, leaseId }
  );
}

async function cancelJob(
  page: import("@playwright/test").Page,
  csrfToken: string,
  jobId: string
) {
  return page.evaluate(
    async ({ csrfToken: token, jobId: id }) => {
      const response = await fetch(`/api/admin/jobs/${id}/cancel`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-csrf-token": token
        },
        body: "{}"
      });
      return response.json();
    },
    { csrfToken, jobId }
  );
}
