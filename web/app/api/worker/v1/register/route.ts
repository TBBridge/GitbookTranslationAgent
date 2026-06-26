import { z } from "zod";

import { authenticateWorkerRequest } from "@/lib/auth/worker";
import { registerWorker } from "@/lib/services/workers";
import { workerCapabilitiesV1Schema } from "@/lib/schemas/worker-v1";

const registerBodySchema = z
  .object({
    schemaVersion: z.literal(1),
    capabilities: workerCapabilitiesV1Schema
  })
  .strict();

export async function POST(request: Request) {
  const authenticated = authenticateWorkerRequest(request);
  if (authenticated instanceof Response) {
    return authenticated;
  }

  const parsed = registerBodySchema.safeParse(await readJson(request));
  if (!parsed.success) {
    return Response.json({ error: "Invalid worker payload" }, { status: 400 });
  }

  const worker = await registerWorker({
    capabilities: parsed.data.capabilities,
    tokenFingerprint: authenticated.tokenFingerprint,
    version: request.headers.get("x-worker-version") ?? "unknown"
  });

  return Response.json({ workerId: worker.id });
}

async function readJson(request: Request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}
