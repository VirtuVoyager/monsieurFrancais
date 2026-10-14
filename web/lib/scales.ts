// Mirrors content/exam_scales.yaml: where a score sits on the A1→C2 axis of a skill bar.
const RECEPTIVE_BANDS = [100, 200, 300, 400, 500, 600, 700];
const PRODUCTIVE_BANDS = [0, 4, 6, 10, 14, 16, 21];

export const SKILLS = [
  { code: "CO", name: "Listening", receptive: true, nclc7: 458 },
  { code: "CE", name: "Reading", receptive: true, nclc7: 453 },
  { code: "EE", name: "Writing", receptive: false, nclc7: 10 },
  { code: "EO", name: "Speaking", receptive: false, nclc7: 10 },
] as const;

export function axisPosition(score: number, receptive: boolean): number {
  const bands = receptive ? RECEPTIVE_BANDS : PRODUCTIVE_BANDS;
  const segment = 100 / (bands.length - 1);
  for (let i = 0; i < bands.length - 1; i++) {
    if (score < bands[i + 1]) {
      const within = (score - bands[i]) / (bands[i + 1] - bands[i]);
      return (i + Math.max(within, 0)) * segment;
    }
  }
  return 100;
}
