"""
IntentGuard — Confidence Engine

Confidence is COMPUTED, never asked from the LLM.
The LLM is never asked "How confident are you?"

Confidence depends on:
- Self-consistency agreement rate across semantic samples
- Structural pass/fail
- Evidence completeness
- Transaction amount proximity to limit
- Hard categorical mismatches in extracted facts
"""

from typing import Dict, List, Optional

from backend.models import SemanticVerdict, StructuralResult, ExtractedFacts
from backend.policy.thresholds import get_thresholds


def compute_agreement_rate(verdicts: List[str]) -> float:
    """
    Compute the agreement rate among semantic judgment samples.
    
    Examples:
        [FIT, FIT, FIT] → 1.00
        [FIT, FIT, AMBIGUOUS] → 0.67
        [FIT, NO_FIT, AMBIGUOUS] → 0.33
    """
    if not verdicts:
        return 0.0

    from collections import Counter
    counts = Counter(verdicts)
    most_common_count = counts.most_common(1)[0][1]
    return most_common_count / len(verdicts)


def compute_confidence(
    structural_result: StructuralResult,
    semantic_verdicts: List[str],
    extracted_facts: Optional[Dict] = None,
    txn_amount: float = 0.0,
    mandate_max_amount: float = 0.0,
    mandate_location_constraint: Optional[str] = None,
) -> Dict:
    """
    Compute deterministic confidence score.
    
    Returns a dict with:
    - confidence_score: float (0.0 to 1.0)
    - components: dict with breakdown of score components
    - agreement_rate: float
    """
    thresholds = get_thresholds()

    # ── Base confidence from self-consistency agreement ────────
    agreement_rate = compute_agreement_rate(semantic_verdicts)

    # Start with agreement rate as base
    base_confidence = agreement_rate

    adjustments = {}
    total_adjustment = 0.0

    # ── Adjustment 1: Agreement quality bonus/penalty ─────────
    if agreement_rate >= 1.0:
        adj = thresholds.FULL_AGREEMENT_BONUS
        adjustments["full_agreement_bonus"] = adj
        total_adjustment += adj
    elif agreement_rate <= 0.34:
        adj = -thresholds.NO_AGREEMENT_PENALTY
        adjustments["no_agreement_penalty"] = adj
        total_adjustment += adj
    elif agreement_rate < 0.67:
        adj = -thresholds.PARTIAL_AGREEMENT_PENALTY
        adjustments["partial_agreement_penalty"] = adj
        total_adjustment += adj

    # ── Adjustment 2: Structural pass bonus ───────────────────
    overall_pass = structural_result.get("overall_pass", False) if isinstance(structural_result, dict) else getattr(structural_result, "overall_pass", False)
    if overall_pass:
        adjustments["structural_pass"] = 0.05
        total_adjustment += 0.05
    else:
        # If structural checks failed, confidence in any non-BLOCK
        # decision should be very low
        adjustments["structural_fail_penalty"] = -0.20
        total_adjustment -= 0.20

    # ── Adjustment 3: Amount proximity to limit ───────────────
    if mandate_max_amount > 0 and txn_amount > 0:
        amount_ratio = txn_amount / mandate_max_amount
        if amount_ratio >= thresholds.AMOUNT_PROXIMITY_THRESHOLD:
            adj = -thresholds.AMOUNT_PROXIMITY_PENALTY
            adjustments["amount_proximity_penalty"] = adj
            total_adjustment += adj

    # ── Adjustment 4: Hard categorical mismatch ───────────────
    if extracted_facts:
        # Check domestic/international mismatch
        extracted_location = extracted_facts.get("domestic_or_international")
        if (
            mandate_location_constraint
            and extracted_location
            and mandate_location_constraint.lower() != extracted_location.lower()
        ):
            adj = -thresholds.HARD_MISMATCH_PENALTY
            adjustments["hard_location_mismatch"] = adj
            total_adjustment += adj

    # ── Adjustment 5: Evidence completeness ───────────────────
    if extracted_facts:
        # Count how many key fields have actual values
        key_fields = ["normalized_category", "item_type", "specific_product"]
        filled = sum(1 for f in key_fields if extracted_facts.get(f))
        completeness = filled / len(key_fields)
        if completeness < 0.5:
            adj = -thresholds.INCOMPLETE_EVIDENCE_PENALTY
            adjustments["incomplete_evidence_penalty"] = adj
            total_adjustment += adj
    else:
        # No extracted facts at all
        adj = -thresholds.INCOMPLETE_EVIDENCE_PENALTY
        adjustments["no_extracted_facts"] = adj
        total_adjustment += adj

    # ── Final confidence ──────────────────────────────────────
    confidence_score = max(0.0, min(1.0, base_confidence + total_adjustment))

    return {
        "confidence_score": round(confidence_score, 4),
        "agreement_rate": round(agreement_rate, 4),
        "base_confidence": round(base_confidence, 4),
        "total_adjustment": round(total_adjustment, 4),
        "adjustments": adjustments,
        "semantic_verdicts": semantic_verdicts,
        "num_samples": len(semantic_verdicts),
    }
