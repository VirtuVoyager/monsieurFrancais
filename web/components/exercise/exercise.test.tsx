import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Exercise } from "./exercise";

describe("Exercise", () => {
  it("checks a cloze answer and shows the correction", async () => {
    const onCheck = vi
      .fn()
      .mockResolvedValue({ correct: false, expected: "suis", explanation: null });
    render(
      <Exercise number={1} exercise={{ kind: "cloze", prompt: "Je ___ ici." }} onCheck={onCheck} />,
    );

    await userEvent.type(screen.getByLabelText("Answer for question 1"), "es");
    await userEvent.click(screen.getByRole("button", { name: "Check" }));

    expect(onCheck).toHaveBeenCalledWith({ text: "es" });
    expect(await screen.findByText(/Answer: suis/)).toBeTruthy();
  });

  it("builds a word-order answer from tapped words", async () => {
    const onChange = vi.fn();
    render(
      <Exercise
        number={2}
        exercise={{ kind: "order", words: ["Nadia.", "m'appelle", "Je"] }}
        onChange={onChange}
      />,
    );

    for (const word of ["Je", "m'appelle", "Nadia."]) {
      await userEvent.click(screen.getByRole("button", { name: word }));
    }

    expect(onChange).toHaveBeenLastCalledWith({ text: "Je m'appelle Nadia." });
  });
});
