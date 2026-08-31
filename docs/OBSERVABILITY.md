# Observability, Live Telemetry & Event Streaming

## 1. Event Bus Architecture
IntentGuard maintains an asynchronous in-memory Event Bus broadcasting structured telemetry over Server-Sent Events (`GET /agents/stream`) and persisting records to SQLite.

### Supported Event Types:
- `agent.started`
- `agent.stage_changed`
- `agent.tool.started`
- `agent.tool.completed`
- `agent.tool.failed`
- `agent.recovery.started`
- `agent.recovery.completed`
- `intentguard.started`
- `intentguard.decision.created`
- `agent.completed`
- `agent.safe_stopped`
- `agent.failed`

## 2. Observable Reasoning Summaries (No Private CoT)
To maintain security and explainability without exposing private chain-of-thought, every state transition emits an **Observable Reasoning Summary**:
- `objective`: What the agent is trying to accomplish
- `selected_action`: Concrete action taken
- `evidence_used`: Signals consulted (e.g. `budget_cap`, `vendor_rating`)
- `tool_used`: Tool invoked
- `result_summary`: Outcome
- `confidence`: Heuristic score
- `next_action`: Planned next stage
