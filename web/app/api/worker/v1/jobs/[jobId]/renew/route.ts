import { z } from "zod";

import { authenticateWorkerRequest } from "@/lib/auth/worker";
import { getLeaseStore } from "@/lib/services/leases";

const renewBodySchema = z
  .object({
    schemaVersion: z.literal(1),
    leaseId: z.string().min(1)
  })
  .strict();

export async function POST(
  request: Request,
  context: { params: Promise<{ jobId: string }> }
) {
  const authenticated = authenticateWorkerRequest(request);
  if (authenticated instanceof Response) {
    return authenticated;
  }

  const parsed = renewBodySchema.safeParse(await readJson(request));
  if (!parsed.success) {
    return Response.json({ error: "Invalid renew payload" }, { status: 400 });
  }

  const { jobId } = await context.params;
  return Response.json(await getLeaseStore().renew(jobId, parsed.data.leaseId));
}

async function readJson(request: Request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}
