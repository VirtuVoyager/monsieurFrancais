import { cx } from "../ui/cx";

export function countWords(text: string): number {
  // Elisions count as two words, matching the grader.
  const trimmed = text.replace(/['’]/g, " ").trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

export function WritingEditor({
  value,
  onChange,
  minWords,
  maxWords,
  disabled = false,
  note,
}: {
  value: string;
  onChange: (text: string) => void;
  minWords: number;
  maxWords: number;
  disabled?: boolean;
  note?: string;
}) {
  const words = countWords(value);
  const inRange = words >= minWords && words <= maxWords;
  return (
    <div className="space-y-2">
      <textarea
        lang="fr"
        aria-label="Your answer"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        rows={10}
        spellCheck={false}
        className="w-full rounded-xl border border-line bg-surface p-3 leading-relaxed outline-none focus:border-accent disabled:opacity-70"
      />
      <div className="flex items-center justify-between text-sm">
        <span className={cx("tabular-nums", inRange ? "text-success" : "text-muted")}>
          {words} words · target {minWords}–{maxWords}
        </span>
        {note && <span className="text-xs text-muted">{note}</span>}
      </div>
    </div>
  );
}
