import {
  chipClass,
  createGradeShowcaseRows,
  formatDate,
  gradeChipClass,
  gradeFor,
  isXX,
  rateFor,
  severityOf,
  tierFor,
} from "./stableLeaderboardUtils";

describe("stableLeaderboardUtils", () => {
  it("assigns grades based on display score", () => {
    expect(gradeFor(150)).toBe("XA+");
    expect(gradeFor(9999)).toBe("XX★");
  });

  it("formats dates defensively", () => {
    expect(formatDate(0)).toBe("—");
    expect(formatDate("invalid")).toBe("—");
    expect(formatDate(Date.UTC(2024, 0, 15))).not.toBe("—");
  });

  it("maps severity thresholds", () => {
    expect(severityOf(null)).toBe("neutral");
    expect(severityOf(-1)).toBe("expired");
    expect(severityOf(0)).toBe("critical");
    expect(severityOf(7)).toBe("critical");
    expect(severityOf(8)).toBe("watch");
    expect(severityOf(30)).toBe("watch");
    expect(severityOf(31)).toBe("buffer");
  });

  it("builds chip styles and tiers", () => {
    expect(chipClass("critical")).toContain("bg-red-500");
    expect(chipClass("unknown")).toContain("bg-slate-700/20");
    expect(tierFor("XX+")).toBe("grade-tier-xxplus");
    expect(tierFor("unknown")).toBe("grade-tier-default");
    expect(gradeChipClass("XX+", true)).toBe("grade-chip grade-tier-xxplus is-active");
  });

  it("recognizes XX tiers and rates", () => {
    expect(isXX("XX")).toBe(true);
    expect(isXX("XA")).toBe(false);
    expect(rateFor("XX★")).toBe(7.5);
    expect(rateFor("XX+")).toBe(4.5);
    expect(rateFor("XX")).toBe(3);
    expect(rateFor("XA")).toBe(2.4);
  });

  it("creates showcase rows with sample metadata", () => {
    const rows = createGradeShowcaseRows();
    const xxRow = rows.find((row) => row.display_name.startsWith("[Sample] XX —"));
    const xxStarRow = rows.find((row) => row.display_name.startsWith("[Sample] XX★ —"));

    expect(rows.length).toBeGreaterThan(0);
    expect(xxRow.is_showcase).toBe(true);
    expect(xxRow.player_id.startsWith("__sample_")).toBe(true);
    expect(xxRow.danger_days_left).toBeCloseTo(0.45, 2);
    expect(xxStarRow.danger_days_left).toBeNull();
  });
});
