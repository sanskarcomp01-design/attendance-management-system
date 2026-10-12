import { test, expect } from "@playwright/test";

async function signInAs(page, role) {
  await page.addInitScript(() => localStorage.setItem("ams_token", "browser-test-token"));
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user: {
          id: 1,
          full_name: role === "teacher" ? "Test Teacher" : "Test Student",
          email: `${role}@test.edu`,
          role,
          roll_number: role === "student" ? "R1" : null,
          has_face_enrolled: true,
        },
      }),
    }),
  );
}

test("student dashboard displays weighted overall attendance", async ({ page }) => {
  await signInAs(page, "student");
  await page.route("**/api/student/attendance", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        summary: [],
        records: [],
        overall: { present: 2, total_sessions: 3, percent: 66.7 },
      }),
    }),
  );

  await page.goto("/student");
  await expect(page.getByText("Overall attendance")).toBeVisible();
  await expect(page.getByText("66.7%")).toBeVisible();
  await expect(page.getByText("2 present out of 3 sessions across all enrolled subjects")).toBeVisible();
});

test("teacher dashboard links to sessions and shows attendance methods", async ({ page }) => {
  await signInAs(page, "teacher");
  await page.route("**/api/teacher/subjects", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ subjects: [] }) }),
  );
  await page.route("**/api/teacher/sessions", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sessions: [{
          id: 3,
          subject_code: "214443",
          started_at: "2026-10-10T10:00:00Z",
          present_count: 2,
          attendance_by_method: { qr_face: 1, manual: 1 },
          is_open: false,
        }],
      }),
    }),
  );

  await page.goto("/teacher");
  await expect(page.getByRole("link", { name: "Open session" })).toHaveAttribute("href", "/teacher/session/3");
  const row = page.getByRole("row").filter({ hasText: "214443" });
  await expect(row.getByRole("cell").nth(3)).toHaveText("1");
  await expect(row.getByRole("cell").nth(4)).toHaveText("1");
});

test("teacher session view labels QR and manual attendance", async ({ page }) => {
  await signInAs(page, "teacher");
  await page.route("**/api/teacher/sessions/3", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session: {
          id: 3,
          subject_code: "214443",
          is_open: false,
          present_count: 2,
          attendance_by_method: { qr_face: 1, manual: 1 },
        },
        roster: [
          { student_id: 1, full_name: "Student One", roll_number: "R1", status: "present", method: "qr_face", note: null },
          { student_id: 2, full_name: "Student Two", roll_number: "R2", status: "present", method: "manual", note: "Camera failed" },
        ],
      }),
    }),
  );

  await page.goto("/teacher/session/3");
  await expect(page.getByText("QR + face: 1 · Manual: 1")).toBeVisible();
  await expect(page.getByRole("cell", { name: "QR + face" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "Manual · Camera failed" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Teacher dashboard" })).toHaveAttribute("href", "/teacher");
});
