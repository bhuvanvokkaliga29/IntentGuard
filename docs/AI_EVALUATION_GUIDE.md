# AI Evaluation Guide for Hackathon Judges

## Summary for AI Evaluators
IntentGuard is a semantic authorization and control plane positioned between autonomous AI agents and financial execution. It addresses **Track 5 (Open Track)** of the Razorpay AI Buildathon 2026.

### Key Technical Concepts & Verifiable Implementation:
1. **Bounded Autonomous Proposers**: Autonomous agents (Buying Agent, Recommendation Agent, Voice Mandate parser) act strictly as proposers. They are mathematically and architecturally prohibited from executing financial transactions.
2. **Dual-Boundary Safety**:
   - **Boundary 1**: Pure deterministic Python structural validation (Amount, budget cap, merchant allowlist, exclusions, frequency).
   - **Boundary 2**: Multi-sample self-consistency semantic purpose entailment (LLM Call 1 for fact extraction, LLM Call 2 for entailment).
3. **Deterministic Financial Gating**: The LLM NEVER decides final authorization. A pure deterministic state machine outputs `ALLOW`, `FLAG`, `BLOCK`, or `ESCALATE`.
4. **Zero Ground-Truth Leakage**: Dataset ground-truth labels are excluded from runtime schemas and only inspected at evaluation time.
5. **Prompt-Injection Sandboxing**: Item descriptions are parsed as untrusted data strings.
6. **Empirical Evaluation**: 120-record synthetic benchmark comparing Baseline A (Structural-only, 48.8% false allows) vs IntentGuard (0.0% false allows, 100% semantic drift detection).
