import { defineConfig, devices } from "@playwright/test";

/** E2E golden-path coverage against a real running dev stack (Postgres +
 * FastAPI backend + this Next.js frontend) - not started by this config,
 * since it needs real seeded data (see e2e/README.md). Points at
 * PLAYWRIGHT_BASE_URL if set, else assumes `npm run dev -- -p 3000` is
 * already running locally. */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
        },
      },
    },
  ],
});
