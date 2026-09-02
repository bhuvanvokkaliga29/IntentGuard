# IntentGuard — Fintech Compliance & Governance Framework

> **Document Class:** Technical Governance & Regulatory Compliance Architecture  
> **Audience:** Financial Auditors, Risk Officers, Platform Security Engineers (Razorpay Assessment)  
> **Buildathon Track:** Track 5 — Open Track (Agentic Financial Control Plane)  
> **Status:** Active / Production-Ready Baseline  

---

## 1. Executive Compliance Summary

IntentGuard is an **in-line financial authorization and semantic control plane** that prevents unauthorized, fraudulent, or scope-drifted transactions initiated by delegated autonomous AI agents.

In traditional payments, authorization checks are purely numerical (balance, amount ceiling, MCC). IntentGuard introduces **Deterministic Intent Verification**, ensuring an autonomous agent cannot spend funds outside the user's explicit semantic mandate—even if numerical rules pass.

---

## 2. Core Compliance Invariants (The "Zero-Trust" Principles)

### 2.1. Segregation of Duties (SOD)
* **Untrusted Proposers:** Autonomous agents (`BuyingAgent`, `RecommendationAgent`, `VoiceMandateAgent`) operate in a sandboxed execution boundary. They formulate transaction *proposals* only.
* **Zero Credential Possession:** Proposers possess zero payment credentials, API tokens, or direct gateway access.
* **Supervisory Enforcement:** Only the `IntentGuard Main Agent` and its deterministic policy engine can authorize settlement.

### 2.2. Deterministic Circuit Breakers (Zero-LLM Direct Authority)
* **Rule:** An LLM *never* has direct authority to approve a payment.
* **Mechanism:** 
  1. [`backend/policy/hard_constraints.py`](../backend/policy/hard_constraints.py) executes zero-LLM mathematical checks (amount ceiling, frequency limits, merchant allowlists, explicit keyword exclusions) in `<1ms`.
  2. If hard constraints fail, the transaction is immediately **BLOCKED**; LLM evaluation is bypassed entirely.
  3. LLMs are strictly bounded to probabilistic semantic fact extraction and entailment consensus.
  4. Final authorization outcomes (`ALLOW`, `BLOCK`, `ESCALATE`) are computed exclusively by a deterministic Python state matrix ([`backend/policy/decision.py`](../backend/policy/decision.py)).

### 2.3. Safe Default on Uncertainty (Fail-Closed Architecture)
* In the event of:
  * LLM provider outage or rate-limiting (`HTTP 429` / `500`)
  * Low entailment consensus score ($< 0.40$)
  * Incomplete merchant metadata / opaque SKU codes
* IntentGuard deterministically defaults to **`ESCALATE` (Human Review)**. It **never fails open** to `ALLOW`.

---

## 3. Auditability & Non-Repudiation (SOC2 / ISO 27001 Alignment)

Every transaction evaluated by IntentGuard is recorded in an immutable, append-only ledger schema:

| Field | Description | Compliance Purpose |
| :--- | :--- | :--- |
| `correlation_id` | Distributed UUID propagated across HTTP headers, FSM stages, and DB records | End-to-end request tracing across microservices |
| `decision_id` | Unique identifier for the authorization verdict | Non-repudiation and operator audit lookup |
| `mandate_id` | Cryptographic pointer to user-approved spending policy | Proof of authorization boundary |
| `structural_result` | Exact boolean output of hard constraint checks | Proof of mathematical limit enforcement |
| `semantic_samples` | Multi-sample consensus reasoning logs | Transparent AI reasoning record |
| `confidence_score` | Mathematical confidence rating ($0.0 \dots 1.0$) | Quantitative threshold verification |
| `final_decision` | `ALLOW`, `BLOCK`, or `ESCALATE` | Final authoritative gate state |
| `timestamp` | UTC ISO-8601 timestamp | Audit timeline sequencing |

---

## 4. Enterprise Secrets & Key Isolation

* **Pluggable Architecture:** Implemented in [`backend/security/secrets.py`](../backend/security/secrets.py).
* **Supported Backends:** Local environment (`.env`), **AWS Secrets Manager**, and **HashiCorp Vault** (AppRole / Token auth).
* **Zero Committed Secrets:** Repository audit verification guarantees zero API keys, private certificates, or database credentials exist in version control.

---

## 5. Architectural Decision Records (ADRs)

To ensure full transparency into engineering trade-offs, IntentGuard maintains 10 formal Architecture Decision Records in [`docs/adr/`](adr/):
* `ADR-001`: Deterministic Policy Engine vs Direct LLM Authorization
* `ADR-002`: Proposer-Authorizer Isolation Boundary
* `ADR-003`: Multi-Sample Self-Consistency for Semantic Verification
* `ADR-004`: Fail-Closed Handling for LLM Outages
* `ADR-005`: Append-Only Audit Schema with Correlation IDs

---

*Verified & Validated: IntentGuard Engineering & Compliance Architecture — Razorpay AI Buildathon 2026.*
