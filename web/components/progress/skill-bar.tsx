const LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"];

export type SkillEstimateView = {
  label: string;
  /** Position on the A1→C2 axis, 0–100. */
  position: number;
  /** Half-width of the uncertainty band on the same axis. */
  spread: number;
  caption: string;
  stale: boolean;
};

export function SkillBar({
  skill,
  estimate,
  targetPosition,
  highlight = false,
}: {
  skill: string;
  estimate: SkillEstimateView | null;
  targetPosition: number;
  highlight?: boolean;
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-4">
        <span className={`text-sm font-medium ${highlight ? "text-danger" : ""}`}>
          {skill}
          {highlight && <span className="ml-2 text-xs">weakest</span>}
        </span>
        <span className="text-muted text-right text-xs">
          {estimate ? estimate.caption : "No timed evidence yet"}
          {estimate?.stale && " · stale"}
        </span>
      </div>
      <div
        className="bg-surface-2 relative h-3 rounded-full"
        role="img"
        aria-label={estimate ? `${skill}: ${estimate.label}` : `${skill}: not assessed yet`}
      >
        {estimate && (
          <>
            <div
              className="bg-accent/25 absolute inset-y-0 rounded-full"
              style={{
                left: `${Math.max(estimate.position - estimate.spread, 0)}%`,
                width: `${Math.min(estimate.spread * 2, 100)}%`,
              }}
            />
            <div
              className={`absolute inset-y-0 left-0 rounded-full ${estimate.stale ? "bg-muted" : "bg-accent"}`}
              style={{ width: `${estimate.position}%` }}
            />
          </>
        )}
        <div
          className="bg-ink absolute -inset-y-1 w-0.5"
          style={{ left: `${targetPosition}%` }}
          title="NCLC 7 target"
        />
      </div>
      <div className="text-muted mt-1 grid grid-cols-6 text-[10px]">
        {LEVELS.map((level) => (
          <span key={level}>{level}</span>
        ))}
      </div>
    </div>
  );
}
