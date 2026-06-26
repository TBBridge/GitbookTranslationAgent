import { z } from "zod";

import { authenticateWorkerRequest } from "@/lib/auth/worker";
import { heartbeatWorker } from "@/lib/services/workers";
import { workerCapabilitiesV1Schema } from "@/lib/schemas/worker-v1";

const heartbeatBodySchema = z
  .object({
    schemaVersion: z.literal(1),
    workerId: z.string().min(1),
    capabilities: workerCapabilitiesV1Schema
  })
  .strict();

export async function POST(request: Request) {
  const authenticated = authenticateWorkerRequest(request);
  if (authenticated instanceof Response) {
    return authenticated;
  }

  const parsed = heartbeatBodySchema.safeParse(await readJson(request));
  if (!parsed.success) {
    return Response.json({ error: "Invalid heartbeat payload" }, { status: 400 });
  }

  await heartbeatWorker({
    workerId: parsed.data.workerId,
    capabilities: parsed.data.capabilities,
    tokenFingerprint: authenticated.tokenFingerprint,
    version: request.headers.get("x-worker-version") ?? "unknown"
  });

  return Response.json({ accepted: true });
}

async function readJson(request: Request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}
