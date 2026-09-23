import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("contacts", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("create a contact, find it in the list, and open its detail page", async ({ page }) => {
    const uniqueLastName = `E2E-${Date.now()}`;

    await page.goto("/contacts");
    await page.getByRole("button", { name: "Add contact" }).click();
    await page.getByLabel("First name").fill("Playwright");
    await page.getByLabel("Last name").fill(uniqueLastName);
    await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();

    // The dialog closes and the new contact is visible without a manual reload.
    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(page.getByText(`Playwright ${uniqueLastName}`).first()).toBeVisible();

    await page.getByText(`Playwright ${uniqueLastName}`).first().click();
    await expect(page).toHaveURL(/\/contacts\/[0-9a-f-]+/);
    await expect(page.getByRole("heading", { name: new RegExp(uniqueLastName) })).toBeVisible();
  });

  test("editing a contact's title persists after reload", async ({ page }) => {
    const uniqueLastName = `E2E-Edit-${Date.now()}`;

    await page.goto("/contacts");
    await page.getByRole("button", { name: "Add contact" }).click();
    await page.getByLabel("First name").fill("Playwright");
    await page.getByLabel("Last name").fill(uniqueLastName);
    await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();

    await page.getByText(`Playwright ${uniqueLastName}`).first().click();
    await expect(page).toHaveURL(/\/contacts\/[0-9a-f-]+/);

    await page.getByRole("button", { name: "Edit Record" }).click();
    // The Business Card fields (Title, Department, ...) are plain
    // label-span + Input pairs, not <label for>, so they're targeted by
    // the row's text rather than getByLabel.
    const titleRow = page.locator("div").filter({ hasText: /^Title:/ }).last();
    await titleRow.locator("input").fill("E2E Test Title");
    await page.getByRole("button", { name: "Save Changes" }).click();

    await expect(page.getByText("E2E Test Title").first()).toBeVisible({ timeout: 10000 });
    await page.reload();
    await expect(page.getByText("E2E Test Title").first()).toBeVisible({ timeout: 10000 });
  });
});
