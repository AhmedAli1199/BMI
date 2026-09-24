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

  test("clearing a contact's first and last name updates the page, survives reload, and shows in history", async ({ page }) => {
    // Regression for three compounding bugs found together: (1)
    // cleanPayload dropped every empty-string field before a PATCH ever
    // reached the backend, so "clear this field out" silently did
    // nothing; (2) once fixed to send "", the backend's typed birthdate
    // field rejected it outright (only null parses as "no date"),
    // 422-ing the *entire* save including the name fields; (3) that 422
    // (and any other backend error) was being silently swallowed by the
    // dev-fallback path and replaced with fake canned data, so the save
    // looked successful even though nothing was actually persisted.
    const lastName = `E2E-ClearName-${Date.now()}`;

    await page.goto("/contacts");
    await page.getByRole("button", { name: "Add contact" }).click();
    await page.getByLabel("First name").fill("Temp");
    await page.getByLabel("Last name").fill(lastName);
    await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
    await page.waitForURL(/\/contacts\/[0-9a-f-]+/, { timeout: 10000 });
    await expect(page.getByText(`Temp ${lastName}`).first()).toBeVisible();

    await page.getByRole("button", { name: "Edit Record" }).click();
    const nameInputs = page.locator("div.grid.grid-cols-2 input");
    await nameInputs.nth(0).fill("");
    await nameInputs.nth(1).fill("");
    await page.getByRole("button", { name: "Save Changes" }).click();

    await expect(page.getByText("Contact record updated")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("(no name)").first()).toBeVisible({ timeout: 10000 });

    await page.reload();
    await expect(page.getByText("(no name)").first()).toBeVisible();

    await page.getByText("History of changes").click();
    await expect(page.getByText("First name", { exact: true })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("Last name", { exact: true })).toBeVisible();
  });
});
