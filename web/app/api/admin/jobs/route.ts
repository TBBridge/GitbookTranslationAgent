import { requireAdminMutation } from "@/lib/auth/csrf";
import { createAdminJob, getAdminJobStore } from "@/lib/services/jobs";

export async function GET() {
  return Response.json({ jobs: await getAdminJobStore().list() });
}

export async function POST(request: Request) {
  const guard = await requireAdminMutation(request);
  if (guard instanceof Response) {
    return guard;
  }

  const job = await createAdminJob(await readJson(request));
  return Response.json(job, { status: 201 });
}

async function readJson(request: Request) {
  try {
    return await request.json();
  } catch {
    return null;
  }
}
