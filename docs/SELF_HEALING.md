# Agent Self-Healing & Fault Recovery

## 1. Core Engineering Principle: Self-Healing $\neq$ Self-Authorization
- **Operational Failures**: Agents are permitted to recover autonomously from infrastructure and tool faults (e.g. catalog lookup timeout $\rightarrow$ retry).
- **Security & Authorization Invariants**: Agents are strictly prohibited from recovering by mutating user mandates, expanding budget limits, adding vendors, or bypassing IntentGuard.

## 2. Recovery Strategies
1. **Tool Timeout / Transient Fault**: Exponential backoff retry up to 3 attempts.
2. **Malformed LLM Output**: Strict JSON repair schema re-invocation.
3. **Product Unavailable**: Autonomous candidate re-ranking.
4. **Provider Outage**: Failover to secondary LLM provider.
5. **Security Violation**: Immediate `SAFE_STOP` and escalation to human review.
