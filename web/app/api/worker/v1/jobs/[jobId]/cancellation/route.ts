import { authenticateWorkerRequest } from "@/lib/auth/worker";
import { getLeaseStore } from "@/lib/services/leases";

export async function GET(
  request: Request,
  context: { params: Promise<{ jobId: string }> }
) {
  const authenticated = authenticateWorkerRequest(request);
  if (authenticated instanceof Response) {
    return authenticated;
  }

  const leaseId = new URL(request.url).searchParams.get("leaseId");
  if (!leaseId) {
    return Response.json({ error: "leaseId is required" }, { status: 400 });
  }

  const { jobId } = await context.params;
  return Response.json(await getLeaseStore().cancellationState(jobId, leaseId));
}
