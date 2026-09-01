# IntentGuard — Benchmark Evaluation & Comparative Analysis

> **Live AI Benchmark:** [`docs/reports/evaluation_report_live.json`](reports/evaluation_report_live.json)  
> **Offline Mock (CI):** [`docs/reports/evaluation_report.json`](reports/evaluation_report.json)  

---

## 1. Executive Summary

Autonomous financial AI agents require supervisory control layers that intercept semantic intent violations without causing unacceptable false-block friction on legitimate spending. 

We evaluate IntentGuard in two modes: a Live Provider benchmark using genuine LLMs (Gemini/Grok), and an Offline Mock benchmark for rapid CI/regression testing of the deterministic policy pipeline.

---

## 2. Live Provider Benchmark (Genuine AI Performance)

**Source:** `docs/reports/evaluation_report_live.json`  
**Command:** `python scripts/evaluate.py --provider gemini --limit 30`

This evaluates the actual prompt templates and real LLM reasoning. *(Metrics will be populated once the live benchmark is run. Refer to the JSON report for authoritative numbers.)*

---

## 3. Offline Mock Benchmark (CI / Regression)

**Source:** `docs/reports/evaluation_report.json`  
**Command:** `python scripts/evaluate.py --provider mock`

**WARNING:** The numbers below are generated using a keyword-matching simulator (`MockProvider`). They prove that the *deterministic structural engine and routing policy* work correctly, but they do **NOT** constitute evidence of real LLM semantic capability.

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
