import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("automations hub", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("shows the New for review / Recently resolved feed and tab toggles with pending bubbles", async ({ page }) => {
    // The Command Center page was retired - these two feeds are what
    // survived from it, folded into the Hub instead of a separate
    // destination.
    await page.goto("/automations");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("New for review")).toBeVisible();
    await expect(page.getByText("Recently resolved")).toBeVisible();

    // Every workstream toggle is a real button (not a thin underlined
    // label) with its own pending-count bubble.
    const salesTab = page.getByRole("tab", { name: /Sales Acceleration & Follow-ups/ });
    await expect(salesTab).toBeVisible();
    const engineTab = page.getByRole("tab", { name: /Scanners & Settings/ });
    await expect(engineTab).toBeVisible();
  });

  test("the retired brain route no longer exists", async ({ page }) => {
    const resp = await page.goto("/brain");
    expect(resp?.status()).toBe(404);
    await expect(page.getByText("Command Center")).not.toBeVisible();
  });
});
