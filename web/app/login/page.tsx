import { APP_NAME } from "@/lib/constants";

export default function LoginPage() {
  return (
    <section className="hero">
      <p className="section-label">Administrator access</p>
      <h1>Sign in</h1>
      <p>{APP_NAME} requires an administrator password before jobs can be managed.</p>
      <form method="post" action="/api/admin/login" className="login-form">
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        <button type="submit">Sign in</button>
      </form>
    </section>
  );
}
