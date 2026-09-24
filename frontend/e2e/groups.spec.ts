import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("groups", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("bulk-removing members updates the list without a page reload or losing scroll", async ({ page }) => {
    const groupName = `E2E Bulk Remove ${Date.now()}`;
    const lastNameA = `E2E-Bulk-A-${Date.now()}`;
    const lastNameB = `E2E-Bulk-B-${Date.now()}`;

    // Create the group.
    await page.goto("/groups");
    await page.getByRole("button", { name: "New group" }).click();
    await page.getByLabel("Name").fill(groupName);
    await page.getByRole("dialog").getByRole("button", { name: "Create group" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();

    // Create two contacts and add each to the group via the contact page's
    // group picker (same EntityPicker flow already covered in contacts.spec.ts).
    for (const lastName of [lastNameA, lastNameB]) {
      await page.goto("/contacts");
      await page.getByRole("button", { name: "Add contact" }).click();
      await page.getByLabel("First name").fill("Playwright");
      await page.getByLabel("Last name").fill(lastName);
      await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
      await expect(page.getByRole("dialog")).toBeHidden();

      await page.getByText(`Playwright ${lastName}`).first().click();
      await expect(page).toHaveURL(/\/contacts\/[0-9a-f-]+/);
      await page.getByRole("tab", { name: "Groups (0)" }).click();
      await page.getByRole("button", { name: "Add to group" }).click();
      await page.getByPlaceholder("Search groups…").click();
      await page.getByPlaceholder("Search groups…").fill(groupName.slice(0, 12));
      await expect(page.getByText(groupName)).toBeVisible({ timeout: 5000 });
      await page.getByText(groupName).click();
    }

    // Now bulk-remove both from the group's own page.
    await page.goto("/groups");
    await page.getByText(groupName).first().click();
    await expect(page).toHaveURL(/\/groups\/[0-9a-f-]+/);
    await expect(page.getByText("Members (2)")).toBeVisible();

    const checkboxes = page.locator('tbody input[type="checkbox"]');
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();
    await expect(page.getByText("2 selected", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: /Remove 2 selected/ }).click();

    await expect(page.getByText("Members (0)")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("tbody tr")).toHaveCount(0);
  });
});
