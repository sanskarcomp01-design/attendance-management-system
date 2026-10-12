import { useEffect, useState } from "react";
import { api, downloadFile } from "../api.js";

export default function ReportsPage({ teacherMode = false }) {
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const path = teacherMode ? "/api/teacher/subjects" : "/api/admin/subjects";
    api(path)
      .then((data) => {
        setSubjects(data.subjects);
        if (data.subjects[0]) setSubjectId(String(data.subjects[0].id));
      })
      .catch((err) => setError(err.message));
  }, [teacherMode]);

  async function loadReport(event) {
    event.preventDefault();
    setError("");
    try {
      const data = await api(`/api/reports/subject/${subjectId}`);
      setReport(data);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="stack">
      <article className="card">
        <h2>{teacherMode ? "My subject report" : "Attendance report"}</h2>
        {error ? <p className="error">{error}</p> : null}
        <form className="form-grid" onSubmit={loadReport}>
          <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>{s.code} · {s.name}</option>
            ))}
          </select>
          <button className="btn" type="submit">Generate</button>
        </form>
      </article>
      {report ? (
        <article className="card">
          <div className="toolbar">
            <h3>{report.subject.code} · {report.sessions.length} sessions</h3>
            <div className="row-actions">
              <button
                className="btn teal"
                type="button"
                onClick={() =>
                  downloadFile(
                    `/api/reports/subject/${report.subject.id}/csv`,
                    `${report.subject.code}-attendance.csv`,
                  ).catch((err) => setError(err.message))
                }
              >
                Download CSV
              </button>
              <button className="btn light" type="button" onClick={() => window.print()}>Print / save PDF</button>
            </div>
          </div>
          <p className="muted">SPPU-style eligibility: {report.eligibility_percent}% or higher. Rows below the line are highlighted.</p>
          <table>
            <thead>
              <tr><th>Roll</th><th>Student</th><th>Present</th><th>Total</th><th>%</th><th>Eligible</th></tr>
            </thead>
            <tbody>
              {report.rows.map((row) => (
                <tr key={row.student_id} className={row.eligible ? "" : "row-risk"}>
                  <td>{row.roll_number}</td>
                  <td>{row.full_name}</td>
                  <td>{row.present}</td>
                  <td>{row.total_sessions}</td>
                  <td>{row.percent}%</td>
                  <td>
                    <span className={`badge ${row.eligible ? "ok" : "warn"}`}>
                      {row.eligible ? "yes" : "below 75%"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ) : null}
    </div>
  );
}
