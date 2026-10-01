export type Gloss = { lemma: string; en: string };
export type Glossary = Record<string, Gloss>;
export type Hit = { text: string; gloss: Gloss; start: number; end: number };

const WORD = /[\p{L}\p{M}]+(?:['’-][\p{L}\p{M}]+)*/gu;
// Longest fixed phrase the glossaries hold ("s'il vous plaît", "du lundi au vendredi").
const MAX_PHRASE = 4;

/** Must match the API's normalize(): lower case, straight apostrophes, NFC, single spaces. */
export function normalize(text: string): string {
  return text
    .normalize("NFC")
    .replace(/’/g, "'")
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(" ")
    .replace(/'\s+/g, "'");
}

type Span = { start: number; end: number };

function words(text: string): Span[] {
  return Array.from(text.matchAll(WORD), (m) => ({
    start: m.index,
    end: m.index + m[0].length,
  }));
}

/**
 * What the pointer is on, most specific meaning first: a fixed phrase around the word
 * ("il y a"), the whole word ("aujourd'hui"), then the elided or hyphenated piece under the
 * pointer ("j'" or "ai" in "j'ai").
 */
export function lookup(glossary: Glossary, text: string, offset: number): Hit | null {
  const spans = words(text);
  const index = spans.findIndex((s) => s.start <= offset && offset < s.end);
  if (index < 0) return null;
  const find = (start: number, end: number): Hit | null => {
    const slice = text.slice(start, end);
    const gloss = glossary[normalize(slice)];
    return gloss ? { text: slice, gloss, start, end } : null;
  };

  for (let n = MAX_PHRASE; n >= 2; n--) {
    for (let first = index - n + 1; first <= index; first++) {
      const last = first + n - 1;
      if (first < 0 || last >= spans.length) continue;
      const hit = find(spans[first]!.start, spans[last]!.end);
      if (hit) return hit;
    }
  }
  const word = spans[index]!;
  const whole = find(word.start, word.end);
  if (whole) return whole;
  // An elided piece keeps its apostrophe (j', l', qu'); a hyphen just separates (habite-t-elle).
  let start = word.start;
  for (const piece of text.slice(word.start, word.end).split(/(?<=['’])|-/)) {
    const end = start + piece.length;
    if (offset >= start && offset < end) return find(start, end);
    start = end + (text[end] === "-" ? 1 : 0);
  }
  return null;
}
