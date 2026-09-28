import { test, expect } from "@playwright/test";
import { login } from "./helpers";

/** Lookup, selection -> group, export, duplicate, reminders and the mail
 * merge wizard's document outputs (email sending needs a real Outlook
 * connection, so it's covered by the backend tests instead). */
test.describe("CRM tools", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  async function addContact(page: import("@playwright/test").Page, last: string) {
    await page.goto("/contacts");
    await page.getByRole("button", { name: "Add contact" }).click();
    await page.getByLabel("First name").fill("Lookup");
    await page.getByLabel("Last name").fill(last);
    await page.getByRole("dialog").getByRole("button", { name: "Add contact" }).click();
    await expect(page.getByRole("dialog")).toBeHidden();
  }

  test("lookup, sort, select into a new group and export", async ({ page }) => {
    const stamp = Date.now();
    await addContact(page, `Zed-${stamp}`);
    await addContact(page, `Abe-${stamp}`);

    await page.goto(`/contacts?q=${stamp}`);
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(2);
    await expect(rows.first()).toContainText(`Abe-${stamp}`);

    // Sort by name descending via the column header.
    await page.getByRole("link", { name: /Contact & Title/ }).click();
    await expect(page).toHaveURL(/desc=1/);
    await expect(rows.first()).toContainText(`Zed-${stamp}`);

    // Tick both -> new group from the selection.
    await page.getByLabel("Select every contact on this page").check();
    await expect(page.getByText("2 contacts selected")).toBeVisible();
    await page.getByRole("button", { name: "New group" }).click();
    await page.getByLabel("Group name").fill(`E2E Selection ${stamp}`);
    await page.getByRole("dialog").getByRole("button", { name: "Create group" }).click();
    await expect(page.getByText(/Created “E2E Selection/)).toBeVisible();

    // Export the lookup.
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export" }).first().click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  });

  test("duplicate a contact and set a reminder", async ({ page }) => {
    const stamp = Date.now();
    await addContact(page, `Dup-${stamp}`);
    await page.getByText(`Lookup Dup-${stamp}`).first().click();
    await expect(page).toHaveURL(/\/contacts\/[0-9a-f-]+/);

    await page.getByRole("button", { name: "Remind me" }).click();
    await page.getByRole("radio", { name: "Tomorrow" }).click();
    await page.getByLabel("What about? (optional)").fill("E2E follow-up");
    await page.getByRole("button", { name: "Set reminder" }).click();
    await expect(page.getByText(/Reminder set for/)).toBeVisible();

    await page.getByRole("button", { name: "Duplicate" }).click();
    await page.getByLabel("First name").fill("Copy");
    await page.getByLabel("Last name").fill(`Dup-${stamp}`);
    await page.getByRole("button", { name: "Create contact" }).click();
    await expect(page.getByText("Contact created from a copy")).toBeVisible();
    await expect(page.getByText(`Copy Dup-${stamp}`).first()).toBeVisible();

    await page.goto("/reminders");
    await expect(page.getByText("E2E follow-up").first()).toBeVisible();
  });

  test("mail merge: letters and merge data download", async ({ page }) => {
    const stamp = Date.now();
    await addContact(page, `Merge-${stamp}`);
    await page.getByText(`Lookup Merge-${stamp}`).first().click();
    await page.getByRole("button", { name: "Write" }).click();
    await expect(page).toHaveURL(/\/mail-merge\?contact=/);

    await page.getByRole("radio", { name: /Letters \(Word\)/ }).click();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.getByText("1 included")).toBeVisible();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.getByLabel("Letter").fill("Dear {{first_name}},\n\nHello from the test.");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    const [letters] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: /Create 1 letters/ }).click(),
    ]);
    expect(letters.suggestedFilename()).toBe("letters.docx");

    // Back to step 1 -> merge data as CSV.
    await page.getByRole("button", { name: /Output/ }).click();
    await page.getByRole("radio", { name: /Merge data/ }).click();
    await page.getByRole("button", { name: /Options/ }).click();
    await page.getByLabel(/CSV/).check();
    const [data] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Download merge data" }).click(),
    ]);
    expect(data.suggestedFilename()).toBe("merge-data.csv");
  });
});
