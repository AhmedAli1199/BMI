import type { Page } from "@playwright/test";

export const E2E_ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || "e2e-admin@bmipublishing.co.uk";
export const E2E_ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || "E2eTestPass123!";

/** Signs in as the seeded e2e admin (see backend/scripts/seed_admin.py)
 * and waits for the dashboard to load - the shared entry point for every
 * spec that needs an authenticated session. */
export async function login(page: Page, email = E2E_ADMIN_EMAIL, password = E2E_ADMIN_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForURL("/");
}
