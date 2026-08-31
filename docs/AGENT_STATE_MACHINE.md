# Finite State Machine Specification for Autonomous Agents

## 1. Stage Definitions
Proposer agents transition through an explicit 11-stage Finite State Machine (FSM):

```
IDLE
  │
  ▼
INITIALIZING
  │
  ▼
READING_CONTEXT
  │
  ▼
PLANNING
  │
  ▼
TOOL_CALL ◄─── (Self-Healing Recovery)
  │               ▲
  ▼               │
OBSERVING ────────┘
  │
  ▼
EVALUATING_OPTIONS
  │
  ▼
GENERATING_PROPOSAL
  │
  ▼
VALIDATING_PROPOSAL
  │
  ▼
SUBMITTING_TO_INTENTGUARD
  │
  ▼
WAITING_FOR_DECISION
  │
  ▼
COMPLETED
```

## 2. Failure & Terminal Stages
- `RECOVERING`: Active self-healing retry or fallback.
- `SAFE_STOPPED`: Run halted due to retry exhaustion or security policy violation.
- `FAILED`: Unhandled fatal error.
