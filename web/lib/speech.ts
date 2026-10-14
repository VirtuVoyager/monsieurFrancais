/**
 * Browser speech synthesis stands in for Azure neural TTS until generated audio exists.
 * It is for practice only; timed assessments will use cached Azure audio.
 */
export function speakFrench(text: string, rate = 0.95): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "fr-FR";
  utterance.rate = rate;
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang.startsWith("fr"));
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
}
