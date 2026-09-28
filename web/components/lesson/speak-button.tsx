"use client";

import { Volume2 } from "lucide-react";

import { speakFrench } from "@/lib/speech";

export function SpeakButton({ text, label = "Listen" }: { text: string; label?: string }) {
  return (
    <button
      type="button"
      onClick={() => speakFrench(text)}
      aria-label={`${label}: ${text}`}
      className="text-muted hover:bg-surface-2 hover:text-accent rounded-lg p-1.5 transition-colors"
    >
      <Volume2 className="size-4" aria-hidden />
    </button>
  );
}
