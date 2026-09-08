"""
IntentGuard — Proposal Risk Signal Aggregator

Synthesizes multi-dimensional verification evidence into a structured risk profile:
- Structural violations
- Prompt injection & adversarial indicators
- Semantic drift & purpose mismatch
- Transaction novelty
- Behavioral deviations
- Temporal validity
- Multi-agent divergence
- Agent trust & operational reliability

CRITICAL ARCHITECTURAL PRINCIPLE:
Risk signal aggregation generates STRUCTURED EVIDENCE ONLY.
It does NOT authorize or decline transactions on its own.
The deterministic policy engine remains the sole authority for:
ALLOW / BLOCK / ESCALATE.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RiskSignal(BaseModel):
    category: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    score_impact: float


class ProposalRiskProfile(BaseModel):
    aggregate_risk_score: float = Field(..., ge=0.0, le=1.0, description="0.0 = minimal risk, 1.0 = extreme risk")
    risk_level: str = Field(..., description="'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'")
    active_signals: List[RiskSignal] = Field(default_factory=list)
    suggested_review_priority: str = Field(default="NORMAL", description="'ROUTINE', 'NORMAL', 'HIGH', 'URGENT'")


def aggregate_risk_signals(
    structural_passed: bool,
    structural_failures: Optional[List[str]] = None,
    security_violation: Optional[str] = None,
    drift_analysis: Optional[Dict[str, Any]] = None,
    novelty_analysis: Optional[Dict[str, Any]] = None,
    behavioral_analysis: Optional[Dict[str, Any]] = None,
    temporal_analysis: Optional[Dict[str, Any]] = None,
    multi_agent_consensus: Optional[Dict[str, Any]] = None,
    agent_trust: Optional[Dict[str, Any]] = None,
) -> ProposalRiskProfile:
    """
    Deterministically aggregates evidence signals into an explainable risk profile.
    """
    signals: List[RiskSignal] = []
    base_score = 0.0

    # 1. Security / Prompt Injection (CRITICAL)
    if security_violation:
        signals.append(RiskSignal(
            category="SECURITY_ADVERSARIAL",
            severity="CRITICAL",
            description=f"Adversarial prompt injection detected: {security_violation}",
            score_impact=1.0,
        ))
        base_score = 1.0

    # 2. Structural hard violations (HIGH)
    if not structural_passed:
        reasons = structural_failures or ["Hard constraint failure"]
        signals.append(RiskSignal(
            category="STRUCTURAL_POLICY",
            severity="HIGH",
            description=f"Structural hard constraint breached: {'; '.join(reasons)}",
            score_impact=0.8,
        ))
        base_score = max(base_score, 0.85)

    # 3. Semantic Drift (HIGH/MEDIUM)
    if drift_analysis:
        drift_type = drift_analysis.get("drift_type", "aligned")
        if drift_type not in ("aligned",):
            sev = "HIGH" if drift_type in ("purpose_substitution", "suspicious_justification") else "MEDIUM"
            impact = drift_analysis.get("risk_contribution", 0.6)
            signals.append(RiskSignal(
                category="SEMANTIC_DRIFT",
                severity=sev,
                description=f"Semantic drift identified: {drift_type} ({'; '.join(drift_analysis.get('evidence', []))})",
                score_impact=impact,
            ))
            base_score += impact * 0.4

    # 4. Temporal constraints (HIGH/MEDIUM)
    if temporal_analysis and not temporal_analysis.get("passed", True):
        signals.append(RiskSignal(
            category="TEMPORAL_VALIDITY",
            severity="HIGH",
            description="; ".join(temporal_analysis.get("reasons", ["Temporal constraint failed"])),
            score_impact=0.7,
        ))
        base_score = max(base_score, 0.75)

    # 5. Novelty (LOW/MEDIUM)
    if novelty_analysis and novelty_analysis.get("is_novel"):
        nov_score = novelty_analysis.get("novelty_score", 0.0)
        signals.append(RiskSignal(
            category="NOVELTY_CONTEXT",
            severity="MEDIUM" if nov_score >= 0.6 else "LOW",
            description="; ".join(novelty_analysis.get("novelty_reasons", ["Novel transaction patterns detected"])),
            score_impact=nov_score * 0.3,
        ))
        base_score += nov_score * 0.15

    # 6. Behavioral baseline deviation (LOW/MEDIUM)
    if behavioral_analysis and behavioral_analysis.get("is_deviant"):
        dev_score = behavioral_analysis.get("deviation_score", 0.0)
        signals.append(RiskSignal(
            category="BEHAVIORAL_BASELINE",
            severity="MEDIUM" if dev_score >= 0.5 else "LOW",
            description="; ".join(behavioral_analysis.get("deviation_reasons", ["Spending baseline deviation"])),
            score_impact=dev_score * 0.3,
        ))
        base_score += dev_score * 0.15

    # 7. Multi-agent divergence (MEDIUM)
    if multi_agent_consensus and multi_agent_consensus.get("has_disagreement"):
        signals.append(RiskSignal(
            category="MULTI_AGENT_CONSENSUS",
            severity="MEDIUM",
            description="; ".join(multi_agent_consensus.get("disagreement_signals", ["Agent divergence detected"])),
            score_impact=0.4,
        ))
        base_score += 0.20

    # 8. Agent trust factor
    if agent_trust and agent_trust.get("trust_score", 1.0) < 0.4:
        signals.append(RiskSignal(
            category="AGENT_RELIABILITY",
            severity="MEDIUM",
            description=f"Proposing agent has restricted operational trust ({agent_trust.get('trust_score'):.2f}).",
            score_impact=0.3,
        ))
        base_score += 0.10

    total_score = round(min(1.0, max(0.05, base_score)), 2)

    if total_score >= 0.85:
        level = "CRITICAL"
        priority = "URGENT"
    elif total_score >= 0.60:
        level = "HIGH"
        priority = "HIGH"
    elif total_score >= 0.35:
        level = "MEDIUM"
        priority = "NORMAL"
    else:
        level = "LOW"
        priority = "ROUTINE"

    return ProposalRiskProfile(
        aggregate_risk_score=total_score,
        risk_level=level,
        active_signals=signals,
        suggested_review_priority=priority,
    )
