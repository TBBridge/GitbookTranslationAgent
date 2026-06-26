import { hashSecret, safeEqualHash } from "@/lib/auth/session";

export interface AuthenticatedWorker {
  tokenFingerprint: string;
}

export function authenticateWorkerRequest(
  request: Request
): AuthenticatedWorker | Response {
  const token = parseBearerToken(request.headers.get("authorization"));
  if (!token) {
    return unauthorized();
  }

  for (const configuredToken of configuredWorkerTokens()) {
    if (safeEqualHash(hashSecret(token), hashSecret(configuredToken))) {
      return {
        tokenFingerprint: hashSecret(token)
      };
    }
  }

  return unauthorized();
}

export function parseBearerToken(header: string | null) {
  if (!header) {
    return null;
  }
  const match = /^Bearer\s+(.+)$/i.exec(header.trim());
  return match?.[1]?.trim() || null;
}

function configuredWorkerTokens() {
  const tokens: string[] = [];
  if (process.env.WORKER_TOKEN) {
    tokens.push(process.env.WORKER_TOKEN);
  }

  if (process.env.WORKER_TOKENS) {
    try {
      const parsed = JSON.parse(process.env.WORKER_TOKENS) as unknown;
      if (Array.isArray(parsed)) {
        tokens.push(...parsed.filter((value): value is string => typeof value === "string"));
      } else if (parsed && typeof parsed === "object") {
        tokens.push(
          ...Object.values(parsed).filter(
            (value): value is string => typeof value === "string"
          )
        );
      }
    } catch {
      tokens.push(
        ...process.env.WORKER_TOKENS.split(",")
          .map((token) => token.trim())
          .filter(Boolean)
      );
    }
  }

  return tokens;
}

function unauthorized() {
  return Response.json({ error: "Unauthorized worker" }, { status: 401 });
}
