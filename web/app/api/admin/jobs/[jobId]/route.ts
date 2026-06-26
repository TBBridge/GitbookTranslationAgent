import { getAdminJobStore } from "@/lib/services/jobs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await context.params;
  const job = await getAdminJobStore().get(jobId);
  if (!job) {
    return Response.json({ error: "Job not found" }, { status: 404 });
  }
  return Response.json(job);
}
