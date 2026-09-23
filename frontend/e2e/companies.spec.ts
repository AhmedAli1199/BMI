import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("companies", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("create a company and find it in the list", async ({ page }) => {
    const uniqueName = `E2E Company ${Date.now()}`;

    await page.goto("/companies");
    await page.getByRole("button", { name: "Add company" }).click();
    await page.getByLabel("Name").fill(uniqueName);
    await page.getByRole("dialog").getByRole("button", { name: "Add company" }).click();

    await expect(page.getByRole("dialog")).toBeHidden();
    await expect(page.getByText(uniqueName).first()).toBeVisible();
  });

  test("linking a contact to a company via the EntityPicker shows it on the contact", async ({ page }) => {
    const companyName = `E2E Picker Co ${Date.now()}`;
    const lastName = `E2E-Link-${Date.now()}`;

    await page.goto("/companies");
    await page.getByRole("button", { name: "Add company" }).click();
    await page.getByLabel("Name").fill(companyName);
    await page.getByRole("dialog").getByRole("button", { name: "Add company" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();

    await page.goto("/contacts");
    await page.getByRole("button", { name: "Add contact" }).click();
    await page.getByLabel("First name").fill("Playwright");
    await page.getByLabel("Last name").fill(lastName);
    await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();

    await page.getByText(`Playwright ${lastName}`).first().click();
    await expect(page).toHaveURL(/\/contacts\/[0-9a-f-]+/);

    await page.getByRole("button", { name: "Edit Record" }).click();
    await page.getByPlaceholder("Search companies…").click();
    await page.getByPlaceholder("Search companies…").fill(companyName.slice(0, 12));
    await expect(page.getByText(companyName)).toBeVisible({ timeout: 5000 });
    await page.getByText(companyName).click();
    await page.getByRole("button", { name: "Save Changes" }).click();

    await expect(page.getByText(companyName).first()).toBeVisible({ timeout: 10000 });
  });
});
