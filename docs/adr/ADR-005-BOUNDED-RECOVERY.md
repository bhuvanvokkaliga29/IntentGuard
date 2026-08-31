# ADR-005: Bounded Self-Healing Without Self-Authorization

## Status
Accepted

## Context
Self-healing mechanisms are crucial for agent resilience against network timeouts or tool failures. However, an autonomous agent must never be permitted to "heal" a policy rejection by expanding its budget, altering the merchant allowlist, or re-interpreting user intent.

## Decision
The Self-Healing Engine (`backend/agent/self_healing.py`) is bounded:
1. Permitted recoveries: Transient tool retry, JSON schema repair, catalog candidate re-ranking, and provider failover.
2. Invariants: Retries are capped at 3 attempts. Mandates, budgets, and security policies are strictly immutable.
3. Policy rejections (`BLOCK`, `FLAG`) cannot be bypassed by retry.

## Consequences
- Operational stability is achieved without compromising financial safety.
- Repeated failures result in an immediate `SAFE_STOP` and human review escalation.
