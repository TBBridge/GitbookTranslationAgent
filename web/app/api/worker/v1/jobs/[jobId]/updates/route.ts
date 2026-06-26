import { z } from "zod";

import { authenticateWorkerRequest } from "@/lib/auth/worker";
import { getLeaseStore, LeaseConflictError } from "@/lib/services/leases";

const updatesBodySchema = z
  .object({
    schemaVersion: z.literal(1),
    leaseId: z.string().min(1),
    firstSequence: z.number().int().positive(),
    updates: z.array(z.unknown()).min(1)
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

  const parsed = updatesBodySchema.safeParse(await readJson(request));
  if (!parsed.success) {
    return Response.json({ error: "Invalid updates payload" }, { status: 400 });
  }

  const { jobId } = await context.params;
  try {
    return Response.json(
      await getLeaseStore().appendUpdates({
        jobId,
        leaseId: parsed.data.leaseId,
        firstSequence: parsed.data.firstSequence,
        updates: parsed.data.updates
      })
    );
  } catch (error) {
    if (error instanceof LeaseConflictError) {
      return Response.json({ error: "Stale lease" }, { status: 409 });
    }
    throw error;
  }
}

async function readJson(request: Request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}
