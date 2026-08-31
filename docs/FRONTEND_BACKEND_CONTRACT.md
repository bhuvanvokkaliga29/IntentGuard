# Frontend ↔ Backend Contract & Single Source of Truth

## 1. Single Source of Truth Invariant
The backend is the sole owner of all authorization logic, policy evaluations, confidence calculations, and agent state transitions.
- **Frontend Role**: Purely visual presentation, telemetry rendering, and interactive scenario selection.
- **Forbidden in Frontend**: Hardcoded decision logic, mock evaluation metrics, or client-side authorization bypasses.

## 2. API Data Contracts

### A. Proposal Evaluation (`POST /decisions/evaluate` or `/agents/orchestrator/execute`)
```typescript
interface DecisionResponse {
  decision_id: string;
  transaction_id: string;
  final_decision: "ALLOW" | "FLAG" | "BLOCK" | "ESCALATE";
  explanation: string;
  confidence_score: number;
  decision_path: string;
  structural_result: {
    overall_pass: boolean;
    failure_reasons: string[];
  };
  semantic_judgment?: {
    majority_verdict: "direct_fit" | "related_fit" | "no_fit" | "ambiguous";
    agreement_rate: number;
  };
  latency_ms: number;
}
```

### B. Live Telemetry Event (`GET /agents/stream`)
```typescript
interface AgentTelemetryEvent {
  event_id: string;
  run_id: string;
  agent_id: string;
  event_type: string;
  stage: string;
  payload: {
    observable_summary?: {
      objective: string;
      selected_action: string;
      evidence_used: string[];
      tool_used?: string;
      result_summary: string;
      confidence: number;
      next_action: string;
    };
  };
  timestamp: string;
}
```
