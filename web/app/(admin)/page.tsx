import { JobProgress } from "@/components/job-progress";
import { WorkerStatus } from "@/components/worker-status";
import { APP_NAME } from "@/lib/constants";
import { getAdminJobStore } from "@/lib/services/jobs";
import { getWorkerStore } from "@/lib/services/workers";

export default async function DashboardPage() {
  const jobs = process.env.DATABASE_URL ? await getAdminJobStore().list(5) : [];
  const workers = process.env.DATABASE_URL ? await getWorkerStore().list() : [];
  const activeJob = jobs.find((job) => ["queued", "leased", "running"].includes(job.state));

  return (
    <section className="stack">
      <header className="page-header">
        <p className="section-label">Control plane</p>
        <h1>{APP_NAME}</h1>
        <p>Launch translations on local workers and monitor every leased job.</p>
      </header>
      <WorkerStatus workers={workers} />
      {activeJob ? (
        <JobProgress
          job={activeJob}
          logs={[{ id: 1, stage: "state", message: `Job is ${activeJob.state}` }]}
        />
      ) : (
        <p className="empty-state">No active jobs.</p>
      )}
    </section>
  );
}
