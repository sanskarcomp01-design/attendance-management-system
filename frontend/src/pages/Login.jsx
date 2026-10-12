import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <section className="login-hero">
        <p className="eyebrow" style={{ color: "#9ee7dc" }}>Community Engagement Project · SE IT</p>
        <h1>Secure attendance with QR + face verification</h1>
        <p>
          Built for S. B. Patil College of Engineering, Vangali, Indapur under Savitribai Phule Pune University.
          Time-limited QR codes and AI face matching reduce proxy attendance.
        </p>
      </section>
      <form className="login-card" onSubmit={onSubmit}>
        <h2>Campus login</h2>
        <p className="muted">Use the account credentials provided by your administrator.</p>
        {error ? <p className="error">{error}</p> : null}
        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="btn full" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
