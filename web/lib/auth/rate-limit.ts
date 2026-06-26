import { getSql, type SqlClient } from "@/lib/db/client";

export const LOGIN_ATTEMPT_WINDOW_MINUTES = 15;
export const MAX_FAILED_LOGIN_ATTEMPTS = 10;

export async function isLoginRateLimited(
  ipHash: string,
  sql: SqlClient = getSql()
) {
  const rows = await sql`
    SELECT count(*)::int AS failed_count
    FROM admin_login_attempts
    WHERE ip_hash = ${ipHash}
      AND succeeded = false
      AND attempted_at > now() - (${LOGIN_ATTEMPT_WINDOW_MINUTES} || ' minutes')::interval
  `;
  return Number(rows[0]?.failed_count ?? 0) >= MAX_FAILED_LOGIN_ATTEMPTS;
}

export async function recordLoginAttempt(
  ipHash: string,
  succeeded: boolean,
  sql: SqlClient = getSql()
) {
  await sql`
    INSERT INTO admin_login_attempts (ip_hash, succeeded)
    VALUES (${ipHash}, ${succeeded})
  `;
  await sql`
    DELETE FROM admin_login_attempts
    WHERE attempted_at < now() - interval '7 days'
  `;
}
