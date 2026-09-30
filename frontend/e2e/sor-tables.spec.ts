import { test, expect } from "@playwright/test";
import { login } from "./helpers";

/** Every SOR table has the same filter sidebar, sortable headers and URL state. */
test.describe("SOR tables", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("bookings: filter, sort, chips and export follow the URL", async ({ page }) => {
    await page.goto("/sales/bookings");
    const sidebar = page.getByRole("complementary", { name: "Filter bookings" });
    await sidebar.getByRole("checkbox", { name: /Booked/ }).first().check();
    await expect(page).toHaveURL(/status=booked/);
    await expect(page.getByRole("button", { name: "Remove Status: Booked" })).toBeVisible();

    await page.getByRole("button", { name: /^Value/ }).click();
    await expect(page).toHaveURL(/sort=value&dir=desc/);
    const values = await page.locator("tbody tr td:nth-child(6)").allInnerTexts();
    const nums = values.slice(0, 5).map((v) => Number(v.replace(/[£,]/g, "")));
    expect(nums).toEqual([...nums].sort((a, b) => b - a));

    await page.getByRole("searchbox", { name: "Search bookings" }).fill("zzzz-nothing-matches");
    await expect(page.getByText("No bookings match these filters.")).toBeVisible();
    await page.getByRole("button", { name: "Clear search" }).click();
    await expect(page).not.toHaveURL(/q=/);

    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Export" }).click()]);
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  });

  test("editions, commissions and renewals filter in the browser", async ({ page }) => {
    await page.goto("/sales/editions");
    await page.getByRole("button", { name: "One list" }).click();
    await expect(page).toHaveURL(/group=none/);
    await page.getByRole("searchbox", { name: "Search editions" }).fill("zzzz");
    await expect(page.getByText("No editions match these filters")).toBeVisible();

    await page.goto("/sales/commissions");
    await expect(page.getByRole("complementary", { name: "Filter commission" })).toBeVisible();

    await page.goto("/sales/renewals");
    await expect(page.getByRole("complementary", { name: "Filter advertisers" })).toBeVisible();
  });
});
