import { expect, test, type Page } from "@playwright/test";

const MODULE = "/modules/a1-01-se-presenter";

async function completeEveryLesson(page: Page) {
  await page.goto(`${MODULE}`);
  await page.getByRole("link", { name: /Pronoms sujets/ }).click();
  for (let i = 0; i < 7; i++) {
    await page.getByRole("button", { name: /Complete lesson|Next lesson|Back to module/ }).click();
    await page.waitForLoadState("networkidle");
  }
  await expect(page).toHaveURL(MODULE);
}

test("a grammar exercise gives immediate feedback", async ({ page }) => {
  await page.goto("/lessons/a1-01-se-presenter/grammaire");
  await page.getByLabel("Answer for question 1").fill("suis");
  await page.getByRole("button", { name: "Check" }).first().click();
  await expect(page.getByRole("status").filter({ hasText: "Correct" })).toBeVisible();

  await page.getByLabel("Answer for question 2").fill("sommes");
  await page.getByRole("button", { name: "Check" }).first().click();
  await expect(page.getByText("Answer: avons")).toBeVisible();
});

test("finishing a module unlocks the next one", async ({ page }) => {
  await page.goto("/path");
  await expect(page.getByText("locked")).toBeVisible();

  await completeEveryLesson(page);
  await page.getByRole("link", { name: "Take the check" }).click();
  await page.getByRole("button", { name: "Start the check" }).click();

  const answers: Record<string, string> = {
    "Tu ___ professeur ?": "es",
    "Ils ___ au Canada. (habiter)": "habitent",
    "Elle ___ Amina. (s'appeler)": "s'appelle",
  };
  for (const [prompt, text] of Object.entries(answers)) {
    const exercise = page.locator("div.rounded-xl", { hasText: prompt.replace("'", "’") });
    await exercise.getByRole("textbox").fill(text);
  }
  for (const option of ["a", "viens", "nationalité", "La", "À Québec"]) {
    await page.getByRole("radio", { name: option, exact: true }).click();
  }
  for (const word of ["Quel", "âge", "avez-vous ?"]) {
    await page.getByRole("button", { name: word, exact: true }).click();
  }
  await page.getByRole("button", { name: "Submit" }).click();

  await expect(page.getByText("Module covered")).toBeVisible();
  await page.goto("/path");
  await expect(page.getByText("covered", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /La famille/ })).toBeVisible();
});

test("completed vocabulary shows up in review and the library", async ({ page }) => {
  await page.goto("/review");
  await page.getByRole("button", { name: "Show answer" }).click();
  await page.getByRole("button", { name: "Good" }).click();

  await page.goto("/library");
  await page.getByPlaceholder("Search French or English").fill("city");
  await expect(page.getByText("ville", { exact: true })).toBeVisible();
});

test("a timed reading drill fills in the reading skill bar", async ({ page }) => {
  await page.goto("/progress");
  await expect(page.getByText("No timed evidence yet").first()).toBeVisible();

  await page.goto("/drills");
  await page.getByRole("button", { name: "Start" }).nth(1).click();
  for (let i = 0; i < 10; i++) {
    await page.getByRole("radio").first().click();
    const next = page.getByRole("button", { name: "Next question" });
    if (await next.isVisible()) await next.click();
  }
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText(/Estimated \d+\/699/)).toBeVisible();

  await page.goto("/progress");
  await expect(page.getByText(/est\. \d+\/699/)).toBeVisible();
});
