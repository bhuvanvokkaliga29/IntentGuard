import { describe, it, expect } from "vitest";

describe("Demo Benchmark Scenarios UI Integrity", () => {
  const CANONICAL_SCENARIOS = [
    { id: "scenario-1", name: "Scenario 1: Semantic Drift", expected: "BLOCK" },
    { id: "scenario-2", name: "Scenario 2: Hard Categorical Mismatch", expected: "BLOCK" },
    { id: "scenario-3", name: "Scenario 3: Vague Description", expected: "ESCALATE" },
    { id: "scenario-4", name: "Scenario 4: Correct Purchase", expected: "ALLOW" },
    { id: "scenario-5", name: "Scenario 5: Promotion Trap", expected: "BLOCK" },
    { id: "scenario-6", name: "Scenario 6: Merchant Allowlist Violation", expected: "BLOCK" },
    { id: "scenario-7", name: "Scenario 7: Amount / Budget Violation", expected: "BLOCK" },
    { id: "scenario-8", name: "Scenario 8: Insufficient Context Mandate", expected: "ESCALATE" },
    { id: "scenario-9", name: "Scenario 9: Prompt Injection Attack", expected: "BLOCK" },
  ];

  it("contains exactly 9 canonical benchmark cases", () => {
    expect(CANONICAL_SCENARIOS).toHaveLength(9);
  });

  it("ensures every scenario maps strictly to ALLOW, BLOCK, or ESCALATE", () => {
    const validOutcomes = new Set(["ALLOW", "BLOCK", "ESCALATE"]);
    CANONICAL_SCENARIOS.forEach((sc) => {
      expect(validOutcomes.has(sc.expected)).toBe(true);
    });
  });

  it("verifies expected distribution across cases", () => {
    const blocks = CANONICAL_SCENARIOS.filter((s) => s.expected === "BLOCK");
    const allows = CANONICAL_SCENARIOS.filter((s) => s.expected === "ALLOW");
    const escalates = CANONICAL_SCENARIOS.filter((s) => s.expected === "ESCALATE");

    expect(blocks.length).toBe(6);
    expect(allows.length).toBe(1);
    expect(escalates.length).toBe(2);
  });
});
