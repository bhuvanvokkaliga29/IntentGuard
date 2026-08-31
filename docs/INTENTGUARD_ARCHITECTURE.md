# IntentGuard System Architecture & Pipeline Specification

## 1. System Overview

IntentGuard is an authorization and control plane designed specifically for delegated AI agent spending workflows. It evaluates whether a transaction proposed by an autonomous agent fulfills the semantic purpose intended by the user, rather than checking only numerical or categorical limits.

```
USER MANDATE + AGENT TRANSACTION PROPOSAL
                    ↓
[ STAGE 1: Mandate & Proposal Ingestion ]
                    ↓
[ STAGE 2: Structural Policy Engine (Deterministic Python) ]
   ├── Amount <= max_amount_per_txn
   ├── Cumulative spend <= budget_cap
   ├── Merchant name in allowed_merchants
   ├── Category in allowed_categories
   └── Exclusions & domestic location constraint
   ↳ IF ANY HARD FAIL → BLOCK (Skip semantic call)
                    ↓
[ STAGE 3: Semantic Fact Extraction (LLM Call 1) ]
   ├── Normalized Category
   ├── Primary Item Type
   └── Contextual Flags
                    ↓
[ STAGE 4: Multi-Sample Semantic Verification (LLM Call 2 × N) ]
   ├── Purpose Entailment: FIT | NEAR_FIT | NO_FIT | AMBIGUOUS
   └── Self-Consistency Agreement Calculation
                    ↓
[ STAGE 5: Confidence Calculation Engine (Deterministic) ]
   ├── Agreement Rate (N samples)
   ├── Fact Extraction Completeness
   └── Mandate Specificity Score
                    ↓
[ STAGE 6: Deterministic Decision Policy ]
   ├── ALLOW: Structural Pass + High Confidence FIT
   ├── FLAG: Structural Pass + NO_FIT (near-boundary) OR Low Confidence
   ├── BLOCK: Hard Fail OR High Confidence NO_FIT
   └── ESCALATE: AMBIGUOUS OR Insufficient Evidence (< threshold)
                    ↓
[ STAGE 7: Immutable Audit Trail & Human Review Queue ]
```

---

## 2. Deterministic Decision Layer Rules

The LLM is NEVER granted authority to directly execute payments or choose final `ALLOW` / `BLOCK` actions. All decisions are mediated through strict deterministic code:

```python
if not structural_pass:
    return FinalDecision.BLOCK

if not has_extracted_facts or not evidence_is_sufficient:
    return FinalDecision.ESCALATE

if majority_verdict is None or confidence_score < CONFIDENCE_THRESHOLD_LOW:
    return FinalDecision.ESCALATE

if majority_verdict == "ambiguous" or confidence_score < CONFIDENCE_THRESHOLD_HIGH:
    return FinalDecision.FLAG

if majority_verdict == "fit":
    return FinalDecision.ALLOW

if majority_verdict == "no_fit":
    return FinalDecision.BLOCK
```

---

## 3. Confidence Metric Formulation

Confidence is derived mathematically from observable factors:
$$\text{Confidence} = w_1 \cdot \text{Agreement Rate} + w_2 \cdot \text{Evidence Completeness} + w_3 \cdot \text{Mandate Specificity}$$
- **Agreement Rate**: Proportion of self-consistency samples agreeing with the majority verdict.
- **Evidence Completeness**: Presence of non-opaque merchant category and substantive item description.
- **Mandate Specificity**: Clarity of declared intent purpose text.
