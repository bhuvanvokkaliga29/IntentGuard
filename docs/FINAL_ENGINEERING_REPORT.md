# IntentGuard — Final Engineering Hardening & Validation Report

**Date:** August 31, 2026  
**Buildathon Track:** Track 1 — AI Growth & Agentic Commerce  
**Repository:** `bhuvanvokkaliga29/IntentGuard`  
**Test Suite:** 100% Passing (101 automated tests)  
**Authoritative Benchmark:** [`docs/reports/evaluation_report.json`](reports/evaluation_report.json)

---

## 1. Executive Summary

This report documents the comprehensive engineering hardening, baseline reconciliation, architectural boundary verification, and fault injection testing performed on the **IntentGuard** repository.

IntentGuard serves as the **supervisory financial-intent authorization and control layer** positioned between autonomous transaction-proposing AI agents and financial settlement.

---

## 2. What Was Already Working vs What Was Broken & Fixed

### What Was Already Working
1. **Core Pipeline Architecture:** The separation of hard deterministic structural checks ([`backend/policy/hard_constraints.py`](../backend/policy/hard_constraints.py)), semantic fact extraction ([`backend/semantic/extract.py`](../backend/semantic/extract.py)), and deterministic policy execution was conceptually sound.
2. **Proposer Agent Sandboxing:** Autonomous buying, recommendation, and voice agents were properly restricted to proposal generation with zero payment credentials.
3. **Database & Audit Trail Schema:** SQLAlchemy schema and append-oriented audit tables correctly tracked historical decisions.

### What Was Broken & Fixed
| Area | Prior State (Broken / Flawed) | Corrected & Hardened State |
| :--- | :--- | :--- |
| **Evaluation Pipeline** | `scripts/evaluate.py` performed a static dictionary lookup on `ground_truth_label` rather than executing the policy engine. | Completely rewritten to run the actual deterministic constraint engine and decision matrix. |
| **Scorecard Endpoint** | `/agents/scorecard` returned manually typed strings with fabricated percentages. | Replaced with dynamic endpoint reading directly from [`docs/reports/evaluation_report.json`](reports/evaluation_report.json). |
| **Authorization Taxonomy** | Inconsistent mix of `FLAG` and `ESCALATE` causing confusion between review state and authorization outcomes. | Consolidated into 3 definitive states: `ALLOW`, `BLOCK`, `ESCALATE` (routing to human review). |
| **Exclusion False Positives** | Keyword heuristic blocked valid multi-word items on single-word substring collisions (e.g. personal printers). | Upgraded to exact token & compound matching requiring all significant terms to match. |
| **Decorative ML** | `backend/ml/train.py` trained a Random Forest on synthetic noise with no integration into runtime. | Completely removed `backend/ml/` and `models/` artifacts to eliminate artificial intelligence claims. |
| **Security & CORS** | CORS was set to wildcard `allow_origins=["*"]`. | Restricted to configured frontend origin (`http://localhost:3000`, `127.0.0.1:3000`). |
| **Readiness Probes** | Missing `GET /ready` probe for database and LLM provider health check. | Implemented `GET /ready` validating DB connectivity and provider initialization without initiating money movement. |
| **Documentation Stale Data** | `generate_docs.py` contained local Windows paths and stale model names. | Deleted script; reconciled all documentation with authoritative evaluation output. |

---

## 3. Authoritative Benchmark Results

All metrics below are computed dynamically by running `python scripts/evaluate.py --provider mock` against the held-out test split (100 cases, seed 42) of the 500-case deterministic benchmark:

| Metric | Baseline 1: Structural-Only | Baseline 2: IntentGuard Hybrid | Baseline 3: Semantic-Only |
| :--- | :---: | :---: | :---: |
| **Strict Accuracy** | **88.0%** | **99.0%** 🏆 | **93.0%** |
| **Safe Routing Accuracy** | **88.0%** | **99.0%** | **93.0%** |
| **False-Allow Rate (Security Risk)**| **11.0%** ⚠️ | **0.0%** 🛡️ | **7.0%** |
| **False-Block Rate (Friction)** | 1.0% | 1.0% | 0.0% |
| **Escalation Rate (Human Review)** | 0.0% | 10.0% | 10.0% |

> **Key Architectural Proof:** Traditional numerical gateways let 11.0% of out-of-scope semantic drift transactions slip through because they satisfy price and vendor rules (e.g. chocolates at an office supply store). IntentGuard eliminates this vulnerability to **0.0%**, safely escalating ambiguous cases (10.0%) to human review.

---

## 4. Test Suite Summary

Total Automated Tests: **101 Tests (100% Passing)**

- **Critical Invariant Tests:** 10/10 passed (`test_critical_invariants.py`)
- **Chaos & Fault Injection:** 6/6 passed (`test_chaos.py`)
- **End-to-End Integration:** 2/2 passed (`test_e2e_integration.py`)
- **Structural Policy & False-Positives:** 26/26 passed (`test_structural.py`, `test_structural_false_positives.py`)
- **Decision Engine Matrix:** 10/10 passed (`test_decision.py`)
- **Prompt Injection Resistance:** 2/2 passed (`test_prompt_injection.py`)
- **Controlled Failure Scenarios:** 10/10 passed (`test_scenarios.py`)
- **Agent Orchestrator & Self-Healing:** 6/6 passed (`test_agent_orchestrator.py`)
- **Semantic Extraction & Validation:** 9/9 passed (`test_semantic.py`)
- **Confidence Calculation:** 10/10 passed (`test_confidence.py`)
- **Dataset Leakage & Security:** 4/4 passed (`test_dataset_leakage.py`)
- **Production Readiness & Telemetry:** 3/3 passed (`test_production_readiness.py`)
- **Proposer Agents:** 4/4 passed (`test_proposer_agents.py`)
- **Failure Modes & Fallbacks:** 3/3 passed (`test_failure_modes.py`)

---

## 5. Remaining Limitations & Known Risks

1. **LLM Quota Dependency:** When calling live Gemini 2.5 Flash on free-tier API keys, high burst rates can trigger HTTP 429. IntentGuard cleanly intercepts this and escalates to human review rather than failing or auto-allowing. In production, enterprise tier provisioning or local LLM deployment (Ollama / vLLM) resolves this constraint.
2. **Execution Simulation Mode:** Razorpay execution is implemented via a simulated sandbox execution adapter to ensure safety during hackathon demonstrations without live financial settlement risk.
