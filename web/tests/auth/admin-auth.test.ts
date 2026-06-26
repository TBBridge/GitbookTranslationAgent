import { hash } from "@node-rs/argon2";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { POST as login } from "@/app/api/admin/login/route";
import { requireSameOriginMutation } from "@/lib/auth/csrf";
import { MemorySessionStore, setSessionStoreForTests } from "@/lib/auth/session";

describe("administrator authentication", () => {
  beforeEach(async () => {
    process.env.ADMIN_PASSWORD_HASH = await hash("correct-password");
    setSessionStoreForTests(new MemorySessionStore());
  });

  afterEach(() => {
    delete process.env.ADMIN_PASSWORD_HASH;
    setSessionStoreForTests(null);
  });

  it("sets a secure http-only strict cookie after valid login", async () => {
    const response = await loginRequest("correct-password");
    const cookie = response.headers.get("set-cookie") ?? "";
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("SameSite=Strict");
    expect(body.csrfToken).toEqual(expect.any(String));
  });

  it("rejects an invalid password without setting a session cookie", async () => {
    const response = await loginRequest("wrong-password");

    expect(response.status).toBe(401);
    expect(response.headers.get("set-cookie")).toBeNull();
  });

  it("rejects a cross-origin mutation", () => {
    const request = new Request("https://control.test/api/admin/jobs", {
      method: "POST",
      headers: {
        origin: "https://evil.test"
      }
    });

    const response = requireSameOriginMutation(request);

    expect(response?.status).toBe(403);
  });
});

function loginRequest(password: string, origin = "https://control.test") {
  return login(
    new Request("https://control.test/api/admin/login", {
      method: "POST",
      headers: {
        "content-type": "application/json",
        origin
      },
      body: JSON.stringify({ password })
    })
  );
}
