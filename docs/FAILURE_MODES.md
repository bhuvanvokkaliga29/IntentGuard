# IntentGuard — Failure Modes & Recovery Matrix

This document catalogs all potential operational, semantic, adversarial, and infrastructure failure modes, their detection mechanism, self-healing recovery strategy, and test verification status.

---

## Failure Mode Verification Table

| Failure Mode | Trigger / Fault Scenario | Detection Mechanism | Recovery / Safety Action | Test Verification | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **F-01: Transient Tool Timeout** | `catalog.search` network latency > 3000ms | Orchestrator timeout interceptor | Exponential backoff retry (up to 3 attempts) | [`test_agent_orchestrator.py`](../backend/tests/test_agent_orchestrator.py) | **VERIFIED** |
| **F-02: Retry Exhaustion** | 3 consecutive tool execution failures | Attempt counter >= max_retries | `SAFE_STOP` -> Structured failure report | [`test_chaos.py`](../backend/tests/test_chaos.py) | **VERIFIED** |
| **F-03: LLM Rate Limit (HTTP 429)** | Gemini/Grok API quota exhausted | HTTP status 429 in Provider | Bounded retry with backoff -> Safe fallback to `ESCALATE` | [`test_chaos.py`](../backend/tests/test_chaos.py), [`smoke_test.py`](../scripts/smoke_test.py) | **VERIFIED** |
| **F-04: Malformed Model Output** | LLM outputs invalid JSON or missing fields | Strict Pydantic schema validation | Schema repair prompt -> Fallback to `ESCALATE` | [`test_semantic.py`](../backend/tests/test_semantic.py), [`test_chaos.py`](../backend/tests/test_chaos.py) | **VERIFIED** |
| **F-05: Adversarial Prompt Injection** | Item description contains `[SYSTEM OVERRIDE]` | Untrusted data isolation boundary | Stripped from control instructions; evaluated purely as item text | [`test_prompt_injection.py`](../backend/tests/test_prompt_injection.py) | **VERIFIED** |
| **F-06: Vague / Insufficient Mandate** | User specifies `"Buy office stuff"` without specifics | Evidence completeness check (< 0.5) | Confidence penalty -> Deterministic `ESCALATE` to human | [`test_failure_modes.py`](../backend/tests/test_failure_modes.py) | **VERIFIED** |
| **F-07: Out-of-Scope Semantic Drift** | Purchasing chocolates under stationery budget | Multi-sample semantic entailment (`no_fit`) | Deterministic `BLOCK` | [`test_e2e_integration.py`](../backend/tests/test_e2e_integration.py) | **VERIFIED** |
| **F-08: Hard Constraint Violation** | Price exceeds per-transaction limit or unapproved merchant | Deterministic `check_hard_constraints()` | Immediate deterministic `BLOCK` (Zero LLM invoked) | [`test_structural.py`](../backend/tests/test_structural.py) | **VERIFIED** |
| **F-09: Database Session Lock** | High concurrency SQLite access contention | SQLAlchemy connection pool timeout | Non-blocking retry with transaction rollback | [`test_production_readiness.py`](../backend/tests/test_production_readiness.py) | **VERIFIED** |
| **F-10: Self-Healing Permission Boundary** | Compromised agent attempts to mutate budget on retry | Strict engine signature separation | Impossible by design (Engine holds zero mutation methods) | [`test_chaos.py`](../backend/tests/test_chaos.py) | **VERIFIED** |
| **F-11: Provider Failover Outage** | Primary Gemini API completely unreachable | Provider exception handler | Failover to secondary Grok provider (if configured) | [`test_chaos.py`](../backend/tests/test_chaos.py) | **VERIFIED** |
| **F-12: Illegal FSM Stage Bypass** | Malicious agent attempts direct transition `IDLE -> COMPLETED` | `validate_stage_transition()` table | Immediate exception and rejection | [`test_agent_orchestrator.py`](../backend/tests/test_agent_orchestrator.py) | **VERIFIED** |

---

## Status Legend
- **VERIFIED:** Automated unit, chaos, or integration test exists and passes in CI.
- **PARTIAL:** Handled in core logic with partial test coverage.
- **NOT_YET_HANDLED:** Known future enhancement backlog.
