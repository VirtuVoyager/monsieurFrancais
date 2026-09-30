import { describe, expect, it } from "vitest";

import { axisPosition } from "./scales";

describe("axisPosition", () => {
  it("places band boundaries at segment edges", () => {
    expect(axisPosition(400, true)).toBeCloseTo(50);
    expect(axisPosition(10, false)).toBeCloseTo(50);
  });

  it("interpolates within a band and clamps at the ends", () => {
    expect(axisPosition(450, true)).toBeCloseTo(58.33, 1);
    expect(axisPosition(699, true)).toBeLessThanOrEqual(100);
    expect(axisPosition(20, false)).toBeLessThanOrEqual(100);
    expect(axisPosition(0, false)).toBe(0);
  });
});
