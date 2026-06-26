import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE_NAME } from "@/lib/auth/session";

const PUBLIC_PREFIXES = ["/login", "/api/admin/login", "/api/worker"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/api/admin") || pathname.startsWith("/jobs")) {
    const hasSession = request.cookies.has(SESSION_COOKIE_NAME);
    if (!hasSession) {
      const loginUrl = new URL("/login", request.url);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|favicon.ico).*)"]
};
