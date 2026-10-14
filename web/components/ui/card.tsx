import type { HTMLAttributes } from "react";

import { cx } from "./cx";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx("rounded-2xl border border-line bg-surface p-5 shadow-sm sm:p-6", className)}
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
      className={cx("text-xs font-semibold tracking-wider text-muted uppercase", className)}
      {...props}
    />
  );
}
