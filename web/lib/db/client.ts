import { neon, type NeonQueryFunction } from "@neondatabase/serverless";

export type SqlClient = NeonQueryFunction<false, false>;

let cachedSql: SqlClient | null = null;
let cachedDatabaseUrl: string | null = null;

export function getSql(databaseUrl = process.env.DATABASE_URL): SqlClient {
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required");
  }

  if (cachedSql === null || cachedDatabaseUrl !== databaseUrl) {
    cachedSql = neon(databaseUrl);
    cachedDatabaseUrl = databaseUrl;
  }

  return cachedSql;
}
