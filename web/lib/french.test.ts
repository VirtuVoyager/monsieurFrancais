import { describe, expect, it } from "vitest";

import { fr } from "./french";

describe("fr", () => {
  it("puts a narrow no-break space before high punctuation", () => {
    expect(fr("Comment vous appelez-vous ?")).toBe("Comment vous appelez-vous ?");
    expect(fr("Attention : double l")).toBe("Attention : double l");
  });

  it("uses typographic apostrophes and spaced guillemets", () => {
    expect(fr("« J'ai trente ans »")).toBe("« J’ai trente ans »");
  });
});
