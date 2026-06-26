const AUTH_HEADER_RE = /(Authorization:\s*(?:Bearer|Basic)\s+)([^\s"']+)/gi;
const COOKIE_HEADER_RE = /(Cookie:\s*)([^\n"']+)/gi;
const SECRET_PAIR_RE = /\b(token|api[_-]?key|secret|password|cookie)=([^&\s"']+)/gi;

export function sanitizeProgressEvent<T>(event: T): T {
  return redact(event) as T;
}

function redact(value: unknown): unknown {
  if (typeof value === "string") {
    return value
      .replace(AUTH_HEADER_RE, "$1[REDACTED]")
      .replace(COOKIE_HEADER_RE, "$1[REDACTED]")
      .replace(SECRET_PAIR_RE, "$1=[REDACTED]");
  }
  if (Array.isArray(value)) {
    return value.map((item) => redact(item));
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        isSecretKey(key) ? "[REDACTED]" : redact(item)
      ])
    );
  }
  return value;
}

function isSecretKey(key: string) {
  return ["authorization", "cookie", "credentials", "password", "secret", "token"].includes(
    key.toLowerCase()
  );
}
