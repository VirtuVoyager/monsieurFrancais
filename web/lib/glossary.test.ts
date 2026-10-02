import { describe, expect, it } from "vitest";

import { lookup, normalize, type Glossary } from "./glossary";

const glossary: Glossary = {
  suis: { lemma: "être", en: "(I) am" },
  "j'": { lemma: "je", en: "I" },
  ai: { lemma: "avoir", en: "(I) have" },
  "aujourd'hui": { lemma: "aujourd'hui", en: "today" },
  "il y a": { lemma: "il y a", en: "there is / there are" },
  habite: { lemma: "habiter", en: "lives" },
  elle: { lemma: "elle", en: "she" },
  y: { lemma: "y", en: "there" },
};

const at = (text: string, word: string, nth = 0) => {
  let index = -1;
  for (let i = 0; i <= nth; i++) index = text.indexOf(word, index + 1);
  return lookup(glossary, text, index);
};

describe("normalize", () => {
  it("matches the API's keys", () => {
    expect(normalize("J’ai  Été")).toBe("j'ai été");
    expect(normalize("s’ appelle")).toBe("s'appelle");
  });
});

describe("lookup", () => {
  it("finds a plain word and its exact span", () => {
    const hit = at("Je suis indien.", "suis");
    expect(hit?.gloss.en).toBe("(I) am");
    expect(hit?.text).toBe("suis");
  });

  it("prefers a fixed phrase around the word", () => {
    expect(at("Il y a deux chambres.", "y")?.text).toBe("Il y a");
    expect(at("Il y a deux chambres.", "a ")?.gloss.en).toBe("there is / there are");
  });

  it("splits elisions under the pointer, but keeps words that own their apostrophe", () => {
    expect(at("J’ai trente ans.", "J")?.gloss.en).toBe("I");
    expect(at("J’ai trente ans.", "ai")?.gloss.en).toBe("(I) have");
    expect(at("Aujourd'hui, il pleut.", "jour")?.gloss.en).toBe("today");
  });

  it("splits hyphenated inversions", () => {
    expect(at("Où habite-t-elle ?", "habite")?.text).toBe("habite");
    expect(at("Où habite-t-elle ?", "elle")?.gloss.en).toBe("she");
  });

  it("ignores punctuation, spaces and unknown words", () => {
    expect(lookup(glossary, "Je suis.", 2)).toBeNull();
    expect(at("Bonjour !", "Bon")).toBeNull();
  });
});
