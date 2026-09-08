"""
IntentGuard — Contextual Intelligence Subsystem

Provides contextual, temporal, behavioral, novelty, and agent-trust evidence signals
to the deterministic policy engine.
"""

from backend.context.novelty import analyze_transaction_novelty, NoveltyAnalysis
from backend.context.behavioral_baseline import compute_behavioral_baseline, BehavioralAnalysis
from backend.context.temporal import check_temporal_authorization, TemporalAnalysis
from backend.context.agent_context import get_agent_identity, assess_agent_trust, AgentTrustContext
from backend.context.multi_agent import cross_verify_proposals, MultiAgentConsensus

__all__ = [
    "analyze_transaction_novelty",
    "NoveltyAnalysis",
    "compute_behavioral_baseline",
    "BehavioralAnalysis",
    "check_temporal_authorization",
    "TemporalAnalysis",
    "get_agent_identity",
    "assess_agent_trust",
    "AgentTrustContext",
    "cross_verify_proposals",
    "MultiAgentConsensus",
]
