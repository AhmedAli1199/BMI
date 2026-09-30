import { test, expect } from "@playwright/test";
import { login } from "./helpers";

/** End-to-end regression for the Sept 23 demo /today crash (missing
 * Company import in morning_queue.py's _resolve_owner - see
 * backend/tests/test_morning_queue.py for the same regression at the
 * unit/API level). This confirms the fix holds through the real page,
 * not just the route. */
test.describe("today", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("loads without error for 'My list' and 'Everyone'", async ({ page }) => {
    const resp = await page.goto("/automations/today");
    expect(resp?.status()).toBe(200);
    await expect(page.getByText("This page hit a snag.")).toBeHidden();
    await expect(page.getByRole("heading", { name: /list for today/i })).toBeVisible();

    const everyone = page.getByRole("link", { name: "Everyone" });
    if (await everyone.isVisible().catch(() => false)) {
      await everyone.click();
      await expect(page.getByText("This page hit a snag.")).toBeHidden();
      await expect(page.getByRole("heading", { name: "Everyone's list for today" })).toBeVisible();
    }
  });
});
