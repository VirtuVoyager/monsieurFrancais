import { defineConfig, devices } from "@playwright/test";

// Expects the API (with a freshly seeded database) and the web app to be running: `make e2e`.
export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1,
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000", trace: "retain-on-failure" },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], storageState: "test-results/.auth/learner.json" },
      dependencies: ["setup"],
    },
  ],
});
