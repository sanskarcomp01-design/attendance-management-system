import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function StudentProfile() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function changePassword(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation do not match.");
      return;
    }

    setBusy(true);
    try {
      const data = await api("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setMessage(data.message);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <article className="card">
        <h2>Student profile</h2>
        <dl className="profile-list">
          <div><dt>Full name</dt><dd>{user.full_name}</dd></div>
          <div><dt>Email</dt><dd>{user.email}</dd></div>
          <div><dt>Roll number</dt><dd>{user.roll_number || "Not provided"}</dd></div>
          <div><dt>Face enrollment</dt><dd>{user.has_face_enrolled ? "Enrolled" : "Not enrolled"}</dd></div>
        </dl>
      </article>
      <article className="card">
        <h2>Change password</h2>
        <p className="muted">Enter your current password to set a new password of at least 8 characters.</p>
        {error ? <p className="error" role="alert">{error}</p> : null}
        {message ? <p className="success" role="status">{message}</p> : null}
        <form className="form-grid" onSubmit={changePassword}>
          <label>
            Current password
            <input
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              required
            />
          </label>
          <label>
            New password
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              required
            />
          </label>
          <label>
            Confirm new password
            <input
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
          </label>
          <button className="btn teal" type="submit" disabled={busy}>
            {busy ? "Updating…" : "Change password"}
          </button>
        </form>
      </article>
    </div>
  );
}
