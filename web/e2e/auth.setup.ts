import { expect, test as setup } from "@playwright/test";

const PASSPHRASE = process.env.E2E_PASSPHRASE ?? "e2e-passphrase";
export const STORAGE_STATE = "test-results/.auth/learner.json";

setup("sign in", async ({ page }) => {
  await page.goto("/");
  const firstTime = page.getByRole("button", { name: "Set passphrase" });
  await expect(firstTime.or(page.getByRole("button", { name: "Sign in" }))).toBeVisible();
  await page.getByLabel("Passphrase").fill(PASSPHRASE);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: /Bonjour/ })).toBeVisible();
  await page.context().storageState({ path: STORAGE_STATE });
});
