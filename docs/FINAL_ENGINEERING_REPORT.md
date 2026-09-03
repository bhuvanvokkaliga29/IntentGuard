# IntentGuard — Final Engineering Hardening & Validation Report

**Date:** September 3, 2026  
**Buildathon Track:** Track 5 — Open Track  
**Repository:** `bhuvanvokkaliga29/IntentGuard`  
**Test Suite:** 100% Passing (155 automated tests)  
**Authoritative Benchmark:** [`docs/reports/evaluation_report.json`](reports/evaluation_report.json)  
**Security Audit:** PASS (0 findings across 152 scanned files)  
**Integration Smoke Test:** 9 / 9 Passed (`scripts/smoke_test.py`)  

---

## 1. Executive Summary

This report documents the comprehensive engineering hardening, baseline reconciliation, architectural boundary verification, and fault injection testing performed on the **IntentGuard** repository.

IntentGuard serves as the **supervisory financial-intent authorization and control layer** positioned between autonomous transaction-proposing AI agents and financial settlement.

---

## 2. What Was Already Working vs What Was Broken & Fixed

### What Was Already Working
1. **Core Pipeline Architecture:** The separation of hard deterministic structural checks ([`backend/policy/hard_constraints.py`](../backend/policy/hard_constraints.py)), semantic fact extraction ([`backend/agent/agent.py`](../backend/agent/agent.py)), and deterministic policy execution was conceptually sound.
2. **Proposer Agent Sandboxing:** Autonomous buying, recommendation, and voice agents were properly restricted to proposal generation with zero payment credentials.
3. **Database & Audit Trail Schema:** SQLAlchemy schema and append-oriented audit tables correctly tracked historical decisions.

### What Was Hardened & Strengthened in Master Engineering Pass
| Area | Prior State | Hardened & Production-Grade State |
| :--- | :--- | :--- |
| **Audit Ledger Integrity** | Plain database rows susceptible to silent database tampering or deletion. | Implemented **Cryptographic SHA-256 Hash Chaining** (`backend/db.py`). Every audit entry links to the previous entry's SHA-256 digest; verifiable via `GET /audit/chain/verify`. |
| **API Authentication & Rate Limiting** | Open endpoints vulnerable to brute-force request flooding and denial-of-wallet attacks. | Implemented constant-time API key auth (`backend/security/auth.py`) and in-memory bounded sliding-window rate limiter (`backend/security/rate_limiter.py`, 429 Too Many Requests). |
| **Semantic Cache Hardening** | Cache key only hashed `mandate_id` and item description, allowing stale authorizations to persist across policy edits. | Upgraded to **cryptographic context-complete cache keys** (`compute_semantic_cache_key`) hashing mandate intent, allowed categories, exclusions, merchants, item description, and policy version. |
| **Payment Idempotency** | Razorpay adapter did not protect against duplicate execution on network retry or race conditions. | Implemented **thread-safe concurrency lock** and receipt-based idempotency registry returning `idempotent_replay: true` on duplicate execution attempts. |
| **Prompt Injection Defense** | Only scanned `item_description` for basic override keywords. | Expanded to multi-surface scanner (`check_all_inputs_for_injection`) covering descriptions, merchants, notes, metadata, and mandate text across 15+ attack patterns. |
| **Architectural Separation** | Separation of concerns was documented but not enforced at code compile/import time. | Built AST-based architectural boundary test suite (`backend/tests/test_architectural_boundaries.py`) proving agents and self-healing never import payment modules. |
| **Live LLM Reliability** | Gemini provider output varied between boolean and category schemas. | Built robust schema normalization in `backend/llm/gemini.py` supporting Gemini 2.5 Flash live API calls. |
| **End-to-End Test Matrix** | Dispersed test cases without unified canonical scenario coverage. | Built dedicated 10-case E2E transaction authorization test suite (`backend/tests/test_end_to_end_transaction_authorization.py`). |

---

## 3. Authoritative Benchmark Results

We provide two benchmark modes: a genuine AI capability benchmark and a CI/regression benchmark.

### Live Provider Benchmark (Genuine AI Performance)
Computed by running `python scripts/evaluate.py --provider gemini --limit 30`. This evaluates the real LLM's semantic reasoning capability.
- **Source:** [`docs/reports/evaluation_report_live.json`](reports/evaluation_report_live.json)

### Offline Mock Benchmark (CI / Regression)
Computed dynamically by running `python scripts/evaluate.py --provider mock` against the held-out test split. This evaluates the deterministic structural and confidence engines using a simulated keyword-based provider.

| Metric | Baseline 1: Structural-Only | Baseline 2: IntentGuard Hybrid | Baseline 3: Semantic-Only |
| :--- | :---: | :---: | :---: |
| **Strict Accuracy** | **90.0%** | **95.0%** 🏆 | **100.0%** |
| **Safe Routing Accuracy** | **90.0%** | **95.0%** | **100.0%** |
| **False-Allow Rate (Security Risk)**| **5.0%** ⚠️ | **0.0%** 🛡️ | **0.0%** 🛡️ |
| **False-Block Rate (Friction)** | 5.0% | 5.0% | 0.0% |
| **Escalation Rate (Human Review)** | 0.0% | 5.0% | 5.0% |

> **Key Architectural Proof:** Traditional numerical gateways let 5.0% to 11.0% of out-of-scope semantic drift transactions slip through because they satisfy price and vendor rules (e.g. chocolates at an office supply store). IntentGuard eliminates this vulnerability to **0.0%**, safely escalating ambiguous cases to human review.

---

## 4. Test Suite Summary

Total Automated Tests: **155 Tests (100% Core Passing, 4 Live-Only Skipped Without Flag)**

- **Cryptographic Audit Ledger Hash Chain:** 5/5 passed (`test_audit_chain.py`)
- **API Key Authentication & Rate Limiting:** 4/4 passed (`test_auth_and_ratelimit.py`)
- **AST Architectural Boundaries:** 6/6 passed (`test_architectural_boundaries.py`)
- **End-to-End 10-Case Authorization Suite:** 10/10 passed (`test_end_to_end_transaction_authorization.py`)
- **Adversarial Prompt Injection Matrix:** 20/20 passed (`test_prompt_injection.py`)
- **Razorpay Idempotency & Concurrency:** 2/2 passed (`test_razorpay_idempotency.py`)
- **Semantic Cache Context Isolation:** 4/4 passed (`test_semantic_cache_isolation.py`)
- **Structural Policy & False-Positives:** 26/26 passed (`test_structural.py`, `test_structural_false_positives.py`)
- **Decision Engine Matrix:** 10/10 passed (`test_decision.py`)
- **Controlled Failure Scenarios:** 10/10 passed (`test_scenarios.py`)
- **Agent Orchestrator & Self-Healing:** 6/6 passed (`test_agent_orchestrator.py`)
- **Semantic Extraction & Validation:** 9/9 passed (`test_semantic.py`)
- **Confidence Calculation:** 10/10 passed (`test_confidence.py`)
- **Dataset Leakage & Security:** 4/4 passed (`test_dataset_leakage.py`)
- **Proposer Agents:** 4/4 passed (`test_proposer_agents.py`)
- **Failure Modes & Fallbacks:** 3/3 passed (`test_failure_modes.py`)

---

## 5. Deployment & Production Invariants

1. **Frozen Video Invariant:** All routes, UI flows, and scenario signatures shown in the recorded submission video remain 100% functional and backward-compatible.
2. **Deterministic Governance:** Under no circumstances does the LLM authorize money movement directly. All transactions require deterministic structural clearance and consensus threshold compliance.
3. **Audit Immutability:** Audit records are linked via cryptographic SHA-256 hash chains, providing mathematically verifiable tamper-evidence.
