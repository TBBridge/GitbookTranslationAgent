import { createHash, randomBytes, timingSafeEqual } from "node:crypto";

import { getSql, type SqlClient } from "@/lib/db/client";

export const SESSION_COOKIE_NAME = "admin_session";
export const SESSION_TTL_SECONDS = 12 * 60 * 60;

export interface StoredSession {
  sessionHash: string;
  csrfHash: string;
  expiresAt: Date;
}

export interface CreatedSession {
  sessionId: string;
  csrfToken: string;
  expiresAt: Date;
}

export interface SessionStore {
  create(session: StoredSession): Promise<void>;
  delete(sessionHash: string): Promise<void>;
  find(sessionHash: string): Promise<StoredSession | null>;
}

let sessionStoreForTests: SessionStore | null = null;

export class DatabaseSessionStore implements SessionStore {
  constructor(private readonly sql: SqlClient = getSql()) {}

  async create(session: StoredSession) {
    await this.sql`
      INSERT INTO admin_sessions (session_hash, csrf_hash, expires_at)
      VALUES (${session.sessionHash}, ${session.csrfHash}, ${session.expiresAt.toISOString()})
      ON CONFLICT (session_hash) DO UPDATE
        SET csrf_hash = EXCLUDED.csrf_hash,
            expires_at = EXCLUDED.expires_at,
            last_seen_at = now()
    `;
  }

  async delete(sessionHash: string) {
    await this.sql`
      DELETE FROM admin_sessions
      WHERE session_hash = ${sessionHash}
    `;
  }

  async find(sessionHash: string) {
    const rows = await this.sql`
      UPDATE admin_sessions
      SET last_seen_at = now()
      WHERE session_hash = ${sessionHash}
        AND expires_at > now()
      RETURNING session_hash, csrf_hash, expires_at
    `;
    const row = rows[0];
    if (!row) {
      return null;
    }
    return {
      sessionHash: String(row.session_hash),
      csrfHash: String(row.csrf_hash),
      expiresAt: new Date(String(row.expires_at))
    };
  }
}

export class MemorySessionStore implements SessionStore {
  private readonly sessions = new Map<string, StoredSession>();

  async create(session: StoredSession) {
    this.sessions.set(session.sessionHash, session);
  }

  async delete(sessionHash: string) {
    this.sessions.delete(sessionHash);
  }

  async find(sessionHash: string) {
    const session = this.sessions.get(sessionHash) ?? null;
    if (session && session.expiresAt > new Date()) {
      return session;
    }
    if (session) {
      this.sessions.delete(sessionHash);
    }
    return null;
  }
}

export function setSessionStoreForTests(store: SessionStore | null) {
  sessionStoreForTests = store;
}

export function getSessionStore() {
  if (process.env.E2E_IN_MEMORY === "1") {
    return e2eMemorySessionStore();
  }
  return sessionStoreForTests ?? new DatabaseSessionStore();
}

export async function createAdminSession(
  store: SessionStore = getSessionStore()
): Promise<CreatedSession> {
  const sessionId = randomToken();
  const csrfToken = randomToken();
  const expiresAt = new Date(Date.now() + SESSION_TTL_SECONDS * 1000);

  await store.create({
    sessionHash: hashSecret(sessionId),
    csrfHash: hashSecret(csrfToken),
    expiresAt
  });

  return { sessionId, csrfToken, expiresAt };
}

export async function getSessionFromRequest(
  request: Request,
  store: SessionStore = getSessionStore()
) {
  const sessionId = readCookie(request, SESSION_COOKIE_NAME);
  if (!sessionId) {
    return null;
  }
  return store.find(hashSecret(sessionId));
}

export async function deleteSessionFromRequest(
  request: Request,
  store: SessionStore = getSessionStore()
) {
  const sessionId = readCookie(request, SESSION_COOKIE_NAME);
  if (sessionId) {
    await store.delete(hashSecret(sessionId));
  }
}

export function buildSessionCookie(session: CreatedSession) {
  return [
    `${SESSION_COOKIE_NAME}=${session.sessionId}`,
    "Path=/",
    "HttpOnly",
    "Secure",
    "SameSite=Strict",
    `Max-Age=${SESSION_TTL_SECONDS}`,
    `Expires=${session.expiresAt.toUTCString()}`
  ].join("; ");
}

export function buildExpiredSessionCookie() {
  return [
    `${SESSION_COOKIE_NAME}=`,
    "Path=/",
    "HttpOnly",
    "Secure",
    "SameSite=Strict",
    "Max-Age=0",
    "Expires=Thu, 01 Jan 1970 00:00:00 GMT"
  ].join("; ");
}

export function readCookie(request: Request, name: string) {
  const header = request.headers.get("cookie");
  if (!header) {
    return null;
  }
  for (const part of header.split(";")) {
    const [rawName, ...rawValue] = part.trim().split("=");
    if (rawName === name) {
      return rawValue.join("=");
    }
  }
  return null;
}

export function hashSecret(secret: string) {
  return createHash("sha256").update(secret).digest("hex");
}

export function safeEqualHash(a: string, b: string) {
  const left = Buffer.from(a, "hex");
  const right = Buffer.from(b, "hex");
  return left.length === right.length && timingSafeEqual(left, right);
}

function randomToken() {
  return randomBytes(32).toString("base64url");
}

function e2eMemorySessionStore() {
  const stores = globalThis as typeof globalThis & {
    __gitbookAdminSessions?: MemorySessionStore;
  };
  stores.__gitbookAdminSessions ??= new MemorySessionStore();
  return stores.__gitbookAdminSessions;
}
