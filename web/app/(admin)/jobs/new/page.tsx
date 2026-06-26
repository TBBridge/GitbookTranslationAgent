import { JobForm, type JobFormWorker } from "@/components/job-form";
import { getWorkerStore } from "@/lib/services/workers";

export default async function NewJobPage() {
  const shouldReadStore = process.env.DATABASE_URL || process.env.E2E_IN_MEMORY === "1";
  const workers: JobFormWorker[] = shouldReadStore
    ? (await getWorkerStore().list()).map((worker) => ({
        id: worker.id,
        name: worker.name,
        capabilities: worker.capabilities
      }))
    : [];

  return (
    <section className="stack">
      <header className="page-header">
        <p className="section-label">Create</p>
        <h1>New translation job</h1>
        <p>Select a registered local worker and submit an immutable job config.</p>
      </header>
      <JobForm workers={workers} />
    </section>
  );
}
