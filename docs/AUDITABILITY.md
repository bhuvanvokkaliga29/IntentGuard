# IntentGuard Auditability, Versioning & Decision Replay Specification

## 1. Overview & Non-Repudiation Architecture

In high-assurance financial control planes, every automated decision must be:
1. **Mathematically Provable:** Cryptographically chained to establish an immutable, tamper-evident sequence.
2. **Deterministic & Reproducible:** Reconstructible at any future point in time using exact historical versions.
3. **Accountable & Auditable:** Every automated event and human intervention must record an explicit actor, action, timestamp, and signature.

---

## 2. Cryptographic SHA-256 Audit Hash Chain

Every transaction evaluation automatically generates an audit record in the `audit_logs` table (`backend/db.py`):

```
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│     Audit Record N-1    │       │      Audit Record N     │       │     Audit Record N+1    │
│  seq: 142               │       │  seq: 143               │       │  seq: 144               │
│  prev_hash: <hash_141>  │       │  prev_hash: <hash_142>  │       │  prev_hash: <hash_143>  │
│  curr_hash: <hash_142>  ├──────►│  curr_hash: <hash_143>  ├──────►│  curr_hash: <hash_144>  │
│  action: AUTHORIZE      │       │  action: ESCALATE       │       │  action: HUMAN_APPROVE  │
└─────────────────────────┘       └─────────────────────────┘       └─────────────────────────┘
```

### Hash Computation Specification
1. **Genesis Hash:** The very first entry in the ledger sets `previous_record_hash = "0" * 64`.
2. **Canonical Payload Formulation:**
   ```python
   canonical_payload = {
       "sequence_number": row.sequence_number,
       "decision_id": row.decision_id,
       "transaction_id": row.transaction_id,
       "mandate_id": row.mandate_id,
       "final_decision": row.final_decision,
       "previous_record_hash": row.previous_record_hash,
       "timestamp": row.timestamp.isoformat(),
   }
   ```
3. **Hashing Algorithm:**
   `current_record_hash = SHA256(json.dumps(canonical_payload, sort_keys=True))`

### Chain Verification Engine
- Exposed via `GET /audit/chain/verify`.
- Recomputes the SHA-256 hash for every committed record from sequence 1 to $M$.
- Flags:
  - `HASH_MISMATCH`: The content of a record was modified post-commit.
  - `CHAIN_BROKEN`: A record was deleted or reordered, causing `previous_record_hash != prior.current_record_hash`.
  - `SEQUENCE_GAP`: Sequence numbers do not increment monotonically by 1.

---

## 3. Mandate & Policy Version Snapshots

Every decision record in `decisions` and `audit_logs` is permanently bound to immutable version metadata:
- `mandate_version`: Integer version of the spending mandate under which the transaction was authorized (e.g. 1, 2).
- `policy_version`: Active version string of the deterministic policy engine (e.g. `2.1.0`).
- `config_hash`: SHA-256 digest of active confidence thresholds, constraint definitions, and matrix rules.

### Mandate Lineage & Versioning
When a mandate is modified, the existing record is transitioned to `policy_state = "SUPERSEDED"` and a new record is created with `version = current_version + 1` and `previous_version_id = current.id`. Historical transactions maintain referential integrity to the exact version active at the time of execution.

---

## 4. Deterministic Decision Replay Engine

The Replay Engine (`backend/policy/replay.py`) proves complete reproducibility by re-evaluating historical proposals against their historical mandate and policy snapshots.

### Replay Invariant
> **CRITICAL INVARIANT:**
> Decision replay is strictly analytical. It NEVER invokes the financial execution gateway or initiates fund movements.

### Replay Workflow
1. Client issues `POST /decisions/{decision_id}/replay`.
2. Replay engine loads the original transaction proposal, historical mandate version, and historical policy version.
3. Reconstructs:
   - Structural hard constraints evaluation
   - Semantic drift analysis & evidence
   - Contextual novelty, behavioral baseline, and temporal checks
   - Deterministic policy matrix verdict
4. Compares `replayed_decision` against `original_decision`.
5. Returns `is_reproducible: true` and detailed verification metrics.

---

## 5. Human Review Auditability & Non-Repudiation

When transactions are escalated to human compliance officers:
1. Review actions (`APPROVE`, `REJECT`, `REQUEST_MORE_INFORMATION`) are dispatched via `POST /decisions/{decision_id}/review`.
2. The decision record is updated with reviewer identity (`reviewer_id`), review notes, and timestamp.
3. If approved, the transaction routes through `stage_guard_execution_boundary` with idempotency key `review-{decision_id}`.
4. An immutable audit record is appended to the SHA-256 hash chain documenting the human intervention.
