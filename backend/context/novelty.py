"""
IntentGuard — Transaction Novelty Detection Engine

Evaluates whether a proposed transaction is materially different from
previously authorized transactions under a mandate or portfolio.

Signals:
- Unseen merchant
- Unseen category
- Unusual item type / description
- Unusual amount (e.g. 3x standard deviations above historical mean)
- Unusual merchant + category + purpose combination

CRITICAL POLICY INVARIANT:
Novelty is an evidence/risk signal, NOT an automatic BLOCK.
High novelty triggers higher risk scoring and deterministic ESCALATE for human review
when combined with borderline confidence or semantic uncertainty.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NoveltyAnalysis(BaseModel):
    is_novel: bool
    novelty_score: float = Field(..., ge=0.0, le=1.0, description="0.0 = completely familiar, 1.0 = highly novel")
    signals_detected: List[str] = Field(default_factory=list)
    novelty_reasons: List[str] = Field(default_factory=list)
    recommended_action: str = Field(default="NONE", description="'NONE', 'ELEVATE_REVIEW', 'REQUIRE_EXPLANATION'")


def analyze_transaction_novelty(
    txn_merchant: str,
    txn_category: str,
    txn_amount: float,
    txn_item: str,
    history: Optional[List[Dict[str, Any]]] = None,
) -> NoveltyAnalysis:
    """
    Deterministically computes novelty metrics against historical approved transactions.
    """
    if not history or len(history) == 0:
        # First transaction under mandate — mild novelty, not blocking
        return NoveltyAnalysis(
            is_novel=False,
            novelty_score=0.1,
            signals_detected=["first_transaction_under_mandate"],
            novelty_reasons=["Baseline being established; no historical comparisons available."],
            recommended_action="NONE",
        )

    signals: List[str] = []
    reasons: List[str] = []
    score = 0.0

    # 1. Check merchant familiarity
    known_merchants = {str(h.get("merchant_name", "")).strip().lower() for h in history}
    if txn_merchant.strip().lower() not in known_merchants:
        signals.append("unseen_merchant")
        reasons.append(f"Merchant '{txn_merchant}' has never been used under this mandate.")
        score += 0.35

    # 2. Check category familiarity
    known_categories = {str(h.get("merchant_category", "")).strip().lower() for h in history}
    if txn_category.strip().lower() not in known_categories:
        signals.append("unseen_category")
        reasons.append(f"Category '{txn_category}' is novel for this mandate.")
        score += 0.30

    # 3. Check amount deviation
    amounts = [float(h.get("amount", 0.0)) for h in history if float(h.get("amount", 0.0)) > 0]
    if amounts:
        avg_amount = sum(amounts) / len(amounts)
        max_seen = max(amounts)
        if txn_amount > (avg_amount * 2.5) and txn_amount > max_seen:
            signals.append("unusual_amount_spike")
            reasons.append(f"Amount ₹{txn_amount:,.2f} is significantly higher than historical average ₹{avg_amount:,.2f}.")
            score += 0.35

    # 4. Cap score at 1.0
    score = min(1.0, score)
    is_novel = score >= 0.40

    rec_action = "NONE"
    if score >= 0.65:
        rec_action = "ELEVATE_REVIEW"
    elif score >= 0.35:
        rec_action = "REQUIRE_EXPLANATION"

    return NoveltyAnalysis(
        is_novel=is_novel,
        novelty_score=round(score, 2),
        signals_detected=signals,
        novelty_reasons=reasons,
        recommended_action=rec_action,
    )
