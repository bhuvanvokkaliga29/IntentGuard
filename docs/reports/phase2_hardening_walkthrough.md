# IntentGuard — Phase 2 Forensic Hardening Walkthrough

## Summary of Completed Hardening Pass

All 16 high-value findings from the Phase-1 forensic audit have been implemented, verified against the running codebase, and validated through extensive automated test suites.

---

## Changes Implemented by Domain

### 1. Human Review Audit Integrity (`backend/db.py`)
- Added dedicated, cryptographically chained `AuditLogRow` on every human review action (`APPROVED`, `REJECTED`, `REQUEST_MORE_INFO`).
- Explicitly links:
  - Original decision ID
  - Proposal/transaction ID
  - Mandate ID
  - Reviewer action and reviewer identity
  - Previous and new decision state
  - Correlation ID and timestamp
- Migrated `DecisionRow.reviewer_id` column dynamically in `init_db()`.
- Validated with `test_invariant_9_human_review_actions_are_audited_and_chained`.

### 2. Bounded Semantic LRU Cache (`backend/semantic/cache.py`)
- Replaced in-memory dictionary with thread-safe (`threading.RLock`) `BoundedSemanticCache` backed by `collections.OrderedDict`.
- Configurable maximum capacity (default: 500 entries) with deterministic LRU eviction.
- Tracks hit, miss, eviction, and invalidation counters.
- Supports deterministic mandate invalidation via `cache.invalidate_mandate(mandate_id)`.
- Integrated into `SemanticVerificationAgent` in `backend/agent/agent.py`.
- Validated with 6 unit tests in `backend/tests/test_bounded_semantic_cache.py`.

### 3. Multi-Surface Prompt-Injection Defense (`backend/security/prompt_defense.py`)
- Extended scanner with `inspect_structure_recursively(...)` to recursively inspect dictionary **KEYS**, values, nested lists, and metadata structures.
- Detects adversarial keys such as `SYSTEM_OVERRIDE`, `admin_override`, `grant_authorization`, `bypass_intentguard`.
- Strips zero-width cloaking characters and normalizes Unicode via NFKC before regex matching.
- Validated with 5 unit tests in `backend/tests/test_multi_surface_defense.py`.

### 4. Unified Execution Path (`backend/orchestrator/pipeline.py`, `backend/main.py`)
- Refactored payment execution so that `stage_guard_execution_boundary` in `pipeline.py` is the SINGLE authoritative execution gate.
- Removed duplicated `gateway.create_order` calls in `backend/main.py` (`/proposals/evaluate`, `/decisions/evaluate`, `/agents/simulate`) and `backend/orchestrator/orchestrator.py`.
- Strictly validates `decision == "ALLOW"` before invoking financial adapter.
- Validated with 5 unit tests in `backend/tests/test_unified_execution_path.py`.

### 5. Live Pipeline Telemetry (`backend/orchestrator/pipeline.py`)
- Added structured telemetry events (`emit_pipeline_event(...)`) across all 8 pipeline stages:
  1. `pipeline.proposal.received`
  2. `pipeline.normalization.completed`
  3. `pipeline.structural_check.completed`
  4. `pipeline.semantic_verification.completed`
  5. `pipeline.confidence.calculated`
  6. `pipeline.decision.evaluated`
  7. `pipeline.audit.written`
  8. `pipeline.execution_boundary.evaluated`
- Wired directly to `AgentEventBus` for live SSE consumers.
- Validated with `backend/tests/test_pipeline_telemetry.py`.

### 6. Async Task Routes (`backend/main.py`)
- Exposed clean FastAPI schemas for async task processing:
  - `POST /tasks/evaluate` (202 Accepted with polling URL)
  - `GET /tasks/{task_id}` (Returns status, elapsed time, and result)
- Backed by `AsyncTaskRow` and `backend/tasks.py`.
- Validated with `backend/tests/test_async_tasks.py`.

### 7. Canonical Merchant Normalization (`backend/policy/hard_constraints.py`)
- Implemented `normalize_merchant_canonical(name: str)` supporting corporate forms: `Pvt Ltd`, `Private Limited`, `Ltd`, `Limited`, `LLC`, `Inc`, `Corp`.
- Strictly avoids loose fuzzy matching (e.g., prevents "ABC" matching "ABC Electronics").
- Validated with `backend/tests/test_merchant_normalization.py`.

### 8. Execution Adapter Safety (`backend/execution/razorpay_gateway.py`)
- Explicit execution mode reporting: `LIVE_RAZORPAY`, `TEST_MODE`, `MOCK_ADAPTER`.
- Added masked `__repr__` and `__str__` to prevent credential leakage into logs.
- Gateway `create_order` independently rejects non-`ALLOW` decisions.
- Validated with `backend/tests/test_razorpay_gateway_modes.py`.

### 9. Critical Authorization Invariants
- 11 formal invariant tests in `backend/tests/test_hardened_invariants.py` passing 100%.

---

## Test Results

- **Backend Tests:** 194 PASSED, 4 skipped (live LLM tests requiring live paid credentials), 1 warning (SQLAlchemy teardown).
- **Frontend Tests:** 7 PASSED (Vitest).
- **Total Tests:** 201 PASSED.
- **Frontend Build:** Succeeded (`next build` compiled all 13 routes cleanly).
- **Integration Smoke Test:** 9/9 passed (`scripts/smoke_test.py`).
