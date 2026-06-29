import Link from "next/link";
import type { ReactNode } from "react";

// Admin pages read live job/worker data per request and must never be
// prerendered at build time (the database may be unmigrated or unreachable
// during the build). Force dynamic rendering for the whole admin segment.
export const dynamic = "force-dynamic";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="admin-layout">
      <nav className="top-nav" aria-label="Primary">
        <Link href="/">Dashboard</Link>
        <Link href="/jobs/new">New job</Link>
        <Link href="/jobs">History</Link>
      </nav>
      {children}
    </div>
  );
}
