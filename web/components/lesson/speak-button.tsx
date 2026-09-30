"use client";

import { Volume2 } from "lucide-react";

import { speakFrench } from "@/lib/speech";

/** Plays the recorded clip when one exists, otherwise the browser's French voice. */
export function SpeakButton({
  text,
  url,
  label = "Listen",
}: {
  text: string;
  url?: string | null;
  label?: string;
}) {
  const play = () => (url ? void new Audio(url).play() : speakFrench(text));
  return (
    <button
      type="button"
      onClick={play}
      aria-label={`${label}: ${text}`}
      className="rounded-lg p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-accent"
    >
      <Volume2 className="size-4" aria-hidden />
    </button>
  );
}
