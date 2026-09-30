import { test, expect } from "@playwright/test";
import { E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD, login } from "./helpers";

test.describe("login", () => {
  test("wrong password shows an error and does not navigate away", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(E2E_ADMIN_EMAIL);
    await page.getByLabel(/password/i).fill("definitely-wrong");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/invalid email or password/i)).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("correct credentials sign in and land on the dashboard", async ({ page }) => {
    await login(page, E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD);
    await expect(page.getByRole("link", { name: "Contacts", exact: true })).toBeVisible();
  });
});
