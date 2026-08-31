# IntentGuard — Code Path & Source Traceability

This document maps every architectural subsystem to its exact implementation file and test verification suite.

---

## 1. System Code Directory Mapping

| Subsystem Component | Implementation File(s) | Primary Purpose | Test Verification |
| :--- | :--- | :--- | :--- |
| **Deterministic Structural Rules** | [`backend/policy/hard_constraints.py`](../backend/policy/hard_constraints.py) | Zero-LLM math checks (budget cap, per-txn limit, allowlists, exclusions) | [`backend/tests/test_structural.py`](../backend/tests/test_structural.py), [`test_structural_false_positives.py`](../backend/tests/test_structural_false_positives.py) |
| **Fact Extraction & Semantic Judgment** | [`backend/semantic/extract.py`](../backend/semantic/extract.py), [`backend/semantic/judgment.py`](../backend/semantic/judgment.py) | Structured evidence extraction and multi-sample self-consistency entailment | [`backend/tests/test_semantic.py`](../backend/tests/test_semantic.py) |
| **Mathematical Confidence Engine** | [`backend/policy/confidence.py`](../backend/policy/confidence.py) | Agreement rate derivation, proximity penalties, confidence bounding | [`backend/tests/test_confidence.py`](../backend/tests/test_confidence.py) |
| **Deterministic Decision Engine** | [`backend/policy/decision.py`](../backend/policy/decision.py) | Authoritative decision matrix (`ALLOW`, `BLOCK`, `ESCALATE`) | [`backend/tests/test_decision.py`](../backend/tests/test_decision.py), [`test_critical_invariants.py`](../backend/tests/test_critical_invariants.py) |
| **Multi-Provider LLM Integration** | [`backend/llm/gemini.py`](../backend/llm/gemini.py), [`backend/llm/grok.py`](../backend/llm/grok.py), [`backend/llm/provider.py`](../backend/llm/provider.py) | Abstracted JSON-schema bound interface to Google Gemini & xAI Grok | [`backend/tests/test_prompt_injection.py`](../backend/tests/test_prompt_injection.py) |
| **Proposer Agents (Untrusted)** | [`backend/agent/proposer_buying.py`](../backend/agent/proposer_buying.py), [`backend/agent/proposer_recommendation.py`](../backend/agent/proposer_recommendation.py), [`backend/agent/proposer_voice.py`](../backend/agent/proposer_voice.py) | Proposer agents exploring catalogs with zero execution authority | [`backend/tests/test_proposer_agents.py`](../backend/tests/test_proposer_agents.py) |
| **Agent Orchestrator & State Machine** | [`backend/orchestrator/orchestrator.py`](../backend/orchestrator/orchestrator.py), [`backend/orchestrator/state_machine.py`](../backend/orchestrator/state_machine.py) | 9-stage state machine controlling agent lifecycle and IntentGuard handoffs | [`backend/tests/test_agent_orchestrator.py`](../backend/tests/test_agent_orchestrator.py) |
| **Self-Healing Fault Recovery** | [`backend/agent/self_healing.py`](../backend/agent/self_healing.py) | Automated fault classification and recovery | [`backend/tests/test_agent_orchestrator.py`](../backend/tests/test_agent_orchestrator.py) |
| **Append-Oriented Audit Ledger** | [`backend/db.py`](../backend/db.py), [`backend/models.py`](../backend/models.py) | Structured audit records and transaction history | [`backend/tests/test_dataset_leakage.py`](../backend/tests/test_dataset_leakage.py) |
| **Authoritative Benchmark Runner** | [`scripts/evaluate.py`](../scripts/evaluate.py) | Benchmark runner computing all evaluation metrics dynamically | [`docs/reports/evaluation_report.json`](reports/evaluation_report.json) |

---

## 2. Execution Call Trace (End-to-End Request Path)

```text
HTTP POST /api/evaluate (backend/main.py)
   │
   ├─► 1. Load Mandate & Transaction (backend/db.py)
   │
   ├─► 2. check_hard_constraints() (backend/policy/hard_constraints.py)
   │      └─► If FAIL ──► Deterministic BLOCK (Zero LLM invoked)
   │
   ├─► 3. extract_structured_facts() [LLM Call 1] (backend/semantic/extract.py)
   │      └─► Bound by ExtractedFacts Pydantic Schema
   │
   ├─► 4. semantic_compare() [LLM Call 2 x 3 Samples] (backend/semantic/judgment.py)
   │      └─► Multi-sample self-consistency sampling
   │
   ├─► 5. compute_confidence() (backend/policy/confidence.py)
   │      └─► Pure deterministic mathematical calculation
   │
   ├─► 6. decide() (backend/policy/decision.py)
   │      └─► Deterministic Decision: ALLOW | BLOCK | ESCALATE
   │
   ├─► 7. generate_explanation() (backend/agent/tools.py)
   │      └─► Human-readable rationale grounded in evidence
   │
   └─► 8. record_audit_log() (backend/db.py)
          └─► Tamper-evident structured audit record persisted
```
