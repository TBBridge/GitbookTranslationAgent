import { verifyAdminPassword } from "@/lib/auth/password";
import {
  buildSessionCookie,
  createAdminSession,
  hashSecret
} from "@/lib/auth/session";
import { requireSameOriginMutation } from "@/lib/auth/csrf";
import { isLoginRateLimited, recordLoginAttempt } from "@/lib/auth/rate-limit";

export async function POST(request: Request) {
  const originFailure = requireSameOriginMutation(request);
  if (originFailure) {
    return originFailure;
  }

  const body = await readJson(request);
  const password = body?.password;
  const ipHash = hashSecret(clientIp(request));

  if (await rateLimited(ipHash)) {
    return Response.json({ error: "Too many login attempts" }, { status: 429 });
  }

  const valid = await verifyAdminPassword(password);
  await recordAttemptIfConfigured(ipHash, valid);

  if (!valid) {
    return Response.json({ error: "Invalid credentials" }, { status: 401 });
  }

  const session = await createAdminSession();
  const response = Response.json({ csrfToken: session.csrfToken });
  response.headers.append("set-cookie", buildSessionCookie(session));
  return response;
}

async function readJson(request: Request): Promise<Record<string, unknown> | null> {
  try {
    const data = await request.json();
    return data && typeof data === "object" ? (data as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function clientIp(request: Request) {
  const forwarded = request.headers.get("x-forwarded-for");
  return forwarded?.split(",")[0]?.trim() || "unknown";
}

async function rateLimited(ipHash: string) {
  if (!process.env.DATABASE_URL) {
    return false;
  }
  return isLoginRateLimited(ipHash);
}

async function recordAttemptIfConfigured(ipHash: string, succeeded: boolean) {
  if (process.env.DATABASE_URL) {
    await recordLoginAttempt(ipHash, succeeded);
  }
}
