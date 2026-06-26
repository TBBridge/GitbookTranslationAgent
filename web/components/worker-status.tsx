import type { WorkerRecord } from "@/lib/services/workers";

export function WorkerStatus({ workers }: { workers: WorkerRecord[] }) {
  if (workers.length === 0) {
    return <p className="empty-state">No workers have registered yet.</p>;
  }

  return (
    <ul className="worker-list">
      {workers.map((worker) => (
        <li key={worker.id} className="panel compact">
          <strong>{worker.name}</strong>
          <span>{worker.version}</span>
          <span>{worker.capabilities.providers.length} providers</span>
        </li>
      ))}
    </ul>
  );
}
