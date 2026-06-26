import { requireSameOriginMutation } from "@/lib/auth/csrf";
import {
  buildExpiredSessionCookie,
  deleteSessionFromRequest
} from "@/lib/auth/session";

export async function POST(request: Request) {
  const originFailure = requireSameOriginMutation(request);
  if (originFailure) {
    return originFailure;
  }

  await deleteSessionFromRequest(request);
  const response = Response.json({ ok: true });
  response.headers.append("set-cookie", buildExpiredSessionCookie());
  return response;
}
