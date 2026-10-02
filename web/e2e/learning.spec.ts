import { expect, test, type Page } from "@playwright/test";

const MODULE = "/modules/a1-01-se-presenter";

async function completeEveryLesson(page: Page) {
  await page.goto(`${MODULE}`);
  await page.getByRole("link", { name: /Pronoms sujets/ }).click();
  await page.waitForURL(/\/lessons\//);
  while (!page.url().endsWith(MODULE)) {
    const current = page.url();
    await page.getByRole("button", { name: /Complete lesson|Next lesson|Back to module/ }).click();
    await page.waitForURL((url) => url.toString() !== current);
  }
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
  await page.getByPlaceholder(/Search words/).fill("vile");
  await expect(page.getByRole("link", { name: /ville/ }).first()).toBeVisible();
});

test("a timed reading drill fills in the reading skill bar", async ({ page }) => {
  await page.goto("/progress");
  await expect(page.getByText("No timed evidence yet").first()).toBeVisible();

  await page.goto("/drills");
  await page.getByRole("button", { name: "Start" }).nth(1).click();
  await page.getByRole("button", { name: "Begin" }).click();
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

test("a timed writing drill is graded on /20 with fixes", async ({ page }) => {
  await page.goto("/drills");
  await page.getByRole("button", { name: "Start" }).nth(2).click();
  await page.getByRole("button", { name: "Begin" }).click();
  await page
    .getByLabel("Your answer")
    .fill(
      "Salut Marc ! Je suis trente ans et je habite maintenant à Montréal. Mon appartement est " +
        "petit mais lumineux, et le quartier est calme. Il y a un parc, une boulangerie et le " +
        "métro. Viens me voir le week-end prochain, on pourra visiter la ville ensemble !",
    );
  await page.getByRole("button", { name: "Submit" }).click();

  await expect(page.getByText("TCF /20")).toBeVisible();
  await expect(page.getByText("Fix these first")).toBeVisible();
  await expect(page.getByText(/Estimated \d+\/20/)).toBeVisible();
});

test("the placement test sets both receptive skill bars", async ({ page }) => {
  await page.goto("/placement");
  await page.getByRole("button", { name: "Begin" }).click();
  for (let i = 0; i < 16; i++) {
    await page.getByRole("radio").first().click();
    const next = page.getByRole("button", { name: "Next question" });
    if (await next.isVisible()) await next.click();
  }
  await page.getByRole("button", { name: "Submit" }).click();

  await expect(page.getByText("You start at")).toBeVisible();
  await expect(page.getByText(/\/699 · /).first()).toBeVisible();
});

test("a speaking task gives preparation time, then releases the call on failure", async ({
  page,
}) => {
  await page.goto("/speak");
  await page.getByRole("radio", { name: /Exam/ }).click();
  await page.getByLabel("Show the examiner's words while speaking").uncheck();
  await expect(page.getByText("Exam conditions: this session counts")).toBeVisible();
  await page.getByRole("button", { name: "Start" }).nth(1).click();

  await expect(page.getByText("Exam conditions", { exact: true })).toBeVisible();
  await expect(page.getByText("Posez-moi des questions")).toBeVisible();
  await expect(page.getByText("Preparation")).toBeVisible();
  await page.getByRole("button", { name: "I'm ready" }).click();
  // The fake provider returns no real SDP answer, so the call must fail and end cleanly.
  await page.getByRole("button", { name: "Begin" }).click();

  await expect(page.getByRole("main").getByRole("alert")).toBeVisible();
  await expect(page.getByText("No answer was heard")).toBeVisible();
  await expect(page.getByRole("button", { name: "Choose another task" })).toBeVisible();
});

test("class notes are extracted, approved and land in the Library and Review", async ({ page }) => {
  const note = [
    "# Day 7 — Class Notes",
    "",
    "## Au café",
    "",
    "|French|Gender|Meaning|",
    "|---|---|---|",
    "|un croissant|masc.|a croissant|",
    "|une addition|fem.|the bill|",
    "|Je voudrais un café, s'il vous plaît.||I would like a coffee, please.|",
  ].join("\n");
  await page.goto("/notes");
  await page.getByLabel("Upload notes").setInputFiles({
    name: "Day_7.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(note),
  });
  await expect(page.getByText("3 items to review")).toBeVisible();

  await page.getByRole("link", { name: /Day 7 — Class Notes/ }).click();
  await page.getByLabel("Keep une addition").uncheck();
  await page.getByRole("button", { name: "Save" }).click();
  await expect(
    page.getByText("Saved. Approved words and phrases are now in Review."),
  ).toBeVisible();

  await page.goto("/library");
  await expect(page.getByText("un croissant")).toBeVisible();
  await expect(page.getByText("Class notes · Day 7").first()).toBeVisible();
  await expect(page.getByText("une addition")).toHaveCount(0);
});

test("hovering a French word shows its English meaning, but not in a timed drill", async ({
  page,
}) => {
  await page.goto("/lessons/a1-01-se-presenter/grammaire");
  // Cells are wider than their word; point at the text itself, past the cell padding.
  await page
    .getByRole("cell", { name: "suis", exact: true })
    .first()
    .hover({ position: { x: 22, y: 18 } });

  const tip = page.getByRole("tooltip");
  await expect(tip).toContainText("être");
  await expect(tip).toContainText("(I) am");
  await page.mouse.move(0, 0);
  await expect(tip).toBeHidden();

  await page.goto("/drills");
  await page.getByRole("button", { name: "Start" }).nth(1).click();
  await page.getByRole("button", { name: "Begin" }).click();
  await page.locator('[lang="fr"]').first().hover();
  await expect(page.getByRole("tooltip")).toHaveCount(0);
});
