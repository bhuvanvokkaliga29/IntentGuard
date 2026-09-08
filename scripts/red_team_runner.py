"""
IntentGuard — Adversarial Red-Team Runner Script

Executes all 12+ adversarial attack scenarios, verifies the supervisory boundary,
and outputs a structured audit report to docs/reports/red_team_report.json.

Usage:
  python scripts/red_team_runner.py
"""

import json
import os
import sys
from pathlib import Path

# Root path adjustment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.security.red_team import execute_red_team_suite


def main():
    print("=" * 65)
    print("INTENTGUARD — ADVERSARIAL RED-TEAM STRESS TEST RUNNER")
    print("=" * 65)

    results = execute_red_team_suite()

    print(f"\nTotal Scenarios Evaluated: {results['total_scenarios']}")
    print(f"Blocked (Rejected):        {results['blocked']}")
    print(f"Escalated (Human Review):  {results['escalated']}")
    print(f"Executions Prevented:      {results['financial_executions_prevented']}/{results['total_scenarios']}")
    print(f"Execution Breaches:        {results['financial_executions_breached']}")
    print(f"Security Pass Rate:        {results['pass_rate'] * 100:.1f}%")
    print(f"Zero-Bypass Invariant:     {'HELD [PASS]' if results['zero_bypass_invariant_held'] else 'FAILED'}")

    print("\nDetailed Attack Results:")
    for r in results["results"]:
        status = "[PASS]" if r["passed_security"] else "[FAIL]"
        print(f"  {status} {r['attack_id']}: {r['attack_vector']} -> Outcome: {r['actual_outcome']} (Expected: {r['expected_outcome']})")

    # Output to docs/reports/red_team_report.json
    out_dir = Path("docs/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "red_team_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Red-team report saved to {report_file}")

    if not results["zero_bypass_invariant_held"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
