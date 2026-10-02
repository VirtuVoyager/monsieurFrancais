"use client";

import { useRef, useState, type PointerEvent, type ReactNode } from "react";

import { lookup, normalize, type Glossary, type Hit } from "@/lib/glossary";
import { useGlossary } from "@/lib/queries";

type Tip = { hit: Hit; rect: DOMRect };

// Answers and inputs stay unglossed, so exercises still test the learner.
const SKIP = "input, textarea, select, button, [data-no-gloss]";

function caretAt(x: number, y: number): { node: Node; offset: number } | null {
  const position = document.caretPositionFromPoint?.(x, y);
  if (position) return { node: position.offsetNode, offset: position.offset };
  const range = document.caretRangeFromPoint?.(x, y);
  return range ? { node: range.startContainer, offset: range.startOffset } : null;
}

function find(glossary: Glossary, target: EventTarget, x: number, y: number): Tip | null {
  if (!(target instanceof Element) || !target.closest('[lang="fr"]') || target.closest(SKIP)) {
    return null;
  }
  const caret = caretAt(x, y);
  if (!caret || caret.node.nodeType !== Node.TEXT_NODE) return null;
  const text = caret.node.textContent ?? "";
  const hit = lookup(glossary, text, Math.min(caret.offset, Math.max(text.length - 1, 0)));
  if (!hit) return null;
  const range = document.createRange();
  range.setStart(caret.node, hit.start);
  range.setEnd(caret.node, hit.end);
  // The caret snaps to the nearest character, so check the pointer is really on the word.
  const inside = Array.from(range.getClientRects()).some(
    (r) => x >= r.left - 2 && x <= r.right + 2 && y >= r.top - 2 && y <= r.bottom + 2,
  );
  return inside ? { hit, rect: range.getBoundingClientRect() } : null;
}

/**
 * English meanings on hover (tap on touch screens) for any French text inside. One listener
 * and one tooltip for the whole region, whatever its length. Never wrap timed or exam screens.
 */
export function Glossed({ moduleId, children }: { moduleId?: string; children: ReactNode }) {
  const glossary = useGlossary(moduleId);
  const [tip, setTip] = useState<Tip | null>(null);
  const frame = useRef(0);

  const show = (e: PointerEvent<HTMLDivElement>) => {
    const entries = glossary.data;
    if (!entries) return;
    const { target, clientX, clientY } = e;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => setTip(find(entries, target, clientX, clientY)));
  };

  return (
    <div
      onPointerMove={(e) => e.pointerType === "mouse" && show(e)}
      onPointerUp={(e) => e.pointerType !== "mouse" && show(e)}
      onPointerLeave={() => setTip(null)}
    >
      {children}
      {tip && <Tooltip tip={tip} />}
    </div>
  );
}

function Tooltip({ tip }: { tip: Tip }) {
  const { hit, rect } = tip;
  const below = rect.bottom + 80 < window.innerHeight;
  const showLemma = normalize(hit.gloss.lemma) !== normalize(hit.text);
  return (
    <div
      role="tooltip"
      className="pointer-events-none fixed z-50 max-w-64 rounded-lg border border-line bg-surface px-3 py-2 text-sm shadow-lg"
      style={{
        left: Math.max(8, Math.min(rect.left, window.innerWidth - 264)),
        top: below ? rect.bottom + 6 : undefined,
        bottom: below ? undefined : window.innerHeight - rect.top + 6,
      }}
    >
      <p lang="fr" className="font-medium">
        {hit.text}
        {showLemma && <span className="font-normal text-muted"> · {hit.gloss.lemma}</span>}
      </p>
      <p className="text-muted">{hit.gloss.en}</p>
    </div>
  );
}
