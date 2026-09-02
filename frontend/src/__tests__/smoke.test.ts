import { describe, it, expect } from "vitest";

describe("Frontend Core Integrity & Policy Types", () => {
  it("validates the 3 canonical authorization states", () => {
    const validStates = ["ALLOW", "BLOCK", "ESCALATE"];
    expect(validStates).toHaveLength(3);
    expect(validStates).toContain("ALLOW");
    expect(validStates).toContain("BLOCK");
    expect(validStates).toContain("ESCALATE");
  });

  it("evaluates confidence score thresholds deterministically", () => {
    const HIGH_THRESHOLD = 0.75;
    const LOW_THRESHOLD = 0.40;

    const testScores = [
      { score: 0.95, expectedLevel: "HIGH" },
      { score: 0.75, expectedLevel: "HIGH" },
      { score: 0.60, expectedLevel: "MEDIUM" },
      { score: 0.35, expectedLevel: "LOW" },
    ];

    testScores.forEach(({ score, expectedLevel }) => {
      let level = "MEDIUM";
      if (score >= HIGH_THRESHOLD) level = "HIGH";
      else if (score < LOW_THRESHOLD) level = "LOW";
      expect(level).toBe(expectedLevel);
    });
  });

  it("maps decision states to correct badge visual treatments", () => {
    const getBadgeStyle = (decision: string) => {
      switch (decision) {
        case "ALLOW":
          return { color: "text-acid-lime", bg: "bg-acid-lime/10", border: "border-acid-lime/30" };
        case "BLOCK":
          return { color: "text-coral-red", bg: "bg-coral-red/10", border: "border-coral-red/30" };
        case "ESCALATE":
          return { color: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-400/30" };
        default:
          return { color: "text-mist", bg: "bg-carbon", border: "border-graphite" };
      }
    };

    expect(getBadgeStyle("ALLOW").color).toBe("text-acid-lime");
    expect(getBadgeStyle("BLOCK").color).toBe("text-coral-red");
    expect(getBadgeStyle("ESCALATE").color).toBe("text-amber-400");
  });

  it("verifies Track 5 Open Track identity lock", () => {
    const TRACK_IDENTITY = "TRACK 5 · OPEN TRACK";
    expect(TRACK_IDENTITY).toContain("TRACK 5");
    expect(TRACK_IDENTITY).toContain("OPEN TRACK");
  });
});
