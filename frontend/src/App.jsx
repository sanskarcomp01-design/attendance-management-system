import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import AdminHome from "./pages/AdminHome.jsx";
import UsersPage from "./pages/UsersPage.jsx";
import SubjectsPage from "./pages/SubjectsPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import AuditPage from "./pages/AuditPage.jsx";
import TeacherHome from "./pages/TeacherHome.jsx";
import LiveSession from "./pages/LiveSession.jsx";
import StudentHome from "./pages/StudentHome.jsx";
import ScanPage from "./pages/ScanPage.jsx";
import FaceEnroll from "./pages/FaceEnroll.jsx";
import StudentProfile from "./pages/StudentProfile.jsx";

function Guard({ roles, children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="boot">Loading campus portal…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <div className="boot">Loading campus portal…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "admin") return <Navigate to="/admin" replace />;
  if (user.role === "teacher") return <Navigate to="/teacher" replace />;
  return <Navigate to="/student" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <Guard>
            <Layout />
          </Guard>
        }
      >
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/admin" element={<Guard roles={["admin"]}><AdminHome /></Guard>} />
        <Route path="/admin/users" element={<Guard roles={["admin"]}><UsersPage /></Guard>} />
        <Route path="/admin/subjects" element={<Guard roles={["admin"]}><SubjectsPage /></Guard>} />
        <Route path="/admin/reports" element={<Guard roles={["admin"]}><ReportsPage /></Guard>} />
        <Route path="/admin/audit" element={<Guard roles={["admin"]}><AuditPage /></Guard>} />
        <Route path="/teacher" element={<Guard roles={["teacher"]}><TeacherHome /></Guard>} />
        <Route path="/teacher/session/:id" element={<Guard roles={["teacher"]}><LiveSession /></Guard>} />
        <Route path="/teacher/reports" element={<Guard roles={["teacher"]}><ReportsPage teacherMode /></Guard>} />
        <Route path="/student" element={<Guard roles={["student"]}><StudentHome /></Guard>} />
        <Route path="/student/scan" element={<Guard roles={["student"]}><ScanPage /></Guard>} />
        <Route path="/student/face" element={<Guard roles={["student"]}><FaceEnroll /></Guard>} />
        <Route path="/student/profile" element={<Guard roles={["student"]}><StudentProfile /></Guard>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
