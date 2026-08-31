# IntentGuard REST API Documentation

Base URL: `http://localhost:8000`
OpenAPI Documentation: `http://localhost:8000/docs`

---

## 1. System Health
### `GET /health`
Returns system status, active database connection, and LLM configuration.

**Example Request:**
```bash
curl -X GET http://localhost:8000/health
```

**Example Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "llm_provider": {
    "provider": "gemini",
    "configured": true,
    "model": "gemini-2.5-flash",
    "is_mock": false
  },
  "timestamp": "2026-08-31T00:18:00.000000"
}
```

---

## 2. Agent Orchestration
### `POST /agents/orchestrator/execute`
Launches an autonomous agent run through the 11-stage Finite State Machine.

**Request Body Schema:**
```json
{
  "agent_type": "buying_agent",
  "mandate_id": "mandate-001-office-supplies",
  "objective": "BEST_RATING",
  "injected_failure": null,
  "transcript": null
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/agents/orchestrator/execute \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "buying_agent",
    "mandate_id": "mandate-001-office-supplies",
    "objective": "BEST_RATING"
  }'
```

**Example Response:**
```json
{
  "run_id": "8f3b2c1a-5e4d-4c3b-2a1f-0e9d8c7b6a5f",
  "agent_id": "buying_agent",
  "status": "COMPLETED",
  "proposal": {
    "id": "prod-stat-paper-pens",
    "name": "Ferrero Rocher Chocolates Luxury Box",
    "price": 1950.0,
    "merchant_name": "Stationery Mart"
  },
  "intentguard_decision": {
    "decision_id": "dec-12345",
    "final_decision": "FLAG",
    "explanation": "Transaction flagged: Although Stationery Mart is an approved vendor, chocolates are food confectionery and violate the office supplies spending mandate."
  },
  "latency_ms": 480.2,
  "tools_used": ["catalog.search", "pricing.lookup", "transaction.validate"]
}
```

---

## 3. Real-Time Telemetry Stream
### `GET /agents/stream`
Server-Sent Events (SSE) stream emitting live agent state transitions, tool invocations, self-healing events, and IntentGuard decisions.

**Example Request:**
```bash
curl -N http://localhost:8000/agents/stream
```

---

## 4. Evaluation & Metrics
### `GET /agents/metrics`
Returns derived empirical agent proficiency and financial safety metrics computed from SQLite execution records.

**Example Response:**
```json
{
  "total_runs": 25,
  "task_success_rate": 0.96,
  "tool_success_rate": 0.98,
  "average_latency_ms": 385.4,
  "recovery_success_rate": 1.0,
  "intentguard_rejection_rate": 0.44,
  "health_status": "HEALTHY",
  "metrics_basis": "Empirically calculated from database runs"
}
```
