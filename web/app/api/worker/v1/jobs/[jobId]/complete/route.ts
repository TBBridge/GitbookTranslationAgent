import { z } from "zod";

import { authenticateWorkerRequest } from "@/lib/auth/worker";
import { getLeaseStore, LeaseConflictError } from "@/lib/services/leases";

const resultSchema = z
  .object({
    status: z.enum(["succeeded", "partial", "failed", "cancelled"])
  })
  .passthrough();

const completeBodySchema = z
  .object({
    schemaVersion: z.literal(1),
    leaseId: z.string().min(1),
    lastSequence: z.number().int().nonnegative().nullable().optional(),
    result: resultSchema
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

  const parsed = completeBodySchema.safeParse(await readJson(request));
  if (!parsed.success) {
    return Response.json({ error: "Invalid completion payload" }, { status: 400 });
  }

  const { jobId } = await context.params;
  try {
    return Response.json(
      await getLeaseStore().complete({
        jobId,
        leaseId: parsed.data.leaseId,
        result: parsed.data.result,
        lastSequence: parsed.data.lastSequence
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
