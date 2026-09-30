import { cx } from "../ui/cx";

const GENDERS = {
  m: { label: "masc.", className: "text-masc border-masc/40" },
  f: { label: "fém.", className: "text-fem border-fem/40" },
} as const;

export function GenderTag({ gender }: { gender: string | null | undefined }) {
  if (gender !== "m" && gender !== "f") return null;
  const { label, className } = GENDERS[gender];
  return (
    <span className={cx("rounded border px-1.5 text-[11px] font-medium", className)}>{label}</span>
  );
}
