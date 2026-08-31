# Honest Limitations & Prototype Scope

## 1. Prototype Limitations
- **Synthetic Data**: All evaluations and demo workflows utilize synthetic datasets generated via `scripts/generate_dataset.py`. It does not process live production banking data.
- **Domain Scope**: Currently calibrated for enterprise procurement, domestic travel, team meals, and office supplies. Expanding to specialized medical or legal procurement will require domain-specific extraction schemas.
- **LLM Latency**: Multi-sample semantic verification ($N=3$) introduces ~400–800ms of latency per evaluation. While acceptable for asynchronous agent proposals, high-throughput Point-of-Sale (POS) transactions under 100ms require fast embedding cache lookups.
- **Vague SKU Ambiguity**: If a merchant provides only an opaque code without description (e.g. `SKU-889`), semantic inference is impossible; IntentGuard safely defaults to `ESCALATE` rather than guessing.
- **No Direct Razorpay Settlement**: As a safety control layer prototype, IntentGuard models the authorization gateway without executing live funds movement.
