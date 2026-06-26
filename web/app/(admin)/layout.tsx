import Link from "next/link";
import type { ReactNode } from "react";

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
