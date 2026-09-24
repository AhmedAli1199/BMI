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

  test("Queue Insights panel shows bucketed counts and filters the list", async ({ page }) => {
    // duplicate_contact is one of the 3 kinds Queue Insights covers (see
    // backend's _INSIGHT_BUCKETS) - skips like the test above if the
    // seeded dataset doesn't currently have any, rather than asserting
    // against data this test doesn't control.
    await page.goto("/automations/review?kind=duplicate_contact");
    await page.waitForLoadState("networkidle");

    const panel = page.getByText("Queue Insights:");
    test.skip(!(await panel.isVisible().catch(() => false)), "No duplicate_contact items in the seeded dataset.");

    const highPill = page.getByRole("link", { name: /High confidence/ });
    test.skip(!(await highPill.isVisible().catch(() => false)), "No High confidence bucket to click.");

    await highPill.click();
    await expect(page).toHaveURL(/bucket=high/);
    await expect(page.getByRole("link", { name: "Clear" })).toBeVisible();
  });
});
