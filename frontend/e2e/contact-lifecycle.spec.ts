import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("contact lifecycle features", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("adding a contact from a company page pre-fills and hides the company picker", async ({ page }) => {
    const companyName = `E2E QuickAdd Co ${Date.now()}`;
    const lastName = `E2E-QuickAdd-${Date.now()}`;

    await page.goto("/companies");
    await page.getByRole("button", { name: "Add company" }).click();
    await page.getByLabel("Name").fill(companyName);
    await page.getByRole("dialog").getByRole("button", { name: "Add company" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();

    await page.getByText(companyName).first().click();
    await expect(page).toHaveURL(/\/companies\/[0-9a-f-]+/);

    await page.getByRole("button", { name: "Add contact here" }).click();
    await expect(page.getByText(`Add contact at ${companyName}`)).toBeVisible();
    // The company picker is hidden entirely in this mode - the company is
    // implied by context, not something to re-search for.
    await expect(page.getByPlaceholder("Search companies…")).toHaveCount(0);

    await page.getByLabel("First name").fill("Quick");
    await page.getByLabel("Last name").fill(lastName);
    await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
    await page.waitForURL(/\/contacts\/[0-9a-f-]+/, { timeout: 10000 });

    // The new contact is linked to the company with no extra step.
    await expect(page.getByText(companyName).first()).toBeVisible();
  });

  test("marking a contact as departed moves their notes to the chosen successor", async ({ page }) => {
    const lastFrom = `E2E-Departed-${Date.now()}`;
    const lastTo = `E2E-Successor-${Date.now()}`;
    const ids: string[] = [];

    for (const lastName of [lastFrom, lastTo]) {
      await page.goto("/contacts");
      await page.getByRole("button", { name: "Add contact" }).click();
      await page.getByLabel("First name").fill("R");
      await page.getByLabel("Last name").fill(lastName);
      await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
      await page.waitForURL(/\/contacts\/[0-9a-f-]+/, { timeout: 10000 });
      ids.push(page.url().split("/contacts/")[1].split("?")[0]);
    }

    await page.goto(`/contacts/${ids[0]}`);
    await page.getByRole("button", { name: "Mark as departed" }).click();
    await page.getByPlaceholder("Search for who replaced them…").click();
    await page.getByPlaceholder("Search for who replaced them…").fill(lastTo.slice(0, 12));
    await expect(page.getByText(`R ${lastTo}`)).toBeVisible({ timeout: 5000 });
    await page.getByText(`R ${lastTo}`).click();
    await page.getByRole("button", { name: "Move notes and history" }).click();

    // Navigates straight to the successor's record.
    await page.waitForURL(`**/contacts/${ids[1]}`, { timeout: 10000 });

    // The departed contact's own record now carries a handover note
    // explaining where its history went.
    await page.goto(`/contacts/${ids[0]}`);
    await expect(page.getByText(`Notes and history moved to R ${lastTo}`)).toBeVisible();
  });
});
