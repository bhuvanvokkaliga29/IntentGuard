# IntentGuard Security & Control Invariants

## 1. Security Architecture Principles

### Principle 1: Separation of Proposer and Authorizer
Autonomous agents propose transactions based on user objectives. IntentGuard enforces authorization. Proposers and authorizers run in strictly isolated memory and permission domains. Autonomous agents possess zero financial credentials and cannot directly initiate fund movement.

### Principle 2: Deterministic Final Decision (Zero LLM Direct Authority)
Financial authorization must be deterministic, reproducible, and mathematically provable. LLM outputs are treated as probabilistic evidence, but final classification (`ALLOW`, `BLOCK`, `ESCALATE`) is computed by deterministic Python code in `backend/policy/decision.py`. Under no circumstances does an LLM output directly trigger transaction execution.

### Principle 3: Defense-in-Depth Pipeline
1. **Pydantic Schema Validation**: Rejects malformed payload syntax and type mismatches.
2. **Recursive Multi-Surface Prompt Defense**: Scans dictionary keys, values, nested structures, and metadata with Unicode NFKC normalization and zero-width stripping to eliminate instruction overrides.
3. **Structural Hard Constraints**: Deterministically enforces numerical spend limits, budget caps, canonical merchant normalizations, and category allowlists/blocklists without invoking LLMs.
4. **Semantic Verification**: Verifies intent alignment across multi-sample fact extraction and entailment reasoning.
5. **Confidence Evaluation**: Discounts confidence based on boundary proximity, missing facts, and agreement rates.
6. **Deterministic Decision Matrix**: Renders `ALLOW`, `BLOCK`, or `ESCALATE`.
7. **Authoritative Execution Boundary**: Payments can ONLY execute if decision is strictly `ALLOW`. `BLOCK` and `ESCALATE` decisions are unconditionally rejected at the adapter boundary.

### Principle 4: Zero Committed Secrets & Transparent Masking
All API credentials, database URLs, and cryptographic keys are loaded dynamically from environment variables (`.env`) or cloud key vaults. Secrets are masked in string representations (`__repr__` and `__str__`) to prevent credential leakage into log files or crash traces.

### Principle 5: API Key Authentication & Sliding-Window Rate Limiting
All mutation endpoints require valid API key authorization via `X-API-Key` or `Authorization: Bearer`, verified in constant time (`hmac.compare_digest`). Bounded sliding-window rate limiting (`backend/security/rate_limiter.py`) throttles excessive requests (HTTP 429 Too Many Requests) to prevent denial-of-wallet and credential exhaustion. Health checks and public status endpoints remain intentionally accessible.

### Principle 6: Cryptographic Audit Hash Chaining & Human Review Integrity
Every authorization decision and human review action (`APPROVED`, `REJECTED`, `REQUEST_MORE_INFO`) creates a dedicated audit log record. Audit records are cryptographically linked into an unbroken SHA-256 hash chain (`previous_record_hash -> current_record_hash`). The chain is tamper-evident and continuously verifiable via `GET /audit/chain/verify`.

### Principle 7: Bounded Semantic LRU Cache & Invalidation
The semantic cache is a thread-safe, bounded LRU cache (`backend/semantic/cache.py`) with configurable maximum size, deterministic eviction, hit/miss metrics, and context-complete SHA-256 keys (incorporating mandate intent, allowed merchants, exclusions, categories, and policy version). Mutating or revoking a mandate deterministically invalidates all associated cached authorizations.

### Principle 8: Enterprise Secrets Management
To support high-assurance banking and enterprise deployments beyond local `.env` files, IntentGuard implements a pluggable `SecretsProvider` in `backend/security/secrets.py`:
- **Local Environment (`EnvSecretsProvider`)**: Reads from `.env` and `os.environ` during development and containerized testing.
- **AWS Secrets Manager (`AWSSecretsManagerProvider`)**: Automatically fetches versioned API credentials and signing keys using AWS SDK / IAM roles.
- **HashiCorp Vault (`VaultSecretsProvider`)**: Integrates with Vault KV v2 secret engines using AppRole / Token authentication for zero-trust environments.
- **Resilient Fallback**: In the event of cloud network partition, providers fall back to configured local environment overrides with structured logging.
