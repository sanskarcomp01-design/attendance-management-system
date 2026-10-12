import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";

export default function LiveSession() {
  const { id } = useParams();
  const [qr, setQr] = useState(null);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  async function refreshDetail() {
    const data = await api(`/api/teacher/sessions/${id}`);
    setDetail(data);
  }

  async function refreshQr() {
    if (detail && !detail.session.is_open) return;
    const data = await api(`/api/teacher/sessions/${id}/qr`);
    setQr(data);
  }

  useEffect(() => {
    refreshDetail().catch((err) => setError(err.message));
  }, [id]);

  useEffect(() => {
    if (!detail?.session?.is_open) return undefined;
    refreshQr().catch((err) => setError(err.message));
    const timer = setInterval(() => {
      refreshQr().catch((err) => setError(err.message));
      refreshDetail().catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, [id, detail?.session?.is_open]);

  async function closeSession() {
    await api(`/api/teacher/sessions/${id}/close`, { method: "POST" });
    await refreshDetail();
  }

  async function manualMark(student, status) {
    const reason = window.prompt(
      status === "present"
        ? `Reason for marking ${student.full_name} present (camera/QR issue, late, etc.)`
        : `Reason for marking ${student.full_name} absent (correction)`,
    );
    if (!reason || reason.trim().length < 3) {
      setError("A short reason is required for manual attendance.");
      return;
    }
    setError("");
    setBusyId(student.student_id);
    try {
      await api(`/api/teacher/sessions/${id}/mark`, {
        method: "POST",
        body: JSON.stringify({ student_id: student.student_id, status, reason: reason.trim() }),
      });
      await refreshDetail();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  if (!detail) return <p>Loading session…</p>;

  return (
    <div className="qr-wrap">
      <article className="card qr-box">
        <h2>Live QR</h2>
        {error ? <p className="error">{error}</p> : null}
        {detail.session.is_open && qr ? (
          <>
            <img src={`data:image/png;base64,${qr.image_base64}`} alt="Attendance QR code" />
            <p className="muted">Rotates about every {qr.ttl_seconds} seconds. Students must also pass face verification.</p>
            <button className="btn danger full" type="button" onClick={closeSession}>Close session</button>
          </>
        ) : (
          <p>This session is closed. The QR code is no longer valid.</p>
        )}
      </article>
      <article className="card">
        <div className="toolbar">
          <div>
            <h2>{detail.session.subject_code} roster</h2>
            <p className="muted">QR + face: {detail.session.attendance_by_method?.qr_face ?? 0} · Manual: {detail.session.attendance_by_method?.manual ?? 0}</p>
          </div>
          <Link className="btn light" to="/teacher">Teacher dashboard</Link>
        </div>
        <p className="muted">Present: {detail.session.present_count}</p>
        <p className="muted">If a phone or camera fails, mark the student here. Every change is stored in the audit log with your reason.</p>
        <table>
          <thead><tr><th>Roll</th><th>Name</th><th>Status</th><th>Method</th><th></th></tr></thead>
          <tbody>
            {detail.roster.map((row) => (
              <tr key={row.student_id}>
                <td>{row.roll_number}</td>
                <td>{row.full_name}</td>
                <td><span className={`badge ${row.status === "present" ? "ok" : "warn"}`}>{row.status}</span></td>
                <td>{row.method === "qr_face" ? "QR + face" : row.method === "manual" ? "Manual" : "—"}{row.note ? ` · ${row.note}` : ""}</td>
                <td className="row-actions">
                  <button className="btn teal" type="button" disabled={busyId === row.student_id} onClick={() => manualMark(row, "present")}>Present</button>
                  <button className="btn light" type="button" disabled={busyId === row.student_id} onClick={() => manualMark(row, "absent")}>Absent</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </div>
  );
}
