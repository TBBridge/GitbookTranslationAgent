# Next.js Web and Neon Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an authenticated Vercel-deployable Next.js control plane that persists jobs in Neon, safely leases work to local workers, and provides job creation, monitoring, cancellation, and retry screens.

**Architecture:** A standalone `web/` Next.js App Router application owns browser authentication and worker APIs. Database access is centralized in `web/lib/db`, validation in shared Zod schemas, and mutations in service modules so route handlers and tests use the same transaction logic.

**Tech Stack:** Next.js App Router, React, TypeScript, Neon serverless driver, Zod, Tailwind CSS, Vitest, Testing Library, Playwright, Vercel.

---

## File Map

- Create `web/` with App Router and strict TypeScript.
- Create `web/migrations/`: SQL schema and migration runner.
- Create `web/lib/db/`: Neon client, queries, and transactions.
- Create `web/lib/auth/`: administrator and worker authentication.
- Create `web/lib/schemas/`: versioned job and API schemas.
- Create `web/app/api/admin/`: browser APIs.
- Create `web/app/api/worker/v1/`: worker APIs.
- Create dashboard, job form, history, and detail pages.

### Task 1: Scaffold the web application and quality commands

**Files:**
- Create: `web/package.json`
- Create: `web/next.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/eslint.config.mjs`
- Create: `web/vitest.config.ts`
- Create: `web/app/layout.tsx`
- Create: `web/app/globals.css`
- Create: `web/lib/constants.ts`
- Test: `web/tests/smoke.test.ts`

- [ ] **Step 1: Write the failing smoke test**

```typescript
import { describe, expect, it } from "vitest";
import { APP_NAME } from "@/lib/constants";

describe("application", () => {
  it("has the configured product name", () => {
    expect(APP_NAME).toBe("GitBook Translation Control");
  });
});
```

- [ ] **Step 2: Verify RED**

```bash
cd web
npm test -- --run tests/smoke.test.ts
```

- [ ] **Step 3: Add the minimal Next.js project**

Use:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit",
    "test": "vitest",
    "test:run": "vitest run",
    "test:e2e": "playwright test"
  }
}
```

Install runtime dependencies with:

```bash
npm install next react react-dom @neondatabase/serverless zod @node-rs/argon2
npm install -D typescript @types/node @types/react @types/react-dom eslint eslint-config-next vitest @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom @playwright/test tsx
```

Add strict TypeScript, `@/*` aliases, metadata, semantic layout, and responsive neutral styling.

- [ ] **Step 4: Verify GREEN**

```bash
npm test -- --run tests/smoke.test.ts
npm run typecheck
npm run lint
```

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: scaffold translation control web app"
```

### Task 2: Add Neon schema and typed database access

**Files:**
- Create: `web/migrations/0001_initial.sql`
- Create: `web/scripts/migrate.ts`
- Create: `web/lib/db/client.ts`
- Create: `web/lib/db/types.ts`
- Create: `web/lib/db/jobs.ts`
- Test: `web/tests/db/migrations.test.ts`

- [ ] **Step 1: Write the failing migration test**

```typescript
it("creates all control-plane tables", async () => {
  await migrate(testDatabaseUrl);
  const tables = await listTables(testDatabaseUrl);
  expect(tables).toEqual(expect.arrayContaining([
    "admin_sessions", "admin_login_attempts", "workers",
    "jobs", "job_attempts", "job_logs"
  ]));
});
```

- [ ] **Step 2: Verify RED**

```bash
TEST_DATABASE_URL="$TEST_DATABASE_URL" npm test -- --run tests/db/migrations.test.ts
```

- [ ] **Step 3: Implement schema and DB helpers**

Use UUID keys, JSONB configuration/capability fields, timestamptz, status constraints, queued-job and log indexes, and foreign keys. Add bounded `admin_login_attempts` records for Vercel-safe login throttling. Store only worker-token fingerprints and lease-token hashes. Record applied migration filenames in `schema_migrations`.

- [ ] **Step 4: Verify GREEN**

```bash
TEST_DATABASE_URL="$TEST_DATABASE_URL" npm test -- --run tests/db/migrations.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/migrations web/scripts web/lib/db web/tests/db
git commit -m "feat: add neon control-plane schema"
```

### Task 3: Implement administrator authentication, sessions, and CSRF

**Files:**
- Create: `web/lib/auth/password.ts`
- Create: `web/lib/auth/session.ts`
- Create: `web/lib/auth/csrf.ts`
- Create: `web/lib/auth/rate-limit.ts`
- Create: `web/app/login/page.tsx`
- Create: `web/app/api/admin/login/route.ts`
- Create: `web/app/api/admin/logout/route.ts`
- Create: `web/middleware.ts`
- Test: `web/tests/auth/admin-auth.test.ts`

- [ ] **Step 1: Write failing auth tests**

```typescript
it("sets a secure http-only strict cookie after valid login", async () => {
  const response = await loginRequest("correct-password");
  const cookie = response.headers.get("set-cookie") ?? "";
  expect(cookie).toContain("HttpOnly");
  expect(cookie).toContain("Secure");
  expect(cookie).toContain("SameSite=Strict");
});


it("rejects a cross-origin mutation", async () => {
  const response = await createJobRequest({ origin: "https://evil.test" });
  expect(response.status).toBe(403);
});
```

- [ ] **Step 2: Verify RED**

```bash
npm test -- --run tests/auth/admin-auth.test.ts
```

- [ ] **Step 3: Implement authentication**

Verify `ADMIN_PASSWORD_HASH` with Argon2. Generate 32-byte session IDs, store SHA-256 hashes in Postgres, and place raw IDs only in `HttpOnly`, `Secure`, `SameSite=Strict` cookies. Require same-origin plus a per-session CSRF header for mutations. Add bounded database-backed login throttling.

- [ ] **Step 4: Verify GREEN**

```bash
npm test -- --run tests/auth/admin-auth.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/auth web/app/login web/app/api/admin/login web/app/api/admin/logout web/middleware.ts web/tests/auth
git commit -m "feat: secure administrator access"
```

### Task 4: Define the versioned job schema and capability matching

**Files:**
- Create: `web/lib/schemas/job-v1.ts`
- Create: `web/lib/schemas/worker-v1.ts`
- Create: `web/lib/services/capabilities.ts`
- Test: `web/tests/schemas/job-v1.test.ts`
- Test: `web/tests/services/capabilities.test.ts`

- [ ] **Step 1: Write failing schema tests**

```typescript
it("accepts zh-CN as a language tag", () => {
  const config = jobV1Schema.parse(validJob({ languages: ["zh-CN"] }));
  expect(config.languages).toEqual(["zh-CN"]);
});


it("rejects arbitrary local output paths", () => {
  expect(() => jobV1Schema.parse(
    validJob({ outputRoot: "/tmp/output" })
  )).toThrow();
});
```

- [ ] **Step 2: Verify RED**

```bash
npm test -- --run tests/schemas/job-v1.test.ts tests/services/capabilities.test.ts
```

- [ ] **Step 3: Implement schemas and matching**

The immutable payload uses names such as `dictionarySet: "default"` and `outputRoot: "translations"`, never paths. Include provider/models, target patterns, languages, limits, naming, push strategy, and direct-push confirmation. Compatibility requires one online worker to advertise every selected capability.

- [ ] **Step 4: Verify GREEN**

```bash
npm test -- --run tests/schemas/job-v1.test.ts tests/services/capabilities.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/schemas web/lib/services/capabilities.ts web/tests/schemas web/tests/services
git commit -m "feat: validate versioned translation jobs"
```

### Task 5: Implement worker registration and heartbeat

**Files:**
- Create: `web/lib/auth/worker.ts`
- Create: `web/lib/services/workers.ts`
- Create: `web/app/api/worker/v1/register/route.ts`
- Create: `web/app/api/worker/v1/heartbeat/route.ts`
- Test: `web/tests/api/worker-registration.test.ts`

- [ ] **Step 1: Write failing worker-auth tests**

```typescript
it("rejects an invalid worker bearer token", async () => {
  const response = await registerWorker({ authorization: "Bearer wrong" });
  expect(response.status).toBe(401);
});


it("stores capabilities without local paths", async () => {
  await registerWorker({ body: workerRegistration });
  const worker = await getWorker("office-mac");
  expect(JSON.stringify(worker.capabilities)).not.toContain("/Users/");
});
```

- [ ] **Step 2: Verify RED**

```bash
npm test -- --run tests/api/worker-registration.test.ts
```

- [ ] **Step 3: Implement worker identity**

Compare bearer tokens in constant time against `WORKER_TOKEN` or a configured token map and derive a stable fingerprint. Upsert worker name, version, capabilities, and heartbeat. Reject unknown fields and path-like capability values.

- [ ] **Step 4: Verify GREEN**

```bash
npm test -- --run tests/api/worker-registration.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/auth/worker.ts web/lib/services/workers.ts web/app/api/worker/v1/register web/app/api/worker/v1/heartbeat web/tests/api/worker-registration.test.ts
git commit -m "feat: register authenticated local workers"
```

### Task 6: Implement transactional claim and lease lifecycle

**Files:**
- Create: `web/lib/services/leases.ts`
- Create: `web/lib/services/progress.ts`
- Create: `web/app/api/worker/v1/claim/route.ts`
- Create: `web/app/api/worker/v1/renew/route.ts`
- Create: `web/app/api/worker/v1/updates/route.ts`
- Create: `web/app/api/worker/v1/cancellation/route.ts`
- Create: `web/app/api/worker/v1/complete/route.ts`
- Test: `web/tests/api/worker-lifecycle.test.ts`

- [ ] **Step 1: Write failing concurrency tests**

```typescript
it("allows only one concurrent claim for a queued job", async () => {
  const [a, b] = await Promise.all([claim("worker-a"), claim("worker-b")]);
  expect([a.status, b.status].sort()).toEqual([200, 204]);
});


it("rejects completion with a stale lease token", async () => {
  const response = await completeJob({ leaseToken: "expired" });
  expect(response.status).toBe(409);
});
```

- [ ] **Step 2: Verify RED**

```bash
npm test -- --run tests/api/worker-lifecycle.test.ts
```

- [ ] **Step 3: Implement lease transactions**

Claim with this transaction shape, plus capability predicates:

```sql
WITH candidate AS (
  SELECT id
  FROM jobs
  WHERE state = 'queued' AND cancel_requested = false
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE jobs
SET state = 'leased', assigned_worker_id = $1, updated_at = now()
WHERE id = (SELECT id FROM candidate)
RETURNING *;
```

Insert an attempt row in the same transaction with a random lease token whose SHA-256 hash is stored and a bounded expiration. Renewal and updates require worker ID, attempt ID, lease hash, and an unexpired lease. Completion transitions attempt and job in one transaction. Expired attempts become stale and jobs retryable.

- [ ] **Step 4: Verify GREEN**

```bash
npm test -- --run tests/api/worker-lifecycle.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/services/leases.ts web/lib/services/progress.ts web/app/api/worker/v1 web/tests/api/worker-lifecycle.test.ts
git commit -m "feat: lease jobs to local workers"
```

### Task 7: Implement administrator job APIs

**Files:**
- Create: `web/lib/services/jobs.ts`
- Create: `web/app/api/admin/jobs/route.ts`
- Create: `web/app/api/admin/jobs/[jobId]/route.ts`
- Create: `web/app/api/admin/jobs/[jobId]/cancel/route.ts`
- Create: `web/app/api/admin/jobs/[jobId]/retry/route.ts`
- Create: `web/app/api/admin/jobs/[jobId]/logs/route.ts`
- Test: `web/tests/api/admin-jobs.test.ts`

- [ ] **Step 1: Write failing job tests**

```typescript
it("creates an immutable queued job", async () => {
  const response = await createJob(validJob());
  expect(response.status).toBe(201);
  expect((await response.json()).state).toBe("queued");
});


it("retry creates a child job", async () => {
  const response = await retryJob(failedJobId);
  const body = await response.json();
  expect(body.parentJobId).toBe(failedJobId);
  expect(body.id).not.toBe(failedJobId);
});
```

- [ ] **Step 2: Verify RED**

```bash
npm test -- --run tests/api/admin-jobs.test.ts
```

- [ ] **Step 3: Implement admin services and routes**

Require session, same-origin, and CSRF for mutations. Validate compatibility at creation. Cancellation sets `cancel_requested`; queued jobs cancel immediately. Retry copies configuration into a new queued child. Paginate logs by monotonic ID and sanitize before persistence.

- [ ] **Step 4: Verify GREEN**

```bash
npm test -- --run tests/api/admin-jobs.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/lib/services/jobs.ts web/app/api/admin/jobs web/tests/api/admin-jobs.test.ts
git commit -m "feat: manage translation jobs through admin api"
```

### Task 8: Build dashboard, creation, history, and detail pages

**Files:**
- Create: `web/app/(admin)/layout.tsx`
- Create: `web/app/(admin)/page.tsx`
- Create: `web/app/(admin)/jobs/new/page.tsx`
- Create: `web/app/(admin)/jobs/page.tsx`
- Create: `web/app/(admin)/jobs/[jobId]/page.tsx`
- Create: `web/components/job-form.tsx`
- Create: `web/components/job-progress.tsx`
- Create: `web/components/job-log.tsx`
- Create: `web/components/worker-status.tsx`
- Test: `web/tests/components/job-form.test.tsx`
- Test: `web/tests/components/job-progress.test.tsx`

- [ ] **Step 1: Write failing UI tests**

```typescript
it("shows only capabilities from the selected worker", async () => {
  render(<JobForm workers={[workerFixture]} />);
  await user.selectOptions(screen.getByLabelText("Worker"), "office-mac");
  expect(screen.getByRole("option", { name: "qwen3:latest" })).toBeVisible();
  expect(screen.queryByRole("option", { name: "unavailable-model" })).toBeNull();
});


it("requires typed confirmation for direct push", async () => {
  render(<JobForm workers={[workerFixture]} />);
  await selectDirectPush(user);
  expect(screen.getByRole("button", { name: "Create job" })).toBeDisabled();
});
```

- [ ] **Step 2: Verify RED**

```bash
npm test -- --run tests/components/job-form.test.tsx tests/components/job-progress.test.tsx
```

- [ ] **Step 3: Implement accessible pages**

Use server components for initial data and small client components for forms and active-job polling. Poll every two seconds only while active and back off when hidden. Show output-root names and returned local paths with no download action. Include progress, logs, errors, compare URLs, cancel, and retry.

- [ ] **Step 4: Verify GREEN and build**

```bash
npm test -- --run tests/components/job-form.test.tsx tests/components/job-progress.test.tsx
npm run lint
npm run typecheck
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add web/app web/components web/tests/components
git commit -m "feat: add translation job administration ui"
```

### Task 9: Add browser E2E coverage and Vercel configuration

**Files:**
- Create: `web/playwright.config.ts`
- Create: `web/tests/e2e/admin-job-flow.spec.ts`
- Create: `web/vercel.json`
- Create: `web/.env.example`
- Modify: `web/package.json`

- [ ] **Step 1: Write the failing E2E flow**

The test logs in, observes a fake worker, creates a local-only job, observes queued/running states after claim, observes progress, completes it, and sees succeeded. It then creates another job, requests cancellation, and sees cancelled.

- [ ] **Step 2: Verify RED**

```bash
npm run test:e2e -- admin-job-flow.spec.ts
```

- [ ] **Step 3: Add E2E fixtures and Vercel settings**

Use a dedicated test database and API-level fake worker. Configure only required function settings; do not create long-running translation functions. Document `DATABASE_URL`, `ADMIN_PASSWORD_HASH`, `SESSION_SECRET`, and `WORKER_TOKEN`.

- [ ] **Step 4: Verify the web phase**

```bash
npm run lint
npm run typecheck
npm run test:run
npm run build
npm run test:e2e
```

- [ ] **Step 5: Commit**

```bash
git add web/playwright.config.ts web/tests/e2e web/vercel.json web/.env.example web/package.json
git commit -m "test: verify web translation job lifecycle"
```
