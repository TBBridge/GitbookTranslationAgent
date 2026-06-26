import { JobLog } from "@/components/job-log";
import { JobProgress } from "@/components/job-progress";
import { getAdminJobStore } from "@/lib/services/jobs";

export default async function JobDetailPage({
  params
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  const job = process.env.DATABASE_URL ? await getAdminJobStore().get(jobId) : null;
  const logs = process.env.DATABASE_URL ? await getAdminJobStore().logs(jobId) : [];

  if (!job) {
    return <p className="empty-state">Job not found.</p>;
  }

  return (
    <section className="stack">
      <header className="page-header">
        <p className="section-label">Job detail</p>
        <h1>{job.config.repoUrl}</h1>
        <p>{job.config.languages.join(", ")}</p>
      </header>
      <JobProgress job={job} logs={[]} />
      <section className="panel">
        <h2>Logs</h2>
        <JobLog logs={logs} />
      </section>
    </section>
  );
}
