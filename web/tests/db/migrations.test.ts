import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { listTables, migrate, REQUIRED_TABLES } from "@/scripts/migrate";

const testDatabaseUrl = process.env.TEST_DATABASE_URL;

describe("database migrations", () => {
  it("declares all control-plane tables", async () => {
    const sql = await readFile(join(process.cwd(), "migrations/0001_initial.sql"), "utf8");

    for (const table of REQUIRED_TABLES) {
      expect(sql).toContain(`CREATE TABLE IF NOT EXISTS ${table}`);
    }
  });

  const maybeIt = testDatabaseUrl ? it : it.skip;
  maybeIt("creates all control-plane tables", async () => {
    await migrate(testDatabaseUrl);

    const tables = await listTables(testDatabaseUrl);

    expect(tables).toEqual(expect.arrayContaining([...REQUIRED_TABLES]));
  });
});
