# Auditability & Replay Architecture

## 1. Cryptographic Tamper-Evident Audit Chain
Every transaction evaluation automatically writes a cryptographic tamper-evident record to the `audit_logs` table in SQLite (`backend/db.py`):
- `id`: Unique UUIDv4 audit record identifier
- `decision_id`: Foreign key reference to decision record
- `policy_version`: Active policy version (e.g. `policy_v1`)
- `prompt_version`: Active extraction and entailment prompt template version (e.g. `semantic_v1`)
- `model`: Model identifier (e.g. `gemini-2.5-flash` or `grok-3-mini`)
- `provider`: Active LLM provider
- `tool_calls`: Complete sequence of agent tool invocations and latency measurements
- `structural_result`: Exact JSON output of hard constraint checks
- `semantic_samples`: Full list of semantic entailment samples and verdicts
- `confidence_calculation`: Detailed score derivation and penalty breakdown

## 2. Replay Semantics
- **Deterministic Replay**: Given the recorded structural checks and semantic verdicts, `scripts/smoke_test.py` or the Replay API will deterministically reproduce the identical decision.
- **Model Re-Execution**: Rerunning the LLM on historical inputs verifies model stability and prompt version drift over time.
