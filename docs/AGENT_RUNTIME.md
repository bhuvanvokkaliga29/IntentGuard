# Autonomous Agent Runtime Architecture

## 1. Runtime Overview
The IntentGuard Agent Runtime provides a bounded, observable execution environment for autonomous transaction-proposing agents. Proposer agents never possess financial credentials or direct payment authority; they interact strictly via bounded tools and submit structured proposals to the IntentGuard Gateway.

```
MANDATE SERVICE
      │
      ▼
AGENT ORCHESTRATOR
      │
      ├─► Buying Agent (Procurement optimizer)
      ├─► Recommendation Agent (Promotional / deals recommender)
      └─► Voice Mandate Agent (Natural language parser)
      │
      ▼
CONCRETE TOOL EXECUTION (`catalog.search`, `merchant.lookup`, `pricing.lookup`)
      │
      ▼ (Self-Healing Fault Recovery)
PROPOSAL GATEWAY
      │
      ▼
INTENTGUARD GATEWAY (Deterministic Financial Gate)
```

## 2. Bounded Execution Limits
Every agent run enforces hard operational boundaries:
- `max_iterations`: 10 maximum state iterations
- `max_tool_calls`: 8 tool invocations per run
- `timeout_seconds`: 30.0s deadline
- `retry_limit`: 3 self-healing retry attempts

## 3. Bounded Run Memory
Agent memory is strictly segmented:
- **Short-Term Run Memory**: Contains ephemeral catalog observations, candidate items, previous tool failures, and recovery attempts for the current `run_id`. Capped at 25 items.
- **Long-Term Mandate Constraints**: Immutable user policy boundaries and merchant allowlists.
