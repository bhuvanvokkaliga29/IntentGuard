# IntentGuard — Component Traceability Matrix

This matrix establishes 100% concrete source-code traceability for every component across all architectural zones. There are no imaginary or unmapped boxes.

---

## 1. Architectural Component Mapping

| Architecture Component | Source File | Core Function / Class | API Endpoint | DB Model / Table | Test Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mandate Normalizer** | [`backend/agent/proposer_voice.py`](../../backend/agent/proposer_voice.py) | `VoiceMandateAgent.parse_intent()` | `POST /mandates/parse-voice` | `MandateRow` (`mandates`) | [`test_proposer_agents.py`](../../backend/tests/test_proposer_agents.py) |
| **Structural Policy Engine** | [`backend/policy/hard_constraints.py`](../../backend/policy/hard_constraints.py) | `check_hard_constraints()` | Internal Pipeline Call | N/A (Pure Python) | [`test_structural.py`](../../backend/tests/test_structural.py), [`test_structural_false_positives.py`](../../backend/tests/test_structural_false_positives.py) |
| **Fact Extractor (LLM 1)** | [`backend/semantic/extract.py`](../../backend/semantic/extract.py) | `extract_facts()` | Internal Pipeline Call | `ExtractedFacts` (Schema) | [`test_semantic.py`](../../backend/tests/test_semantic.py) |
| **Semantic Verifier (LLM 2)**| [`backend/semantic/judgment.py`](../../backend/semantic/judgment.py) | `judge_semantic_fit()` | Internal Pipeline Call | `SemanticJudgmentResult` | [`test_semantic.py`](../../backend/tests/test_semantic.py) |
| **Mathematical Confidence** | [`backend/policy/confidence.py`](../../backend/policy/confidence.py) | `compute_confidence()` | Internal Pipeline Call | N/A (Pure Python) | [`test_confidence.py`](../../backend/tests/test_confidence.py) |
| **Deterministic Decision Engine** | [`backend/policy/decision.py`](../../backend/policy/decision.py) | `decide()` | `POST /api/evaluate` | `DecisionRow` (`decisions`) | [`test_decision.py`](../../backend/tests/test_decision.py), [`test_critical_invariants.py`](../../backend/tests/test_critical_invariants.py) |
| **Explanation Generator** | [`backend/agent/tools.py`](../../backend/agent/tools.py) | `tool_generate_explanation()` | Part of decision payload | `DecisionRow.explanation` | [`test_e2e_integration.py`](../../backend/tests/test_e2e_integration.py) |
| **Cryptographic Tamper-Evident Audit Chain** | [`backend/db.py`](../../backend/db.py) | `create_audit_log()`, `create_decision()` | `GET /audit/{decision_id}` | `AuditLogRow` (`audit_logs`) | [`test_dataset_leakage.py`](../../backend/tests/test_dataset_leakage.py) |
| **Buying Agent (Untrusted Proposer)** | [`backend/agent/proposer_buying.py`](../../backend/agent/proposer_buying.py) | `BuyingAgent.propose_transaction()` | `POST /agents/buying/propose` | `TransactionRow` | [`test_proposer_agents.py`](../../backend/tests/test_proposer_agents.py) |
| **Recommendation Agent (Untrusted Proposer)** | [`backend/agent/proposer_recommendation.py`](../../backend/agent/proposer_recommendation.py) | `RecommendationAgent.generate_recommendation()` | `POST /agents/recommendation/propose` | `TransactionRow` | [`test_proposer_agents.py`](../../backend/tests/test_proposer_agents.py) |
| **Agent Orchestrator** | [`backend/orchestrator/orchestrator.py`](../../backend/orchestrator/orchestrator.py) | `AgentOrchestrator.run_buying_agent()` | `POST /agents/orchestrator/execute` | `AgentRunRow` (`agent_runs`) | [`test_agent_orchestrator.py`](../../backend/tests/test_agent_orchestrator.py) |
| **Self-Healing Fault Recovery** | [`backend/agent/self_healing.py`](../../backend/agent/self_healing.py) | `SelfHealingEngine.execute_recovery()` | Internal Orchestrator Call | `SelfHealingEventRow` | [`test_agent_orchestrator.py`](../../backend/tests/test_agent_orchestrator.py), [`test_chaos.py`](../../backend/tests/test_chaos.py) |
| **Live Telemetry Event Bus** | [`backend/orchestrator/event_bus.py`](../../backend/orchestrator/event_bus.py) | `EventBus.publish()` | `GET /agents/stream` (SSE) | Memory Ring Buffer | [`test_agent_orchestrator.py`](../../backend/tests/test_agent_orchestrator.py) |
| **Prometheus Exporter** | [`backend/metrics.py`](../../backend/metrics.py) | `generate_prometheus_output()` | `GET /metrics` | In-memory counters | [`test_production_readiness.py`](../../backend/tests/test_production_readiness.py) |
| **Execution Gateway (Sandbox)** | [`backend/orchestrator/evaluator.py`](../../backend/orchestrator/evaluator.py) | `evaluate_transaction()` | Execution Boundary Handoff | N/A (Simulated Gateway) | [`test_critical_invariants.py`](../../backend/tests/test_critical_invariants.py) |
| **Benchmark Runner** | [`scripts/evaluate.py`](../../scripts/evaluate.py) | `run_evaluation()` | CLI (`python scripts/evaluate.py`) | `docs/reports/evaluation_report.json` | [`docs/reports/evaluation_report.json`](../reports/evaluation_report.json) |

---

## 2. Invariant Verification Mapping

- **Proposer Isolation Invariant:** Proposers hold zero payment credentials ([`test_critical_invariants.py:test_invariant_1`](../../backend/tests/test_critical_invariants.py)).
- **Zero-LLM Direct Authorization Invariant:** LLM output is parsed as untrusted semantic evidence ([`test_critical_invariants.py:test_invariant_2`](../../backend/tests/test_critical_invariants.py)).
- **Fail-Safe Escalation Invariant:** Missing facts or low confidence force `ESCALATE` ([`test_critical_invariants.py:test_invariant_3`](../../backend/tests/test_critical_invariants.py)).
- **Self-Healing Boundary Invariant:** Self-healing engine possesses no references or methods to modify mandates or budget caps ([`test_chaos.py`](../../backend/tests/test_chaos.py)).
