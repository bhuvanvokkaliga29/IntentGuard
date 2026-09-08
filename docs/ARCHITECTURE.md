# IntentGuard System Architecture — Supervisory Financial Authorization Control Plane

## 1. Executive Summary & Absolute Invariant

IntentGuard solves **P4 — Spending-Mandate Scope Drift**: preventing autonomous AI agents from executing financial transactions that appear structurally valid (amount, category, merchant) but violate the human's delegated spending intent.

### Fundamental Operating Axiom
> **"AI generates evidence. Deterministic policy controls money."**

IntentGuard is **not** a shopping agent, payment gateway, fraud detector, or recommendation engine. Autonomous proposer agents (`BuyingAgent`, `RecommendationAgent`, `VoiceMandateAgent`) remain strictly proposal-only test agents. IntentGuard is the supervisory verification, risk analysis, and authorization control plane between autonomous agents and financial execution.

```
+─────────────────────────────────────────────────────────────────────────────+
|                             HUMAN USER INTENT                               |
|   "Buy my regular office supplies up to ₹2,000 per week from our usual      |
|    stationery store."                                                       |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|               STRUCTURED MANDATE NORMALIZATION & VERSIONING                 |
|   - StructuredMandateProfile: purpose, categories, merchants, temporal      |
|   - Immutable Version Tracking: version, policy_state, previous_version_id  |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|                         AUTONOMOUS PROPOSER AGENTS                          |
|   Proposer (Buying Agent / Recommendation Agent / Voice Mandate Agent)      |
|   Tool Execution: `catalog.search`, `pricing.lookup`, `merchant.lookup`     |
|   *Operating in zero-credential sandbox with NO financial API access*       |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼ (Untrusted Transaction Proposal)
+─────────────────────────────────────────────────────────────────────────────+
|                   STAGE 1: INTAKE & SCHEMA NORMALIZATION                    |
|   - Pydantic schema validation & amount positivity bounds                   |
|   - POS/L3 raw description normalization & entity canonicalization          |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|            STAGE 2: MULTI-SURFACE ADVERSARIAL & PROMPT DEFENSE              |
|   - Recursive scanning of dictionary keys, values, and nested structures    |
|   - Unicode NFKC normalization, zero-width stripping, and homoglyph defense |
|   - Prompt injection pattern matching with 4000-char boundary enforcement   |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|               STAGE 3: STRUCTURAL & TEMPORAL HARD CONSTRAINTS               |
|   - Numerical amount limits (per-transaction and cumulative budget cap)     |
|   - Canonical merchant allowlist matching & category restrictions           |
|   - Explicit exclusion rules (e.g., gift cards, luxury goods)               |
|   - Temporal boundary verification (effective_from, effective_until, hours) |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|               STAGE 4: SEMANTIC VERIFICATION & DRIFT ENGINE                 |
|   - Fact extraction wrapped in XML prompt boundary encapsulation            |
|   - 3-sample self-consistency semantic entailment (LLM abstraction layer)   |
|   - Dedicated Semantic Drift Engine (9 taxonomical drift classifications)   |
|   - Context-complete Bounded LRU Semantic Cache                             |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|                    STAGE 5: CONTEXTUAL INTELLIGENCE LAYER                   |
|   - Novelty Detection: unseen merchant, unseen category, amount spike       |
|   - Behavioral Baseline: spend distribution and deviation score             |
|   - Temporal Context: business hours, operational days, validity window     |
|   - Agent Trust & Identity: sandboxed agent capabilities and trust score    |
|   - Multi-Agent Consensus: cross-verification divergence detection          |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                                       ▼
+─────────────────────────────────────────────────────────────────────────────+
|             STAGE 6: MULTI-SIGNAL RISK AGGREGATION & POLICY ENGINE          |
|   - Multi-dimensional risk scoring (structural, drift, novelty, agent)      |
|   - Confidence computation (self-consistency agreement & completeness)     |
|   - Deterministic Decision Matrix (ALLOW | BLOCK | ESCALATE)                |
+──────────────────────────────────────┬──────────────────────────────────────+
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
+─────────────────────────────────────+ +─────────────────────────────────────+
|    STAGE 7: TAMPER-EVIDENT AUDIT    | |      STAGE 8: AUTHORITATIVE GATE    |
|   - Sequential sequence_number      | |  - Strictly requires 'ALLOW'        |
|   - SHA-256 hash chaining           | |  - BLOCK/ESCALATE NEVER execute     |
|   - Human review transition audit   | |  - Thread-safe idempotency registry |
|   - Decision Replay reproducibility | |  - Razorpay Gateway adapter         |
+─────────────────────────────────────+ +─────────────────────────────────────+
```

---

## 2. Detailed Pipeline Stages

### Stage 1: Proposal Intake & Normalization
- Schema validation via `TransactionProposalCreate` (strictly enforces positive numerical amounts, non-empty descriptions, and ISO-8601 timestamps).
- Enriches POS Level-1 abbreviations (e.g. `AMZN MKTP -> amazon.in`, `SQ *COFFEE -> Square Merchant`) into canonical merchant identities without modifying authorization constraints.

### Stage 2: Adversarial & Multi-Surface Defense
- Recursive scanning across all untrusted payload surfaces (keys, values, nested JSON structures, headers).
- Unicode NFKC normalization and zero-width character cloaking removal (`\u200b`, `\u200c`, `\u200d`, `\ufeff`).
- Hardened regex detection blocking instruction overrides, prompt injections, authority spoofing ("pre-approved by CFO"), and sandbox escape tokens.
- Buffer-exhaustion defense capping untrusted input at 4,000 characters.

### Stage 3: Structural & Temporal Verification (Pure Deterministic Python)
- **Per-Transaction Limits:** Checks proposed amount against mandate `max_amount_per_txn`.
- **Cumulative Budget Cap:** Tracks spent amount against `budget_cap`.
- **Allowed Merchants & Categories:** Canonical matching against allowlists.
- **Exclusion Filters:** Deterministic substring filtering on prohibited items (e.g., alcohol, gift cards, luxury goods).
- **Temporal Authorization:** Verifies proposal timestamp against `effective_from`, `effective_until`, operational days, and business hours.
- **Fast-Path BLOCK:** If any structural or temporal constraint fails, the pipeline skips LLM inference entirely and renders `BLOCK`.

### Stage 4: Semantic Verification & Dedicated Drift Engine
- **XML Boundary Encapsulation:** Untrusted strings are encapsulated in `<untrusted_transaction_data>` tags to prevent delimiter injection.
- **Structured Fact Extraction:** LLM extracts normalized item nature, intended function, and consumables classification.
- **Multi-Sample Entailment:** Generates $N=3$ independent semantic verdicts (`fit`, `no_fit`, `ambiguous`) with self-consistency agreement scoring.
- **Semantic Drift Engine (`backend/semantic/drift.py`):**
  Classifies transactions into 9 specific drift categories:
  1. `aligned`: Transaction directly satisfies human intent.
  2. `partially_aligned`: Peripheral or borderline fit.
  3. `ambiguous`: Insufficient clarity or contradictory purpose.
  4. `outside_mandate`: Unrelated domain or utility.
  5. `purpose_substitution`: Displacing intended utility with unauthorized utility (e.g., buying a gaming laptop under stationery).
  6. `category_drift`: Shifting spending into adjacent unapproved categories.
  7. `contextual_drift`: Deviating from the business context or organizational mission.
  8. `merchant_purpose_mismatch`: Merchant capability contradicts the stated item purpose.
  9. `suspicious_justification`: Explanations using evasive language or spoofed authorization.

### Stage 5: Contextual Intelligence Subsystem
- **Novelty Engine (`backend/context/novelty.py`):** Flags unseen merchants, novel categories, and amount spikes compared to historical transactions under the mandate.
- **Behavioral Baseline (`backend/context/behavioral_baseline.py`):** Tracks statistical baseline metrics (mean spend, standard deviation, velocity) to produce an anomaly deviation score.
- **Temporal Engine (`backend/context/temporal.py`):** Evaluates validity windows and active schedules.
- **Agent Trust Context (`backend/context/agent_context.py`):** Identifies the proposing agent, its operational tier, capabilities, and historical reliability.
- **Multi-Agent Consensus (`backend/context/multi_agent.py`):** Evaluates cross-agent consensus when multiple proposers analyze or propose for the same mandate.

### Stage 6: Deterministic Policy Engine & Multi-Signal Risk
- Combines structural results, semantic drift, contextual novelty, and agent trust into a unified risk profile.
- Renders final deterministic verdict:
  - `ALLOW`: Structural PASS + Semantic `fit` + High Confidence ($\ge 0.85$) + No Critical Drift.
  - `BLOCK`: Structural FAIL, OR Security Violation, OR Semantic `no_fit` + High Confidence.
  - `ESCALATE`: Ambiguous semantic verdict, low confidence ($< 0.70$), or significant contextual anomaly.

### Stage 7: Tamper-Evident SHA-256 Audit Ledger
- Appends every decision, human review transition, and system recovery to an unbroken SHA-256 cryptographic chain (`AuditLogRow`).
- Stores sequence numbers, timestamps, previous hashes, current hashes, and the complete evaluation dossier.
- Validated via `GET /audit/chain/verify`.

### Stage 8: Authoritative Execution Boundary Gate
- **Single Execution Path:** Payment orders are dispatched to Razorpay ONLY through `stage_guard_execution_boundary`.
- `BLOCK` and `ESCALATE` decisions are strictly rejected with status `BLOCKED_BY_GUARDRAIL`.
- Thread-safe idempotency registry prevents double-spending or concurrent settlement races.

---

## 3. Subsystem Directory Mapping

| Subsystem | Key Files & Modules | Core Responsibilities |
| :--- | :--- | :--- |
| **API Control Plane** | `backend/main.py` | FastAPI application, OpenAPI documentation, routing, lifecycle management |
| **Mandate Management** | `backend/semantic/mandate_interpreter.py`, `backend/db.py` | Structured mandate extraction, version lineage, CRUD |
| **Adversarial Defense** | `backend/security/prompt_defense.py`, `backend/security/red_team.py` | Prompt injection detection, input normalization, 17+ vector red-team suite |
| **Structural Policy** | `backend/policy/hard_constraints.py` | Deterministic constraints (amounts, budgets, categories, merchants, exclusions) |
| **Semantic Drift** | `backend/semantic/drift.py`, `backend/semantic/cache.py` | 9-category drift engine, structured evidence, bounded LRU cache |
| **Contextual Intelligence** | `backend/context/` (`novelty.py`, `behavioral_baseline.py`, `temporal.py`, `agent_context.py`, `multi_agent.py`) | Historical novelty, spending baseline, temporal validity, agent trust, consensus |
| **Policy Versioning & Replay**| `backend/policy/versioning.py`, `backend/policy/replay.py` | Policy snapshots, configuration hash, deterministic decision reconstruction |
| **Human Review & Learning** | `backend/db.py` (`update_decision_review`), `backend/evaluation/learning_loop.py` | Reviewer action audit trail, offline evaluation set collection |
| **Execution Boundary** | `backend/orchestrator/pipeline.py`, `backend/execution/razorpay_gateway.py` | Single authoritative gate, thread-safe idempotency, Razorpay adapter |
| **Audit & Storage** | `backend/db.py` (`AuditLogRow`, `verify_audit_chain`) | Cryptographic SHA-256 hash chaining, SQLite/PostgreSQL support |
| **Proposer Agents (Test Only)**| `backend/agent/proposer_*.py` | Sandboxed proposal generators (`BuyingAgent`, `RecommendationAgent`, `VoiceMandateAgent`) |
