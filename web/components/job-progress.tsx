export interface JobProgressProps {
  job: {
    state: string;
    cancelRequested: boolean;
  };
  logs: Array<{
    id: number;
    message?: string;
    stage?: string;
  }>;
}

export function JobProgress({ job, logs }: JobProgressProps) {
  return (
    <section className="panel">
      <div className="status-row">
        <span className="status-pill">{job.state}</span>
        {job.cancelRequested ? <span className="status-pill warning">cancel requested</span> : null}
      </div>
      <ol className="log-list">
        {logs.map((log) => (
          <li key={log.id}>
            <span>{log.stage ?? "worker"}</span>
            <p>{log.message ?? "Progress update received"}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
