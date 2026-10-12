import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function TeacherHome() {
  const [subjects, setSubjects] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function load() {
    const [s, sess] = await Promise.all([api("/api/teacher/subjects"), api("/api/teacher/sessions")]);
    setSubjects(s.subjects);
    setSessions(sess.sessions);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function startSession(subjectId) {
    setError("");
    try {
      const data = await api("/api/teacher/sessions", {
        method: "POST",
        body: JSON.stringify({ subject_id: subjectId }),
      });
      navigate(`/teacher/session/${data.session.id}`);
    } catch (err) {
      if (err.data?.session?.id) navigate(`/teacher/session/${err.data.session.id}`);
      else setError(err.message);
    }
  }

  return (
    <div className="stack">
      {error ? <p className="error">{error}</p> : null}
      <article className="card">
        <div className="toolbar">
          <div>
            <h2>Teacher attendance portal</h2>
            <p className="muted">Open a session link to show its live QR and attendance roster.</p>
          </div>
          <Link className="btn light" to="/teacher/reports">Open teacher reports</Link>
        </div>
      </article>
      <article className="card">
        <h2>Assigned subjects</h2>
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>Class</th><th>Students</th><th></th></tr></thead>
          <tbody>
            {subjects.map((s) => (
              <tr key={s.id}>
                <td>{s.code}</td>
                <td>{s.name}</td>
                <td>{s.class_group?.name}</td>
                <td>{s.enrolled_count}</td>
                <td><button className="btn teal" type="button" onClick={() => startSession(s.id)}>Start QR session</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
      <article className="card">
        <h2>Recent sessions</h2>
        <table>
          <thead><tr><th>Subject</th><th>Started</th><th>Present</th><th>QR + face</th><th>Manual</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>{s.subject_code}</td>
                <td>{new Date(s.started_at).toLocaleString()}</td>
                <td>{s.present_count}</td>
                <td>{s.attendance_by_method?.qr_face ?? 0}</td>
                <td>{s.attendance_by_method?.manual ?? 0}</td>
                <td><span className={`badge ${s.is_open ? "ok" : "warn"}`}>{s.is_open ? "open" : "closed"}</span></td>
                <td><Link className="btn light" to={`/teacher/session/${s.id}`}>Open session</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </div>
  );
}
