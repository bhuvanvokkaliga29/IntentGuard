# IntentGuard Security & Control Invariants

## 1. Security Architecture Principles

### Principle 1: Separation of Proposer and Authorizer
Autonomous agents propose transactions based on user objectives. IntentGuard enforces authorization. Proposers and authorizers run in strictly isolated memory and permission domains.

### Principle 2: Deterministic Final Decision
Financial authorization must be deterministic and reproducible. LLM outputs are treated as probabilistic evidence, but final classification (`ALLOW`, `BLOCK`, `ESCALATE`) is computed by deterministic Python code.

### Principle 3: Defense-in-Depth Pipeline
1. **Pydantic Schema Validation**: Rejects malformed payload syntax.
2. **Structural Policy**: Enforces mathematical budget caps and merchant allowlists.
3. **Semantic Verification**: Verifies intent alignment across 3 independent samples.
4. **Confidence Evaluation**: Discounts confidence on border proximity and missing facts.
5. **Deterministic Policy**: Authorizes or escalates to human review.

### Principle 4: Zero Committed Secrets
All API credentials, database URLs, and cryptographic keys are loaded dynamically from environment variables (`.env`). No secrets are committed to version control.

### Principle 5: Prototype Authentication Scope
For the scope of the Razorpay Buildathon, user authentication and JWT session validation are stubbed out to prioritize demonstrating the AI architectural boundaries. Production deployments must integrate a standard IdP (e.g. Auth0, AWS Cognito) to secure the API.
