import { APP_NAME } from "@/lib/constants";

export default function HomePage() {
  return (
    <section className="hero">
      <p className="section-label">Local worker control plane</p>
      <h1>{APP_NAME}</h1>
      <p>
        Create translation jobs, lease them to authenticated local workers, and
        watch progress without running long-lived translation work on Vercel.
      </p>
    </section>
  );
}
