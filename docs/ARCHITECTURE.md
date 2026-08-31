# IntentGuard System Architecture

## 1. System Overview
IntentGuard is a semantic authorization and control layer sitting between autonomous transaction-proposing AI agents and financial execution systems.

```
+─────────────────────────────────────────────────────────────────────────+
|                             USER INTENT                                 |
|   "Buy my regular office supplies up to ₹2,000 per week from our usual  |
|    stationery store."                                                   |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                                     ▼
+─────────────────────────────────────────────────────────────────────────+
|                        MANDATE NORMALIZATION                            |
|   max_amount: 2000.0 | category: stationery | vendor: Stationery Mart   |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                                     ▼
+─────────────────────────────────────────────────────────────────────────+
|                          AUTONOMOUS AGENT                               |
|   Proposer (Buying Agent / Recommendation Agent / Voice Mandate Agent)  |
|   Tool Execution: `catalog.search`, `pricing.lookup`, `merchant.lookup` |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                                     ▼ (Transaction Proposal)
+─────────────────────────────────────────────────────────────────────────+
|                      INTENTGUARD PROPOSAL GATEWAY                       |
|   Entry Point: evaluate_proposal(proposal, mandate)                     |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
+───────────────────────────────────+ +───────────────────────────────────+
|         STRUCTURAL POLICY         | |       SEMANTIC VERIFIER (LLM)     |
|   - Amount <= ₹2,000              | |   - Structured Fact Extraction    |
|   - Merchant in Allowlist         | |   - Multi-Sample Entailment (3x)  |
|   - Category Match                | |   - Untrusted Data Isolation      |
+─────────────────┬─────────────────+ +─────────────────┬─────────────────+
                  │                                     │
                  └──────────────────┬──────────────────┘
                                     ▼
+─────────────────────────────────────────────────────────────────────────+
|                 CONFIDENCE & EVIDENCE AGGREGATION                       |
|   Agreement rate + Evidence completeness + Boundary proximity           |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                                     ▼
+─────────────────────────────────────────────────────────────────────────+
|                    DETERMINISTIC DECISION ENGINE                        |
|   Matrix: ALLOW | FLAG (Human Approval) | BLOCK | ESCALATE             |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
+───────────────────────────────────+ +───────────────────────────────────+
|      IMMUTABLE AUDIT LEDGER       | |       LIVE SSE TELEMETRY          |
|   - Policy & Prompt Version       | |   - Real-time Browser Stream      |
|   - Full Trace & Evidence Record  | |   - Observable Reasoning Summary  |
+───────────────────────────────────+ +───────────────────────────────────+
```

## 2. Component Directory Mapping
- **Mandate Management**: `backend/db.py` (`MandateRow`, `get_mandate`)
- **Agent Orchestrator**: `backend/orchestrator/orchestrator.py` (`AgentOrchestrator`)
- **Agent State Machine**: `backend/orchestrator/state_machine.py` (`AgentStage`, `AgentStatus`)
- **Tool System**: `backend/agent/tools.py` (`AgentToolRegistry`)
- **Self-Healing Engine**: `backend/agent/self_healing.py` (`SelfHealingEngine`)
- **Hard Constraints**: `backend/policy/hard_constraints.py` (`check_hard_constraints`)
- **Semantic Verification**: `backend/semantic/` (`extraction.py`, `entailment.py`)
- **LLM Abstraction**: `backend/llm/` (`provider.py`, `gemini.py`, `grok.py`)
- **Confidence Engine**: `backend/policy/confidence.py` (`compute_confidence`)
- **Deterministic Policy**: `backend/policy/decision.py` (`decide`)
- **Audit & Telemetry**: `backend/orchestrator/event_bus.py`, `backend/db.py`
