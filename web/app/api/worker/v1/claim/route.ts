import { z } from "zod";

import { authenticateWorkerRequest } from "@/lib/auth/worker";
import { getLeaseStore } from "@/lib/services/leases";
import { workerCapabilitiesV1Schema } from "@/lib/schemas/worker-v1";

const claimBodySchema = z
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

  const parsed = claimBodySchema.safeParse(await readJson(request));
  if (!parsed.success) {
    return Response.json({ error: "Invalid claim payload" }, { status: 400 });
  }

  const claim = await getLeaseStore().claim({
    workerId: parsed.data.workerId,
    capabilities: parsed.data.capabilities
  });

  if (!claim) {
    return new Response(null, { status: 204 });
  }

  return Response.json({
    job: {
      jobId: claim.jobId,
      leaseId: claim.leaseId,
      leaseExpiresAt: claim.leaseExpiresAt,
      config: claim.config
    }
  });
}

async function readJson(request: Request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}
