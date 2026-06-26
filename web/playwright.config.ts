import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.PLAYWRIGHT_PORT ?? 3100);

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ],
  webServer: {
    command: `npm run dev -- --hostname 127.0.0.1 --port ${port}`,
    env: {
      ADMIN_PASSWORD_HASH:
        "$argon2id$v=19$m=19456,t=2,p=1$30lSHveygLyH7to88CU5nQ$KrxyHdMmzkD4eR2rloEOM6gzlVPhU5oaR7EiEIByVa4",
      E2E_IN_MEMORY: "1",
      WORKER_TOKEN: "worker-secret"
    },
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    url: `http://127.0.0.1:${port}`
  }
});
