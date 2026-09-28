import type { HTMLAttributes } from "react";

import { cx } from "./cx";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx("border-line bg-surface rounded-2xl border p-5 shadow-sm sm:p-6", className)}
      {...props}
    />
  );
}

export function SectionTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cx("font-serif text-xl font-semibold", className)} {...props} />;
}

export function Eyebrow({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cx("text-muted text-xs font-semibold tracking-wider uppercase", className)}
      {...props}
    />
  );
}
