import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function StudentHome() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/student/attendance")
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="stack">
      {error ? <p className="error">{error}</p> : null}
      {!user.has_face_enrolled ? (
        <article className="card">
          <h2>Face enrollment required</h2>
          <p>Before you can mark attendance, save one clear selfie of your face.</p>
          <Link className="btn teal" to="/student/face">Enroll my face</Link>
        </article>
      ) : (
        <article className="card">
          <h2>Ready to mark attendance</h2>
          <p>Ask your teacher to display the live QR, then scan it and capture a selfie.</p>
          <Link className="btn teal" to="/student/scan">Open scanner</Link>
        </article>
      )}
      <article className="card overall-attendance">
        <div>
          <p className="muted">Overall attendance</p>
          <p className="stat-value">{data?.overall?.percent ?? 0}%</p>
        </div>
        <p className="muted">
          {data?.overall?.present ?? 0} present out of {data?.overall?.total_sessions ?? 0} sessions across all enrolled subjects
        </p>
      </article>
      <article className="card">
        <h2>Subject summary</h2>
        <table>
          <thead><tr><th>Code</th><th>Subject</th><th>Present</th><th>Sessions</th><th>%</th></tr></thead>
          <tbody>
            {(data?.summary || []).map((row) => (
              <tr key={row.subject_id}>
                <td>{row.subject_code}</td>
                <td>{row.subject_name}</td>
                <td>{row.present}</td>
                <td>{row.total_sessions}</td>
                <td>{row.percent}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </div>
  );
}
