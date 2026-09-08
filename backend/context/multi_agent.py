"""
IntentGuard — Multi-Agent Cross-Verification Engine

Compares proposals or interpretations across multiple autonomous agents
operating under the same spending mandate.

Examples:
- Buying Agent proposes: "Office productivity laptop ₹65,000"
- Recommendation Agent proposes: "High-end Gaming Laptop ₹140,000"
- Voice Agent transcribes: "User asked for lightweight work machine"

CRITICAL DETERMINISTIC INVARIANT:
Agent voting or agreement NEVER overrides deterministic authorization policy.
Instead, material cross-agent disagreement serves as a risk signal:
- Drops confidence score
- Flags discrepancy in item purpose, category, or amount
- Deterministically routes ambiguous or conflicting interpretations to human ESCALATE.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentProposalSummary(BaseModel):
    agent_id: str
    item_description: str
    amount: float
    category: str
    inferred_purpose: str


class MultiAgentConsensus(BaseModel):
    has_disagreement: bool
    consensus_score: float = Field(..., ge=0.0, le=1.0, description="1.0 = unanimous, 0.0 = total divergence")
    disagreement_signals: List[str] = Field(default_factory=list)
    confidence_adjustment: float = Field(default=0.0, le=0.0, description="Negative penalty to confidence score")
    recommended_policy_action: str = Field(default="NONE", description="'NONE', 'ESCALATE', 'REQUIRE_HUMAN_REVIEW'")


def cross_verify_proposals(
    proposals: List[Dict[str, Any]],
) -> MultiAgentConsensus:
    """
    Compares proposals from multiple agents for the same mandate.
    """
    if not proposals or len(proposals) < 2:
        return MultiAgentConsensus(
            has_disagreement=False,
            consensus_score=1.0,
            disagreement_signals=[],
            confidence_adjustment=0.0,
            recommended_policy_action="NONE",
        )

    amounts = [float(p.get("amount", 0.0)) for p in proposals]
    items = [str(p.get("item_description", "")).lower() for p in proposals]
    categories = [str(p.get("merchant_category", "")).lower() for p in proposals]

    signals: List[str] = []
    penalty = 0.0

    # 1. Price divergence > 50% between agents
    max_amt, min_amt = max(amounts), min(amounts)
    if min_amt > 0 and (max_amt / min_amt) > 1.5:
        signals.append(f"Significant price divergence between agents: min ₹{min_amt:,.2f} vs max ₹{max_amt:,.2f}.")
        penalty -= 0.20

    # 2. Category disagreement
    unique_cats = set(categories)
    if len(unique_cats) > 1:
        signals.append(f"Disagreement on merchant/item category: {list(unique_cats)}.")
        penalty -= 0.25

    # 3. Purpose collision (e.g. gaming vs office)
    has_gaming = any("gaming" in it for it in items)
    has_office = any("office" in it or "work" in it or "stationery" in it for it in items)
    if has_gaming and has_office:
        signals.append("Material semantic conflict: One agent selected gaming/entertainment, another selected office/productivity.")
        penalty -= 0.35

    consensus = max(0.0, 1.0 + penalty)
    has_disagreement = consensus < 0.80
    rec_action = "ESCALATE" if consensus < 0.60 else ("NONE" if not has_disagreement else "REQUIRE_HUMAN_REVIEW")

    return MultiAgentConsensus(
        has_disagreement=has_disagreement,
        consensus_score=round(consensus, 2),
        disagreement_signals=signals,
        confidence_adjustment=penalty,
        recommended_policy_action=rec_action,
    )
