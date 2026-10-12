import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function AdminHome() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/admin/stats")
      .then(setStats)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p>Loading dashboard…</p>;

  const cards = [
    ["Students", stats.students],
    ["Teachers", stats.teachers],
    ["Subjects", stats.subjects],
    ["Classes", stats.classes],
    ["Active users", stats.active_users],
  ];

  return (
    <div className="stack">
      <div className="grid stats">
        {cards.map(([label, value]) => (
          <article className="card" key={label}>
            <p className="muted">{label}</p>
            <p className="stat-value">{value}</p>
          </article>
        ))}
      </div>
      <article className="card">
        <h2>How attendance works</h2>
        <ol>
          <li>Admin creates teachers, students, subjects, and enrollments.</li>
          <li>Students enroll a face photo once from their dashboard.</li>
          <li>Teacher opens a live session. The QR code rotates every few seconds.</li>
          <li>Student scans the QR, follows a randomized head-turn prompt, and matches both camera frames to their enrolled face.</li>
        </ol>
      </article>
    </div>
  );
}
