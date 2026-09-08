"""
IntentGuard — Agent Identity & Trust Context Engine

Maintains explicit identities and operational reliability metrics for autonomous proposer agents.
Tracks:
- Agent ID & Type (Buying, Recommendation, Voice)
- Version & declared capabilities
- Historical proposal count & approval rate
- Policy violation count
- Escalation frequency

CRITICAL ARCHITECTURAL INVARIANT:
The Agent Trust Score is an OPERATIONAL EVIDENCE SIGNAL ONLY.
- A high trust score CANNOT bypass deterministic hard constraints or semantic policy.
- An untrusted agent cannot authorize anything.
- High violation counts decrease trust and lower the threshold for human escalation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentIdentity(BaseModel):
    agent_id: str
    agent_type: str
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=lambda: ["propose_transactions"])
    is_sandboxed: bool = True
    can_execute_payments: bool = False  # MUST ALWAYS BE FALSE


class AgentTrustContext(BaseModel):
    agent_id: str
    agent_type: str
    trust_score: float = Field(..., ge=0.0, le=1.0, description="0.0 = untrusted, 1.0 = highly reliable")
    historical_proposals: int = 0
    approved_count: int = 0
    blocked_count: int = 0
    escalated_count: int = 0
    policy_violations: int = 0
    trust_tier: str = Field(default="STANDARD", description="'RESTRICTED', 'STANDARD', 'VERIFIED'")
    evidence_notes: List[str] = Field(default_factory=list)


# In-memory agent registry tracking operational metrics
_AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "buying_agent": {
        "agent_id": "buying_agent_v1",
        "agent_type": "buying_agent",
        "version": "1.0.0",
        "capabilities": ["catalog_search", "propose_purchase"],
        "proposals": 120,
        "approved": 95,
        "blocked": 15,
        "escalated": 10,
        "violations": 2,
    },
    "recommendation_agent": {
        "agent_id": "rec_agent_v1",
        "agent_type": "recommendation_agent",
        "version": "1.0.0",
        "capabilities": ["deal_lookup", "propose_bundle"],
        "proposals": 85,
        "approved": 52,
        "blocked": 20,
        "escalated": 13,
        "violations": 3,
    },
    "voice_agent": {
        "agent_id": "voice_agent_v1",
        "agent_type": "voice_mandate_agent",
        "version": "1.0.0",
        "capabilities": ["speech_transcription", "propose_order"],
        "proposals": 45,
        "approved": 38,
        "blocked": 4,
        "escalated": 3,
        "violations": 0,
    },
}


def get_agent_identity(agent_id_or_type: str) -> AgentIdentity:
    """Returns static verified identity proving proposal-only sandboxing."""
    clean = agent_id_or_type.strip().lower()
    for k, v in _AGENT_REGISTRY.items():
        if k in clean or v["agent_id"] == clean:
            return AgentIdentity(
                agent_id=v["agent_id"],
                agent_type=v["agent_type"],
                version=v["version"],
                capabilities=v["capabilities"],
                is_sandboxed=True,
                can_execute_payments=False,
            )
    return AgentIdentity(
        agent_id=clean or "unknown_agent",
        agent_type="external_proposer",
        version="0.1.0",
        capabilities=["propose_transactions"],
        is_sandboxed=True,
        can_execute_payments=False,
    )


def assess_agent_trust(agent_id_or_type: str) -> AgentTrustContext:
    """
    Computes a bounded operational trust score between 0.0 and 1.0.
    """
    clean = agent_id_or_type.strip().lower()
    data = None
    for k, v in _AGENT_REGISTRY.items():
        if k in clean or v["agent_id"] == clean:
            data = v
            break

    if not data:
        return AgentTrustContext(
            agent_id=clean,
            agent_type="unknown",
            trust_score=0.5,
            trust_tier="RESTRICTED",
            evidence_notes=["Unknown or newly registered agent; restricted trust applied."],
        )

    props = max(1, data["proposals"])
    app_rate = data["approved"] / props
    violation_rate = data["violations"] / props

    # Bounded score calculation: base 0.5 + 0.5 * app_rate - penalty
    score = 0.5 + (0.4 * app_rate) - (0.5 * violation_rate)
    score = max(0.1, min(0.95, score))

    tier = "VERIFIED" if score >= 0.75 else ("STANDARD" if score >= 0.45 else "RESTRICTED")
    notes = [
        f"Agent historical approval rate: {app_rate:.1%}.",
        f"Total policy violations on record: {data['violations']}.",
    ]

    return AgentTrustContext(
        agent_id=data["agent_id"],
        agent_type=data["agent_type"],
        trust_score=round(score, 2),
        historical_proposals=data["proposals"],
        approved_count=data["approved"],
        blocked_count=data["blocked"],
        escalated_count=data["escalated"],
        policy_violations=data["violations"],
        trust_tier=tier,
        evidence_notes=notes,
    )
