import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth.jsx";

const NAV = {
  admin: [
    { to: "/admin", label: "Dashboard" },
    { to: "/admin/users", label: "Users" },
    { to: "/admin/subjects", label: "Classes & subjects" },
    { to: "/admin/reports", label: "Reports" },
    { to: "/admin/audit", label: "Audit log" },
  ],
  teacher: [
    { to: "/teacher", label: "My subjects" },
    { to: "/teacher/reports", label: "Reports" },
  ],
  student: [
    { to: "/student", label: "My attendance" },
    { to: "/student/face", label: "Enroll face" },
    { to: "/student/scan", label: "Scan QR" },
    { to: "/student/profile", label: "Profile & password" },
  ],
};

export default function Layout() {
  const { user, logout } = useAuth();
  const links = NAV[user.role] || [];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>AMS</strong>
          <span>SBPCOE · SPPU</span>
        </div>
        <nav>
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to.split("/").length <= 2}>
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-user">
          <p>{user.full_name}</p>
          <small>{user.role}</small>
          <button type="button" className="btn ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">S. B. Patil College of Engineering, Indapur</p>
            <h1>AI-Powered Attendance Management System</h1>
          </div>
          <span className="year-chip">AY 2026–2027</span>
        </header>
        <Outlet />
      </main>
    </div>
  );
}
