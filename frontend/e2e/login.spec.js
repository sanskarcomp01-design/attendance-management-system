import { test, expect } from "@playwright/test";

test("login page shows college branding and form", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /secure attendance/i })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
});

test("protected pages send visitors to login", async ({ page }) => {
  await page.goto("/admin/users");
  await expect(page).toHaveURL(/login/);
  await expect(page.getByRole("heading", { name: /secure attendance/i })).toBeVisible();
});

test("wrong password shows an error when API is running", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("admin@sbpcoe.edu");
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.locator(".error")).toBeVisible({ timeout: 15000 });
});
