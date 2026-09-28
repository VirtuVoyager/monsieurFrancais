"use client";

import { Timer } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cx } from "../ui/cx";

/** Seconds left until the server's deadline; calls `onExpire` once when it reaches zero. */
export function useCountdown(deadline: string, onExpire: () => void): number | null {
  const [remaining, setRemaining] = useState<number | null>(null);
  const expire = useRef(onExpire);
  useEffect(() => {
    expire.current = onExpire;
  }, [onExpire]);

  useEffect(() => {
    const end = new Date(deadline).getTime();
    let fired = false;
    const id = setInterval(() => {
      const left = Math.max(Math.round((end - Date.now()) / 1000), 0);
      setRemaining(left);
      if (left === 0 && !fired) {
        fired = true;
        expire.current();
      }
    }, 250);
    return () => clearInterval(id);
  }, [deadline]);

  return remaining;
}

export function Clock({ remaining }: { remaining: number | null }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 font-medium tabular-nums",
        remaining !== null && remaining < 60 ? "text-danger" : "text-ink",
      )}
    >
      <Timer className="size-4" aria-hidden />
      {remaining === null
        ? "–:–"
        : `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}`}
    </span>
  );
}
