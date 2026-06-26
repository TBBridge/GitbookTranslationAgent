import type { AdminJobLog } from "@/lib/services/jobs";

export function JobLog({ logs }: { logs: AdminJobLog[] }) {
  if (logs.length === 0) {
    return <p className="empty-state">No progress has been reported yet.</p>;
  }

  return (
    <ol className="log-list">
      {logs.map((log) => (
        <li key={log.id}>
          <span>#{log.sequence}</span>
          <pre>{JSON.stringify(log.event, null, 2)}</pre>
        </li>
      ))}
    </ol>
  );
}
