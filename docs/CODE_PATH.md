# IntentGuard Code Path Trace

This document provides a line-by-line, source-referenced trace of a transaction proposal traveling through the IntentGuard control plane.

## 1. Request Initiation
- **Endpoint**: `POST /agents/orchestrator/execute` in [`backend/main.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/main.py)
- **Controller**: Calls `orchestrator.run_buying_agent(mandate_id, objective, injected_failure)` in [`backend/orchestrator/orchestrator.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/orchestrator/orchestrator.py).

## 2. Agent State Machine Progression
1. **`INITIALIZING`**: Creates `AgentRunRow` in DB (`backend/db.py`) and publishes `agent.started` event over Event Bus (`backend/orchestrator/event_bus.py`).
2. **`READING_CONTEXT`**: Reads `MandateRow` using `tool_get_mandate()` and normalizes structural constraints.
3. **`PLANNING`**: Formulates search objective (e.g. `BEST_RATING`).
4. **`TOOL_CALL`**: Executes `catalog.search` via `AgentToolRegistry.execute_tool()` in [`backend/agent/tools.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/agent/tools.py).
5. **`OBSERVING`**: Filters and sorts candidates into short-term bounded run memory (`BoundedRunMemory`).
6. **`EVALUATING_OPTIONS`**: Selects candidate item (e.g. ₹1,950 Chocolates from Stationery Mart).
7. **`GENERATING_PROPOSAL`**: Packages `TransactionProposal` payload.
8. **`VALIDATING_PROPOSAL`**: Pre-validates schema syntax via `transaction.validate` tool.
9. **`SUBMITTING_TO_INTENTGUARD`**: Submits proposal payload to the IntentGuard Gateway.

## 3. IntentGuard Control Plane Execution
- **Gateway Entry**: `evaluate_transaction()` in [`backend/orchestrator/evaluator.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/orchestrator/evaluator.py) calls `run_evaluation_pipeline()` in [`backend/agent/agent.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/agent/agent.py).
- **Step 1: Structural Check**: `check_hard_constraints()` in [`backend/policy/hard_constraints.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/policy/hard_constraints.py).
  - Amount: ₹1,950 $\le$ ₹2,000 $\rightarrow$ **PASS**
  - Merchant: Stationery Mart $\in$ Allowed $\rightarrow$ **PASS**
- **Step 2: Fact Extraction (LLM Call 1)**: `extract_facts()` in [`backend/semantic/extraction.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/semantic/extraction.py) via `LLMProvider.structured_extract()`.
  - Parsed: `category="food_confectionery"`, `item_type="chocolates"`.
- **Step 3: Multi-Sample Entailment (LLM Call 2 $\times$ 3)**: `semantic_compare()` in [`backend/semantic/entailment.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/semantic/entailment.py).
  - Sample 1: `no_fit`
  - Sample 2: `no_fit`
  - Sample 3: `no_fit`
  - Majority Verdict: `no_fit` (Agreement: 1.0)
- **Step 4: Confidence Scoring**: `compute_confidence()` in [`backend/policy/confidence.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/policy/confidence.py).
  - Score: $1.0$ (High confidence).
- **Step 5: Deterministic Decision**: `decide()` in [`backend/policy/decision.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/policy/decision.py).
  - Decision: **`FLAG` / `BLOCK`**
  - Reason: `structural_pass + semantic_no_fit + high_confidence -> BLOCK`
- **Step 6: Explanation Generation**: `generate_explanation()` in [`backend/policy/explanation.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/policy/explanation.py).
- **Step 7: Audit Persistence**: `create_decision()` and `create_audit_log()` in [`backend/db.py`](file:///c:/Users/HP/Desktop/IntentGuard/backend/db.py).

## 4. Telemetry Broadcast
- `intentguard.decision.created` event emitted over `GET /agents/stream` (SSE).
- Frontend live console updates with FSM completion and human review flag.
