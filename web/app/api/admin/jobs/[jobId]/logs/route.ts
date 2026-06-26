import { getAdminJobStore } from "@/lib/services/jobs";

export async function GET(
  request: Request,
  context: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await context.params;
  const url = new URL(request.url);
  const afterId = Number(url.searchParams.get("afterId") ?? 0);
  const limit = Number(url.searchParams.get("limit") ?? 100);
  return Response.json({
    logs: await getAdminJobStore().logs(jobId, afterId, limit)
  });
}
