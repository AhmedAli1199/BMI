import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("review queue", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("counts render and the page lists pending automation kinds", async ({ page }) => {
    await page.goto("/automations/review");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Overdue Follow-ups")).toBeVisible();
  });

  test("resolving a pending item removes it from the list without a reload", async ({ page }) => {
    await page.goto("/automations/review");
    await page.waitForLoadState("networkidle");

    // "Not a lead, ignore" (Inbound Lead Capture) is a plain no-op action
    // with no dependency on other seeded rows, unlike the AI-drafted
    // kinds (signal_trigger/personal_touchpoint_due), whose seeded demo
    // data references EmailSignal rows that may no longer exist - a
    // stable action to exercise the "resolve -> item disappears" UI
    // contract without depending on that other data's freshness.
    const ignoreButtons = page.getByRole("button", { name: "Not a lead, ignore" });
    const before = await ignoreButtons.count();
    test.skip(before === 0, "No pending 'Inbound Lead Capture' items left in the seeded dataset.");

    await ignoreButtons.first().click();

    await expect(async () => {
      expect(await ignoreButtons.count()).toBe(before - 1);
    }).toPass({ timeout: 10000 });
  });
});
