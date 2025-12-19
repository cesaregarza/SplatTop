import { escapeCsvCell, safePearsonCorrelation, toCsvRow } from "./competitionVizUtils";

describe("competitionVizUtils", () => {
  describe("escapeCsvCell", () => {
    it("quotes fields containing commas", () => {
      expect(escapeCsvCell("a,b")).toBe('"a,b"');
    });

    it("escapes quotes by doubling them", () => {
      expect(escapeCsvCell('a"b')).toBe('"a""b"');
    });

    it("quotes fields containing newlines", () => {
      expect(escapeCsvCell("a\nb")).toBe('"a\nb"');
    });

    it("mitigates CSV formula injection", () => {
      expect(escapeCsvCell("=2+2")).toBe("'=2+2");
      expect(escapeCsvCell("  -2+2")).toBe("'  -2+2");
    });
  });

  describe("toCsvRow", () => {
    it("joins and escapes cells", () => {
      expect(toCsvRow(["a,b", "c"])).toBe('"a,b",c');
    });
  });

  describe("safePearsonCorrelation", () => {
    it("returns +1 for perfect positive correlation", () => {
      const points = [
        { x: 1, y: 1 },
        { x: 2, y: 2 },
        { x: 3, y: 3 },
      ];
      const correlation = safePearsonCorrelation(points, (p) => p.x, (p) => p.y);
      expect(correlation).toBeCloseTo(1, 12);
    });

    it("returns -1 for perfect negative correlation", () => {
      const points = [
        { x: 1, y: 3 },
        { x: 2, y: 2 },
        { x: 3, y: 1 },
      ];
      const correlation = safePearsonCorrelation(points, (p) => p.x, (p) => p.y);
      expect(correlation).toBeCloseTo(-1, 12);
    });

    it("returns 0 when the denominator is zero", () => {
      const points = [
        { x: 1, y: 1 },
        { x: 1, y: 2 },
      ];
      const correlation = safePearsonCorrelation(points, (p) => p.x, (p) => p.y);
      expect(correlation).toBe(0);
      expect(Number.isFinite(correlation)).toBe(true);
    });

    it("ignores non-finite values", () => {
      const points = [
        { x: 1, y: 1 },
        { x: 2, y: 2 },
        { x: Number.NaN, y: 3 },
      ];
      const correlation = safePearsonCorrelation(points, (p) => p.x, (p) => p.y);
      expect(correlation).toBeCloseTo(1, 12);
    });
  });
});

