# IntentGuard — Benchmark Evaluation & Comparative Analysis

> **Authoritative Source:** [`docs/reports/evaluation_report.json`](reports/evaluation_report.json)  
> **Reproduce with:** `python scripts/evaluate.py --provider mock`

---

## 1. Executive Summary

Autonomous financial AI agents require supervisory control layers that intercept semantic intent violations without causing unacceptable false-block friction on legitimate spending. 

We evaluated IntentGuard against two industry baselines on a held-out test split of **100 transactions** across diverse spending mandates (office supplies, domestic travel, team catering, and adversarial edge cases).

---

## 2. Comparative Benchmark Matrix

| Evaluation Metric | Baseline 1: Structural-Only (Budget/Allowlist) | Baseline 2: IntentGuard Hybrid (Structural + Semantic + Policy) | Baseline 3: Semantic-Only (Unbounded LLM) |
| :--- | :---: | :---: | :---: |
| **Strict Accuracy** | **88.0%** | **99.0%** | **93.0%** |
| **False-Allow Rate (Security Risk)** | **11.0%** | **0.0%** | **7.0%** |
| **False-Block Rate (Friction)** | 1.0% | 1.0% | 0.0% |
| **Escalation Rate (Human-in-Loop)** | 0.0% | 10.0% | 10.0% |
| **ALLOW Precision** | 80.0% | **100.0%** | 86.5% |
| **BLOCK Precision** | 97.8% | **97.8%** | **100.0%** |
| **ESCALATE Precision** | N/A (Blind) | **100.0%** | **100.0%** |

---

## 3. Key Findings & Architectural Proofs

1. **Elimination of False-Allow Risk (11.0% → 0.0%):**  
   Traditional numerical guardrails let 11.0% of out-of-scope semantic drift transactions drain company funds because they are priced within limits and sold at approved stores (e.g. chocolates at an office supply store). IntentGuard intercepts 100% of these.

2. **Safe Routing of Ambiguous Contexts (10.0% Escalation):**  
   When mandates or transaction line items lack sufficient evidence (e.g., `"miscellaneous items"`) or encounter prompt injection overrides, IntentGuard never auto-authorizes. It safely escalates 10.0% of ambiguous cases to human review.

3. **Zero-LLM Authority:**  
   The LLM is never given authorization authority. All final decisions are rendered by the deterministic policy matrix in [`backend/policy/decision.py`](../backend/policy/decision.py).

---

## 4. Benchmark Methodology

- **Dataset Size:** 500 records total (400 train, 100 held-out test split).
- **Test Seed:** 42 (reproducible deterministic generation).
- **Distribution:** 45 BLOCK, 45 ALLOW, 10 ESCALATE.
- **Evaluation Runner:** [`scripts/evaluate.py`](../scripts/evaluate.py)
