# Model Card: IntentGuard Semantic Entailment Engine

## 1. Model Details
- **Primary LLM**: Google Gemini (`gemini-2.5-flash`)
- **Secondary LLM**: xAI Grok (`grok-3-mini`)
- **Offline / Local Model**: Mock Semantic Engine (`mock-semantic-v1`)
- **Task**: 2-stage fact extraction and natural language semantic entailment verification.

## 2. Intended Use
- **Primary Use**: Extract structured object categories and evaluate whether an autonomous transaction proposal aligns with a user spending mandate.
- **Out-of-Scope**: Direct money execution, payment authorization, or budget mutation.

## 3. Evaluation & Performance

### Live Provider Benchmark (Genuine AI Performance)
- See: `docs/reports/evaluation_report_live.json`
- Evaluates real Gemini/Grok API semantic reasoning.
- **Note:** Due to free-tier quota limits, this may be run on a constrained subset (e.g. n=30) of the full 500-case dataset.

### Offline Mock Benchmark (CI / Regression)
- See: `docs/reports/evaluation_report.json`
- Evaluates the deterministic structural and confidence engines using a simulated keyword-based provider.
- **Warning:** Mock results are not evidence of real LLM semantic reasoning and are solely for regression testing the pipeline architecture.

## 4. Prompts & Security
- **Prompt Version:** `v1` (Extraction and Semantic templates)
- **Adversarial Prompt Injection Robustness:** 100% interception (sandboxed as untrusted data strings).
- **Latency:** Dependent on live provider API response time.

## 4. Fallback Behavior
If an LLM provider encounters a network timeout, quota limit, or malformed JSON output, the IntentGuard framework fails safely by escalating (`ESCALATE`) the proposal to the human review queue.
