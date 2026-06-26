import { requireAdminMutation } from "@/lib/auth/csrf";
import { retryAdminJob } from "@/lib/services/jobs";

export async function POST(
  request: Request,
  context: { params: Promise<{ jobId: string }> }
) {
  const guard = await requireAdminMutation(request);
  if (guard instanceof Response) {
    return guard;
  }

  const { jobId } = await context.params;
  const job = await retryAdminJob(jobId);
  if (!job) {
    return Response.json({ error: "Job not found" }, { status: 404 });
  }
  return Response.json(job, { status: 201 });
}
