import { useEffect, useState } from "react";
import { api } from "../api.js";

const newClass = {
  name: "SE-IT-B",
  year: "SE",
  division: "B",
  department: "Information Technology",
};

const newSubject = {
  code: "",
  name: "",
  class_group_id: "",
  teacher_id: "",
  is_active: "true",
};

export default function SubjectsPage() {
  const [classes, setClasses] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [students, setStudents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [enrollments, setEnrollments] = useState([]);
  const [classForm, setClassForm] = useState(newClass);
  const [subjectForm, setSubjectForm] = useState(newSubject);
  const [editingClassId, setEditingClassId] = useState(null);
  const [editingSubjectId, setEditingSubjectId] = useState(null);
  const [studentId, setStudentId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const [classData, subjectData, teacherData, studentData] = await Promise.all([
      api("/api/admin/classes"),
      api("/api/admin/subjects"),
      api("/api/admin/users?role=teacher"),
      api("/api/admin/users?role=student"),
    ]);
    setClasses(classData.classes);
    setSubjects(subjectData.subjects);
    setTeachers(teacherData.users);
    setStudents(studentData.users);
    if (classData.classes[0] && !subjectForm.class_group_id) {
      setSubjectForm((prev) => ({ ...prev, class_group_id: String(classData.classes[0].id) }));
    }
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function saveClass(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const isEditing = Boolean(editingClassId);
      await api(
        isEditing ? `/api/admin/classes/${editingClassId}` : "/api/admin/classes",
        { method: isEditing ? "PATCH" : "POST", body: JSON.stringify(classForm) },
      );
      setClassForm(newClass);
      setEditingClassId(null);
      setMessage(isEditing ? "Class updated." : "Class created.");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  function editClass(group) {
    setEditingClassId(group.id);
    setClassForm({
      name: group.name,
      year: group.year,
      division: group.division,
      department: group.department,
    });
    setError("");
    setMessage("");
  }

  async function saveSubject(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    const payload = {
      ...subjectForm,
      class_group_id: Number(subjectForm.class_group_id),
      teacher_id: subjectForm.teacher_id ? Number(subjectForm.teacher_id) : null,
    };
    const isEditing = Boolean(editingSubjectId);
    if (isEditing) payload.is_active = subjectForm.is_active === "true";

    try {
      const response = await api(
        isEditing ? `/api/admin/subjects/${editingSubjectId}` : "/api/admin/subjects",
        { method: isEditing ? "PATCH" : "POST", body: JSON.stringify(payload) },
      );
      if (isEditing && selected?.id === response.subject.id) setSelected(response.subject);
      setSubjectForm((prev) => ({
        ...newSubject,
        class_group_id: prev.class_group_id,
      }));
      setEditingSubjectId(null);
      setMessage(isEditing ? "Subject updated." : "Subject created.");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  function editSubject(subject) {
    setEditingSubjectId(subject.id);
    setSubjectForm({
      code: subject.code,
      name: subject.name,
      class_group_id: String(subject.class_group_id),
      teacher_id: subject.teacher_id ? String(subject.teacher_id) : "",
      is_active: String(subject.is_active),
    });
    setError("");
    setMessage("");
  }

  async function openSubject(subject) {
    setError("");
    try {
      setSelected(subject);
      const data = await api(`/api/admin/subjects/${subject.id}/enrollments`);
      setEnrollments(data.enrollments);
    } catch (err) {
      setError(err.message);
    }
  }

  async function enroll(event) {
    event.preventDefault();
    if (!selected) return;
    setError("");
    try {
      await api(`/api/admin/subjects/${selected.id}/enroll`, {
        method: "POST",
        body: JSON.stringify({ student_id: Number(studentId) }),
      });
      setStudentId("");
      await openSubject(selected);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function unenroll(id) {
    if (!selected) return;
    setError("");
    try {
      await api(`/api/admin/subjects/${selected.id}/enroll/${id}`, { method: "DELETE" });
      await openSubject(selected);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="stack">
      {error ? <p className="error" role="alert">{error}</p> : null}
      {message ? <p className="success" role="status">{message}</p> : null}
      <article className="card">
        <h2>{editingClassId ? "Edit class" : "Create class"}</h2>
        <form className="form-grid" onSubmit={saveClass}>
          <input aria-label="Class name" value={classForm.name} onChange={(e) => setClassForm({ ...classForm, name: e.target.value })} placeholder="SE-IT-A" required />
          <input aria-label="Year" value={classForm.year} onChange={(e) => setClassForm({ ...classForm, year: e.target.value })} placeholder="SE" required />
          <input aria-label="Division" value={classForm.division} onChange={(e) => setClassForm({ ...classForm, division: e.target.value })} placeholder="A" required />
          <input aria-label="Department" value={classForm.department} onChange={(e) => setClassForm({ ...classForm, department: e.target.value })} placeholder="Department" required />
          <button className="btn teal" type="submit">{editingClassId ? "Update class" : "Add class"}</button>
          {editingClassId ? (
            <button className="btn light" type="button" onClick={() => { setEditingClassId(null); setClassForm(newClass); }}>Cancel</button>
          ) : null}
        </form>
      </article>
      <article className="card">
        <h2>Classes</h2>
        <table>
          <thead><tr><th>Name</th><th>Year</th><th>Division</th><th>Department</th><th></th></tr></thead>
          <tbody>
            {classes.map((group) => (
              <tr key={group.id}>
                <td>{group.name}</td><td>{group.year}</td><td>{group.division}</td><td>{group.department}</td>
                <td><button className="btn light" type="button" onClick={() => editClass(group)}>Edit</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
      <article className="card">
        <h2>{editingSubjectId ? "Edit subject" : "Create subject"}</h2>
        <form className="form-grid" onSubmit={saveSubject}>
          <input aria-label="Subject code" value={subjectForm.code} onChange={(e) => setSubjectForm({ ...subjectForm, code: e.target.value })} placeholder="Subject code" required />
          <input aria-label="Subject name" value={subjectForm.name} onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })} placeholder="Subject name" required />
          <select aria-label="Class" value={subjectForm.class_group_id} onChange={(e) => setSubjectForm({ ...subjectForm, class_group_id: e.target.value })} required>
            {classes.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
          </select>
          <select aria-label="Teacher" value={subjectForm.teacher_id} onChange={(e) => setSubjectForm({ ...subjectForm, teacher_id: e.target.value })}>
            <option value="">Assign teacher later</option>
            {teachers.map((teacher) => <option key={teacher.id} value={teacher.id}>{teacher.full_name}</option>)}
          </select>
          {editingSubjectId ? (
            <select aria-label="Subject status" value={subjectForm.is_active} onChange={(e) => setSubjectForm({ ...subjectForm, is_active: e.target.value })}>
              <option value="true">Active</option><option value="false">Inactive</option>
            </select>
          ) : null}
          <button className="btn" type="submit">{editingSubjectId ? "Update subject" : "Add subject"}</button>
          {editingSubjectId ? (
            <button className="btn light" type="button" onClick={() => { setEditingSubjectId(null); setSubjectForm(newSubject); }}>Cancel</button>
          ) : null}
        </form>
      </article>
      <article className="card">
        <h2>Subjects</h2>
        <table>
          <thead>
            <tr><th>Code</th><th>Name</th><th>Class</th><th>Teacher</th><th>Enrolled</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {subjects.map((subject) => (
              <tr key={subject.id}>
                <td>{subject.code}</td>
                <td>{subject.name}</td>
                <td>{subject.class_group?.name}</td>
                <td>{subject.teacher_name || "—"}</td>
                <td>{subject.enrolled_count}</td>
                <td>{subject.is_active ? "Active" : "Inactive"}</td>
                <td className="row-actions">
                  <button className="btn light" type="button" onClick={() => editSubject(subject)}>Edit</button>
                  <button className="btn light" type="button" onClick={() => openSubject(subject)}>Enrollments</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </article>
      {selected ? (
        <article className="card">
          <h2>Enrollments · {selected.code}</h2>
          <form className="form-grid" onSubmit={enroll}>
            <select aria-label="Student to enroll" value={studentId} onChange={(e) => setStudentId(e.target.value)} required>
              <option value="">Select student</option>
              {students.map((student) => (
                <option key={student.id} value={student.id}>{student.full_name} ({student.roll_number})</option>
              ))}
            </select>
            <button className="btn teal" type="submit">Assign student</button>
          </form>
          <table>
            <thead><tr><th>Student</th><th>Roll</th><th></th></tr></thead>
            <tbody>
              {enrollments.map((enrollment) => (
                <tr key={enrollment.id}>
                  <td>{enrollment.student_name}</td>
                  <td>{enrollment.roll_number}</td>
                  <td><button className="btn danger" type="button" onClick={() => unenroll(enrollment.student_id)}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ) : null}
    </div>
  );
}
