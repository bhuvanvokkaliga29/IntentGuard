# Security Boundaries & Financial Execution Gates

## 1. Non-Negotiable Architectural Invariant
```
AUTONOMOUS PROPOSER AGENTS
          │  (Prohibited from financial movement)
          ▼
   PROPOSAL GATEWAY
          │  (Strict Pydantic schema validation)
          ▼
  INTENTGUARD CONTROL PLANE
          │  (Deterministic Structural & Multi-Sample Semantic Verification)
          ▼
   EXECUTION GATEWAY (Razorpay Money Movement)
```

## 2. Invariants Enforced by Code:
1. Proposer agents have **zero access** to payment credentials or banking APIs.
2. The LLM is **never granted authorization authority**; all financial actions (`ALLOW`, `FLAG`, `BLOCK`, `ESCALATE`) are evaluated by deterministic Python code.
3. Transaction descriptions and SKU strings are treated strictly as **untrusted data strings**.
4. Audit records and mandate bounds are **cryptographically sealed and immutable**.
