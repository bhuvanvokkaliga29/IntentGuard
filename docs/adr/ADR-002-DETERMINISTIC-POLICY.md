# ADR-002: Deterministic Financial Authorization Engine

## Status
Accepted

## Context
Financial authorization systems require absolute auditability, explainability, and mathematical reproducibility. Relying on probabilistic model judgments for compliance or money movement violates fundamental fintech safety requirements.

## Decision
All financial decisions are computed via a **Deterministic Decision Matrix** in `backend/policy/decision.py`. The engine maps:
1. Structural check pass/fail
2. Extracted structured item facts
3. Majority semantic entailment verdict
4. Deterministically computed confidence score

## Consequences
- The exact decision path (e.g. `structural_pass + semantic_no_fit + high_confidence -> BLOCK`) is stamped on every record.
- Given the same structural results and semantic verdicts, the decision is 100% reproducible.
- Ambiguity or low confidence triggers immediate escalation (`ESCALATE`) to human review.
