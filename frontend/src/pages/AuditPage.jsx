import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/reports/audit")
      .then((data) => setLogs(data.logs))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <article className="card">
      <h2>System activity</h2>
      {error ? <p className="error">{error}</p> : null}
      <table>
        <thead>
          <tr><th>Time</th><th>Actor</th><th>Action</th><th>Details</th><th>IP</th></tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{new Date(log.created_at).toLocaleString()}</td>
              <td>{log.actor_name}</td>
              <td>{log.action}</td>
              <td>{log.details}</td>
              <td>{log.ip_address}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </article>
  );
}
