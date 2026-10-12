import { useEffect, useState } from "react";
import { api } from "../api.js";

const empty = {
  full_name: "",
  email: "",
  password: "",
  role: "student",
  roll_number: "",
  employee_id: "",
  phone: "",
};

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(empty);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const data = await api("/api/admin/users");
    setUsers(data.users);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function saveUser(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      if (editingId) {
        const payload = {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone,
          roll_number: form.roll_number,
          employee_id: form.employee_id,
        };
        if (form.password) payload.password = form.password;
        await api(`/api/admin/users/${editingId}`, { method: "PATCH", body: JSON.stringify(payload) });
        setMessage("Account updated.");
        setEditingId(null);
        setForm(empty);
      } else {
        await api("/api/admin/users", { method: "POST", body: JSON.stringify(form) });
        setForm(empty);
        setMessage("Account created.");
      }
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  function startEdit(user) {
    setEditingId(user.id);
    setForm({
      full_name: user.full_name,
      email: user.email,
      password: "",
      role: user.role,
      roll_number: user.roll_number || "",
      employee_id: user.employee_id || "",
      phone: user.phone || "",
    });
    setMessage("");
    setError("");
  }

  async function deactivate(id) {
    setError("");
    try {
      await api(`/api/admin/users/${id}/deactivate`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function reactivate(user) {
    await api(`/api/admin/users/${user.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: true }),
    });
    await load();
  }

  return (
    <div className="stack">
      <article className="card">
        <h2>{editingId ? "Edit account" : "Create account"}</h2>
        {error ? <p className="error">{error}</p> : null}
        {message ? <p className="success">{message}</p> : null}
        <form className="form-grid" onSubmit={saveUser}>
          <input placeholder="Full name" value={form.full_name} onChange={(e) => setField("full_name", e.target.value)} required />
          <input type="email" placeholder="Email" value={form.email} onChange={(e) => setField("email", e.target.value)} required />
          <input type="password" placeholder={editingId ? "New password (optional)" : "Temp password (8+ chars)"} value={form.password} onChange={(e) => setField("password", e.target.value)} required={!editingId} />
          <select value={form.role} onChange={(e) => setField("role", e.target.value)} disabled={Boolean(editingId)}>
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
            <option value="admin">Admin</option>
          </select>
          <input placeholder="Roll number" value={form.roll_number} onChange={(e) => setField("roll_number", e.target.value)} />
          <input placeholder="Employee ID" value={form.employee_id} onChange={(e) => setField("employee_id", e.target.value)} />
          <input placeholder="Phone" value={form.phone} onChange={(e) => setField("phone", e.target.value)} />
          <button className="btn teal" type="submit">{editingId ? "Update user" : "Save user"}</button>
          {editingId ? (
            <button className="btn light" type="button" onClick={() => { setEditingId(null); setForm(empty); }}>Cancel</button>
          ) : null}
        </form>
      </article>
      <article className="card">
        <h2>Directory</h2>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>ID</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td>{user.role}</td>
                <td>{user.roll_number || user.employee_id || "—"}</td>
                <td>
                  <span className={`badge ${user.is_active ? "ok" : "warn"}`}>{user.is_active ? "active" : "inactive"}</span>
                </td>
                <td className="row-actions">
                  <button className="btn light" type="button" onClick={() => startEdit(user)}>Edit</button>
                  {user.is_active ? (
                    <button className="btn danger" type="button" onClick={() => deactivate(user.id)}>Deactivate</button>
                  ) : (
                    <button className="btn light" type="button" onClick={() => reactivate(user)}>Reactivate</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
    </div>
  );
}
