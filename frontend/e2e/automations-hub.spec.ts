import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("automations hub", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("overview shows the workstreams table and the New for review / Recently resolved feeds", async ({ page }) => {
    await page.goto("/automations");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { name: "New for review" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Recently resolved" })).toBeVisible();
    const main = page.locator("main");
    for (const name of ["Sales & Follow-ups", "Lead & Contact Capture", "Business Cards & Photos", "CRM Data Hygiene"]) {
      await expect(main.getByRole("link", { name: new RegExp(name) }).first()).toBeVisible();
    }
  });

  test("sidebar nests every workstream under a collapsible Automations Hub", async ({ page }) => {
    await page.goto("/contacts");
    await page.waitForLoadState("networkidle");
    const sidebar = page.locator("[data-sidebar='sidebar']").first();
    const trigger = sidebar.getByRole("button", { name: /Automations Hub/ });
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
    await trigger.click();
    await expect(trigger).toHaveAttribute("aria-expanded", "true");

    await sidebar.getByRole("link", { name: /CRM Data Hygiene/ }).click();
    await expect(page).toHaveURL(/\/automations\/hygiene$/);
    await expect(page.getByRole("heading", { level: 1, name: "CRM Data Hygiene" })).toBeVisible();
    // Opening a Hub page keeps the section expanded.
    await expect(trigger).toHaveAttribute("aria-expanded", "true");
  });

  test("a workstream page has KPIs, a range switch, and expandable automation rows", async ({ page }) => {
    await page.goto("/automations/sales");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Pending now")).toBeVisible();
    await expect(page.getByText("Resolved by your team")).toBeVisible();

    await page.getByRole("link", { name: "30 days" }).click();
    await expect(page).toHaveURL(/range=30d/);

    // The label flips Show -> Hide, so match on the stable part.
    const expand = page.getByRole("button", { name: /details for Overdue Follow-ups/ });
    await expand.click();
    await expect(expand).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByText("What your team decided", { exact: false }).first()).toBeVisible();
    await expect(page.getByText("Scanner health", { exact: true })).toBeVisible();
  });

  test("legacy ?tab= links redirect to the workstream's own page", async ({ page }) => {
    await page.goto("/automations?tab=capture");
    await expect(page).toHaveURL(/\/automations\/capture$/);
  });

  test("unknown workstreams show the not-found page", async ({ page }) => {
    // The Hub's loading.tsx starts streaming before notFound() runs, so
    // the status is already 200 - assert on what the user sees instead.
    await page.goto("/automations/not-a-workstream");
    await expect(page.getByText("This page could not be found.")).toBeVisible();
  });

  test("scanners page lists every scheduled scanner with its run history", async ({ page }) => {
    await page.goto("/automations/engine");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("heading", { level: 1, name: "Scanners & Settings" })).toBeVisible();
    await expect(page.getByText(/scanners switched on/)).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Last 10 runs" })).toBeVisible();
  });

  test("the retired brain route no longer exists", async ({ page }) => {
    const resp = await page.goto("/brain");
    expect(resp?.status()).toBe(404);
    await expect(page.getByText("Command Center")).not.toBeVisible();
  });
});
