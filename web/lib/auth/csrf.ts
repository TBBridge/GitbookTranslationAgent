import {
  getSessionFromRequest,
  hashSecret,
  safeEqualHash,
  type SessionStore,
  type StoredSession
} from "@/lib/auth/session";

export const CSRF_HEADER = "x-csrf-token";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

export interface AuthenticatedMutation {
  session: StoredSession;
}

export async function requireAdminMutation(
  request: Request,
  store?: SessionStore
): Promise<AuthenticatedMutation | Response> {
  const originFailure = requireSameOriginMutation(request);
  if (originFailure) {
    return originFailure;
  }

  const session = await getSessionFromRequest(request, store);
  if (!session) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const csrfToken = request.headers.get(CSRF_HEADER);
  if (!csrfToken || !safeEqualHash(hashSecret(csrfToken), session.csrfHash)) {
    return Response.json({ error: "Invalid CSRF token" }, { status: 403 });
  }

  return { session };
}

export function requireSameOriginMutation(request: Request) {
  if (SAFE_METHODS.has(request.method.toUpperCase())) {
    return null;
  }

  const origin = request.headers.get("origin");
  const expectedOrigins = expectedRequestOrigins(request);
  if (!origin || !expectedOrigins.has(origin)) {
    return Response.json({ error: "Cross-origin mutation rejected" }, { status: 403 });
  }

  return null;
}

function expectedRequestOrigins(request: Request) {
  const url = new URL(request.url);
  const origins = new Set([url.origin]);
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (host) {
    const proto =
      request.headers.get("x-forwarded-proto") ??
      url.protocol.replace(/:$/, "") ??
      "https";
    origins.add(`${proto}://${host}`);
  }
  return origins;
}
