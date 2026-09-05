# IntentGuard System Architecture

## 1. System Overview
IntentGuard is a working financial control platform with a production-oriented supervisory architecture sitting between autonomous transaction-proposing AI agents and financial execution systems.

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
|   *Operating in zero-credential sandbox with NO financial API access*   |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                                     ▼ (Untrusted Transaction Proposal)
+─────────────────────────────────────────────────────────────────────────+
|                 1. MULTI-SURFACE PROMPT-INJECTION DEFENSE               |
|   - Recursive scanning of dictionary keys, values, and nested lists     |
|   - Unicode NFKC normalization and zero-width cloaking removal          |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                                     ▼
+─────────────────────────────────────────────────────────────────────────+
|                     2. INTENTGUARD VERIFICATION PIPELINE                |
|                                                                         |
|  ┌───────────────────────────────┐     ┌─────────────────────────────┐  |
|  │    STRUCTURAL HARD POLICY     │     │    SEMANTIC VERIFICATION    │  |
|  │  - Amount <= Budget limit     │     │  - Bounded LRU Cache Check  │  |
|  │  - Canonical Merchant Match   │     │  - Fact Extraction (LLM)    │  |
|  │  - Category Allowlist/Block   │     │  - 3-Sample Entailment (LLM)│  |
|  └───────────────┬───────────────┘     └──────────────┬──────────────┘  |
|                  │                                    │                 |
|                  └──────────────────┬─────────────────┘                 |
|                                     ▼                                   |
|                  ┌─────────────────────────────────────┐                |
|                  │  CONFIDENCE & EVIDENCE AGGREGATION  │                |
|                  │  Agreement + Completeness + Boundary│                |
|                  └──────────────────┬──────────────────┘                |
|                                     ▼                                   |
|                  ┌─────────────────────────────────────┐                |
|                  │    DETERMINISTIC DECISION MATRIX    │                |
|                  │     (ALLOW | BLOCK | ESCALATE)      │                |
|                  └──────────────────┬──────────────────┘                |
+─────────────────────────────────────┼───────────────────────────────────+
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
+────────────────────────────────────+ +─────────────────────────────────+
| 3. CRYPTOGRAPHIC TAMPER-EVIDENT    | |    4. LIVE PIPELINE TELEMETRY   |
|    AUDIT CHAIN                     | |  - 8-Stage Pipeline Telemetry   |
|  - Cryptographic SHA-256 Hash Chain| |  - Observable SSE Browser Stream|
|  - Decision & Human Review Records | |  - Real-time reasoning summaries|
|  - Tamper-evident via /verify      | |                                 |
+──────────────────┬─────────────────+ +─────────────────────────────────+
                   │
                   ▼
+─────────────────────────────────────────────────────────────────────────+
|                    5. AUTHORITATIVE EXECUTION BOUNDARY                  |
|   - Strictly requires decision == 'ALLOW'                               |
|   - BLOCK and ESCALATE decisions NEVER reach financial execution        |
|   - Thread-safe idempotency registry prevents duplicate execution       |
+────────────────────────────────────┬────────────────────────────────────+
                                     │
                                     ▼
+─────────────────────────────────────────────────────────────────────────+
|                         6. FINANCIAL ADAPTER                            |
|   - RazorpayGateway (Razorpay Live / Test / Mock Adapter)               |
|   - Transparent credential masking and mode reporting                   |
+─────────────────────────────────────────────────────────────────────────+
```

## 2. Component Directory Mapping
- **Mandate Management**: `backend/db.py` (`MandateRow`, `get_mandate`)
- **Agent Orchestrator**: `backend/orchestrator/orchestrator.py` (`AgentOrchestrator`)
- **Pipeline Execution**: `backend/orchestrator/pipeline.py` (`run_evaluation_pipeline`)
- **Authoritative Execution Boundary**: `backend/orchestrator/pipeline.py` (`stage_guard_execution_boundary`), `backend/execution/razorpay_gateway.py` (`RazorpayGateway`)
- **Agent State Machine**: `backend/orchestrator/state_machine.py` (`AgentStage`, `AgentStatus`)
- **Tool System**: `backend/agent/tools.py` (`AgentToolRegistry`)
- **Self-Healing Engine**: `backend/agent/self_healing.py` (`SelfHealingEngine`)
- **Hard Constraints & Merchant Normalization**: `backend/policy/hard_constraints.py` (`check_hard_constraints`, `normalize_merchant_canonical`)
- **Bounded Semantic LRU Cache**: `backend/semantic/cache.py` (`BoundedSemanticCache`)
- **Multi-Surface Prompt Defense**: `backend/security/prompt_defense.py` (`check_all_inputs_for_injection`, `inspect_structure_recursively`)
- **Semantic Verification**: `backend/semantic/` (`extraction.py`, `entailment.py`)
- **LLM Abstraction**: `backend/llm/` (`provider.py`, `gemini.py`, `grok.py`)
- **Confidence Engine**: `backend/policy/confidence.py` (`compute_confidence`)
- **Deterministic Policy**: `backend/policy/decision.py` (`decide`)
- **Cryptographic Audit Ledger**: `backend/db.py` (`AuditLogRow`, `verify_audit_chain`, `update_decision_review`)
- **Async Task Subsystem**: `backend/tasks.py` (`AsyncTaskRow`, `create_task`, `get_task`), `backend/main.py` (`/tasks/evaluate`, `/tasks/{task_id}`)
- **Live Telemetry & SSE**: `backend/orchestrator/event_bus.py`, `backend/orchestrator/pipeline.py` (`emit_pipeline_event`)

## 3. Authoritative Architectural Invariants
1. **Single Authoritative Execution Path:**
   `API -> IntentGuard verification -> deterministic decision -> execution boundary -> financial adapter`
   Payment execution logic exists in exactly ONE place: `stage_guard_execution_boundary`. API routers and controllers do not independently initiate fund movement.
2. **Deterministic Governance:** Under no circumstances does the LLM authorize money movement directly. All transactions require deterministic structural clearance and consensus threshold compliance.
3. **Audit Tamper-Evidence:** All decisions and human review actions append to an unbroken SHA-256 cryptographic chain.
4. **Cache Policy Invalidation:** Any mutation or deletion of a spending mandate deterministically invalidates all matching cache entries, guaranteeing that stale cached `ALLOW` decisions cannot persist across policy updates.
