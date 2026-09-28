"use client";

import { Volume2 } from "lucide-react";

import { speakFrench } from "@/lib/speech";

export function SpeakButton({ text, label = "Listen" }: { text: string; label?: string }) {
  return (
    <button
      type="button"
      onClick={() => speakFrench(text)}
      aria-label={`${label}: ${text}`}
      className="rounded-lg p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-accent"
    >
      <Volume2 className="size-4" aria-hidden />
    </button>
  );
}
