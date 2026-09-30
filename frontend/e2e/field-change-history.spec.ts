import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("field change history", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("editing a field shows up in the history panel with who and what changed", async ({ page }) => {
    const lastName = `E2E-Audit-${Date.now()}`;

    await page.goto("/contacts");
    await page.getByRole("button", { name: "Add contact" }).click();
    await page.getByLabel("First name").fill("Audit");
    await page.getByLabel("Last name").fill(lastName);
    await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
    await page.waitForURL(/\/contacts\/[0-9a-f-]+/, { timeout: 10000 });

    // Nothing recorded yet for a freshly-created contact.
    await page.getByText("History of changes").click();
    await expect(page.getByText("No field edits recorded yet.")).toBeVisible({ timeout: 5000 });
    await page.getByText("History of changes").click(); // collapse

    await page.getByRole("button", { name: "Edit Record" }).click();
    const titleRow = page.locator("div").filter({ hasText: /^Title:/ }).last();
    await titleRow.locator("input").fill("Head of Audit");
    await page.getByRole("button", { name: "Save Changes" }).click();
    await expect(page.getByText("Head of Audit").first()).toBeVisible({ timeout: 10000 });

    // Re-opening the (already-fetched-once) panel picks up the new edit,
    // not a stale cached empty list.
    await page.getByText("History of changes").click();
    await expect(page.getByText("Title", { exact: true })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/E2E Admin.*just now/)).toBeVisible();
  });
});
