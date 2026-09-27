import { test, expect } from "@playwright/test";
import { login } from "./helpers";

test.describe("sales orders", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("overview shows the year's key figures and booking pace", async ({ page }) => {
    await page.goto("/sales");
    await expect(page.getByRole("heading", { level: 1, name: "Sales Orders" })).toBeVisible();
    await expect(page.getByText(/^Booked in \d{4}$/)).toBeVisible();
    await expect(page.getByRole("heading", { name: /Booking pace/ })).toBeVisible();
    await expect(page.getByRole("link", { name: "Invoicing" }).first()).toBeVisible();
  });

  test("add, edit and delete a booking on an edition", async ({ page }) => {
    const client = `E2E Advertiser ${Date.now()}`;
    await page.goto("/sales/editions");
    await page.getByText("OnBoard Hospitality (OBH)").first().click();
    await page.getByRole("link", { name: /^OBH 10\d$/ }).first().click();
    await page.waitForURL(/\/sales\/editions\/[0-9a-f-]{36}$/);

    await page.getByRole("button", { name: "Add booking" }).click();
    await page.getByLabel("Client (as it should appear on the order)").fill(client);
    await page.getByLabel("Size / product").fill("FP");
    await page.getByLabel("Value (£)").fill("1234");
    await page.getByLabel("Credited to").selectOption({ label: "Sue Williams (SW)" });
    await page.getByRole("button", { name: "Add booking" }).last().click();
    await expect(page.getByText(`Booking added for ${client}`)).toBeVisible();

    const row = page.getByRole("row", { name: new RegExp(client) });
    await expect(row).toContainText("£1,234");
    await expect(row).toContainText("SW");

    await row.getByRole("button", { name: client }).click();
    await page.getByRole("radio", { name: "Cancelled" }).click();
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText("Booking saved")).toBeVisible();
    await expect(page.getByRole("row", { name: new RegExp(client) })).toContainText("Cancelled");

    await page.getByRole("row", { name: new RegExp(client) }).getByRole("button", { name: client }).click();
    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Delete" }).click();
    await expect(page.getByText("Booking deleted")).toBeVisible();
    await expect(page.getByRole("row", { name: new RegExp(client) })).toHaveCount(0);
  });

  test("renewals, invoicing and commissions pages load", async ({ page }) => {
    await page.goto("/sales/renewals");
    await expect(page.getByText("Retention so far")).toBeVisible();
    await page.goto("/sales/invoicing?view=uninvoiced");
    await expect(page.getByRole("heading", { level: 1, name: "Invoicing" })).toBeVisible();
    await page.goto("/sales/commissions");
    await expect(page.getByRole("heading", { level: 1, name: "Commissions" })).toBeVisible();
  });
});
