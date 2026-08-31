# Agent & System Failure Modes

## 1. Failure Modes & Mitigations

| Failure Mode | Root Cause | System Defense |
|---|---|---|
| **Semantic Drift** | Optimization objective clashes with mandate intent | IntentGuard multi-sample semantic verification $\rightarrow$ **FLAG / BLOCK** |
| **Tool Timeout** | Downstream catalog network delay | Self-healing exponential backoff retry $\rightarrow$ **RECOVER** |
| **Malformed LLM Output** | Non-compliant JSON string | Strict Pydantic schema validation $\rightarrow$ **REPAIR / RETRY** |
| **Prompt Injection** | Adversarial override in item description | Untrusted data isolation $\rightarrow$ **FLAG / BLOCK** |
| **Vague Description** | Opaque single-word SKU string | Evidence completeness penalty $\rightarrow$ **ESCALATE to Human** |
| **Repeated Failures** | Downstream catastrophic failure | Retry exhaustion $\rightarrow$ **SAFE_STOP** |
