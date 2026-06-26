import Link from "next/link";

import { getAdminJobStore } from "@/lib/services/jobs";

export default async function JobsPage() {
  const shouldReadStore = process.env.DATABASE_URL || process.env.E2E_IN_MEMORY === "1";
  const jobs = shouldReadStore ? await getAdminJobStore().list() : [];

  return (
    <section className="stack">
      <header className="page-header">
        <p className="section-label">History</p>
        <h1>Jobs</h1>
      </header>
      <div className="panel">
        {jobs.length === 0 ? (
          <p className="empty-state">No jobs yet.</p>
        ) : (
          <ul className="job-list">
            {jobs.map((job) => (
              <li key={job.id}>
                <Link href={`/jobs/${job.id}`}>{job.config.repoUrl}</Link>
                <span>{job.state}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
