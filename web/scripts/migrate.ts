import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { neon } from "@neondatabase/serverless";

export const REQUIRED_TABLES = [
  "admin_sessions",
  "admin_login_attempts",
  "workers",
  "jobs",
  "job_attempts",
  "job_logs"
] as const;

const MIGRATION_TABLE_SQL = `
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)`;

export async function migrate(
  databaseUrl = process.env.DATABASE_URL,
  migrationsDir = join(process.cwd(), "migrations")
) {
  const sql = neon(requireDatabaseUrl(databaseUrl));
  await sql.query(MIGRATION_TABLE_SQL, []);

  const filenames = (await readdir(migrationsDir))
    .filter((filename) => filename.endsWith(".sql"))
    .sort();

  for (const filename of filenames) {
    const applied = await sql`
      SELECT filename
      FROM schema_migrations
      WHERE filename = ${filename}
    `;
    if (applied.length > 0) {
      continue;
    }

    const migrationSql = await readFile(join(migrationsDir, filename), "utf8");
    for (const statement of splitSqlStatements(migrationSql)) {
      await sql.query(statement, []);
    }

    await sql`
      INSERT INTO schema_migrations (filename)
      VALUES (${filename})
      ON CONFLICT (filename) DO NOTHING
    `;
  }
}

export async function listTables(databaseUrl = process.env.DATABASE_URL) {
  const sql = neon(requireDatabaseUrl(databaseUrl));
  const rows = await sql`
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename
  `;

  return rows.map((row) => String(row.tablename));
}

export function splitSqlStatements(sql: string) {
  return sql
    .split(/;\s*(?:\r?\n|$)/)
    .map((statement) => statement.trim())
    .filter(Boolean);
}

function requireDatabaseUrl(databaseUrl: string | undefined) {
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required");
  }
  return databaseUrl;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  migrate().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
