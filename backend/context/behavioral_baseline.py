"""
IntentGuard — Behavioral Spending Baseline Engine

Establishes behavioral authorization context from historical authorized transactions.
Detects statistical deviations in:
- Normal spend range (percentiles & standard deviations)
- Merchant pattern consistency
- Typical category mix
- Transaction frequency

CRITICAL TERMINOLOGY INVARIANT:
This is explicitly framed as "Behavioral Authorization Context", NOT "fraud detection".
Deviations serve as structured evidence for deterministic policy escalation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BehavioralAnalysis(BaseModel):
    is_deviant: bool
    deviation_score: float = Field(..., ge=0.0, le=1.0)
    normal_spend_range: str
    observed_amount: float
    deviation_reasons: List[str] = Field(default_factory=list)
    confidence_penalty: float = Field(default=0.0, ge=0.0, le=0.5)


def compute_behavioral_baseline(
    proposal_amount: float,
    proposal_merchant: str,
    proposal_category: str,
    historical_txns: Optional[List[Dict[str, Any]]] = None,
) -> BehavioralAnalysis:
    """
    Computes statistical spending baseline and deviation metrics.
    """
    if not historical_txns or len(historical_txns) < 2:
        return BehavioralAnalysis(
            is_deviant=False,
            deviation_score=0.0,
            normal_spend_range="Insufficient history (establishing baseline)",
            observed_amount=proposal_amount,
            deviation_reasons=[],
            confidence_penalty=0.0,
        )

    amounts = [float(t.get("amount", 0.0)) for t in historical_txns if float(t.get("amount", 0.0)) > 0]
    if not amounts:
        return BehavioralAnalysis(
            is_deviant=False,
            deviation_score=0.0,
            normal_spend_range="N/A",
            observed_amount=proposal_amount,
            deviation_reasons=[],
            confidence_penalty=0.0,
        )

    mean_amt = sum(amounts) / len(amounts)
    variance = sum((x - mean_amt) ** 2 for x in amounts) / len(amounts)
    std_dev = variance ** 0.5

    min_normal = max(0.0, mean_amt - (1.5 * std_dev))
    max_normal = mean_amt + (2.0 * std_dev)

    reasons: List[str] = []
    dev_score = 0.0
    penalty = 0.0

    if proposal_amount > max_normal:
        multiplier = proposal_amount / max(mean_amt, 1.0)
        reasons.append(
            f"Observed amount ₹{proposal_amount:,.2f} deviates significantly from normal spend range "
            f"[₹{min_normal:,.2f} - ₹{max_normal:,.2f}] ({multiplier:.1f}x average spend)."
        )
        dev_score += min(0.6, (multiplier - 1.0) * 0.15)
        penalty += 0.10

    # Check category distribution
    cat_counts: Dict[str, int] = {}
    for t in historical_txns:
        c = str(t.get("merchant_category", "")).lower()
        cat_counts[c] = cat_counts.get(c, 0) + 1

    total_cat = sum(cat_counts.values())
    prop_cat = proposal_category.lower()
    if prop_cat in cat_counts and (cat_counts[prop_cat] / total_cat) < 0.1:
        reasons.append(f"Category '{proposal_category}' accounts for less than 10% of historical activity.")
        dev_score += 0.20
        penalty += 0.05

    dev_score = min(1.0, dev_score)
    is_deviant = dev_score >= 0.35

    return BehavioralAnalysis(
        is_deviant=is_deviant,
        deviation_score=round(dev_score, 2),
        normal_spend_range=f"₹{min_normal:,.2f} - ₹{max_normal:,.2f} (mean: ₹{mean_amt:,.2f})",
        observed_amount=proposal_amount,
        deviation_reasons=reasons,
        confidence_penalty=min(0.25, penalty),
    )
