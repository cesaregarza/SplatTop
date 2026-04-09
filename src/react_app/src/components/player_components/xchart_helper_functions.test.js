import { dataWithNulls } from "./xchart_helper_functions";

describe("dataWithNulls", () => {
  it("keeps consecutive observed days continuous even when the value is unchanged", () => {
    const points = [
      {
        x: 10,
        y: 2500,
        timestamp: "2026-01-01T03:00:00.000Z",
      },
      {
        x: 12,
        y: 2500,
        timestamp: "2026-01-02T22:00:00.000Z",
      },
    ];

    expect(dataWithNulls(points, 0.5, [])).toEqual(points);
  });

  it("inserts a discontinuity when observed days are missing", () => {
    const points = [
      {
        x: 10,
        y: 2500,
        timestamp: "2026-01-01T03:00:00.000Z",
      },
      {
        x: 14,
        y: 2500,
        timestamp: "2026-01-03T22:00:00.000Z",
      },
    ];

    expect(dataWithNulls(points, 0.5, [])).toEqual([
      points[0],
      { x: 12, y: null },
      points[1],
    ]);
  });
});
