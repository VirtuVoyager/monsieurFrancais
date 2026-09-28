import type { Schemas } from "@/lib/api/client";

import { ProgressBar } from "../ui/progress-bar";

export function CoverageBar({ coverage }: { coverage: Schemas["CoverageOut"] }) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <span className="text-sm font-medium">Module coverage</span>
        <span className="text-muted text-sm tabular-nums">
          {coverage.covered} / {coverage.total} modules · {coverage.percent}%
        </span>
      </div>
      <ProgressBar value={coverage.percent} label="Module coverage" />
    </div>
  );
}
