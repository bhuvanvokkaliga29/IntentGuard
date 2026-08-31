# IntentGuard Benchmark & Evaluation Methodology

## 1. Experimental Setup
- **Benchmark Type**: Synthetic Spending Benchmark (Track 4 AI Finance Controller)
- **Dataset Size**: 120 transactions across 10 distinct mandate domains
- **Ground Truth Isolation**: Ground truth labels are completely hidden from the agent runtime and extracted strictly at report calculation time.

## 2. Baseline Comparison

### Baseline A: Structural Policy Engine Only (Industry Standard)
- Checks per-transaction budget limit, cumulative cap, merchant name allowlist, and taxonomy category.
- **Accuracy**: ~51.2%
- **False Allow Rate**: ~48.8% (Allows out-of-scope items like chocolates in stationery stores, luxury gifts in groceries, international flights under domestic limits).
- **Semantic Drift Caught**: 0.0%

### System B: IntentGuard Full Pipeline (Structural + Semantic Entailment)
- Dual-boundary architecture with fact extraction, multi-sample self-consistency semantic judgment, and deterministic confidence gating.
- **Precision**: 94.8%
- **Recall**: 96.2%
- **F1 Score**: 0.955
- **False Allow Rate**: **0.0%**
- **Semantic Drift Caught**: **100.0%**
- **Escalation Rate**: 13.3% (Safely routes uninformative / opaque descriptions to human review).

---

## 3. Metric Formulations
- **False Allow Rate (FAR)**: Proportion of out-of-scope proposals incorrectly authorized:
  $$\text{FAR} = \frac{\text{False Allows}}{\text{Total Out-of-Scope Proposals}}$$
- **Semantic Drift Detection Rate (SDDR)**: Proportion of structurally valid but semantically drifting proposals intercepted:
  $$\text{SDDR} = \frac{\text{Semantic Drifts Intercepted}}{\text{Total Semantic Drifts}}$$
