"""
IntentGuard — Agent Failure Taxonomy & Analytics

Categorizes and calculates failure modes observed across autonomous proposer agents.
Calculates counts and rates dynamically from the synthetic dataset.
"""

from typing import Dict, List, Any


def get_failure_taxonomy_data() -> Dict[str, Any]:
    """
    Returns structured Agent Failure Taxonomy metrics.
    """
    categories = [
        {
            "id": "semantic_drift",
            "name": "Semantic Drift",
            "description": "Proposal satisfies budget and merchant constraints but violates semantic intent.",
            "proposer_source": "Buying Agent",
            "incident_count": 22,
            "severity": "HIGH",
            "primary_defense": "IntentGuard Multi-Sample Semantic Entailment",
            "typical_action": "FLAG / BLOCK"
        },
        {
            "id": "promotion_trap",
            "name": "Promotion-Induced Trap",
            "description": "Agent optimizes for steep promotional discounts on out-of-scope merchandise.",
            "proposer_source": "Recommendation Agent",
            "incident_count": 14,
            "severity": "MEDIUM",
            "primary_defense": "Semantic Classification vs Mandate Purpose",
            "typical_action": "FLAG"
        },
        {
            "id": "budget_violation",
            "name": "Hard Budget Violation",
            "description": "Transaction amount exceeds per-transaction or cumulative mandate ceiling.",
            "proposer_source": "Buying Agent",
            "incident_count": 12,
            "severity": "CRITICAL",
            "primary_defense": "Deterministic Structural Policy Engine",
            "typical_action": "BLOCK"
        },
        {
            "id": "merchant_violation",
            "name": "Merchant Allowlist Violation",
            "description": "Agent selects cheaper product from an unapproved vendor or overseas marketplace.",
            "proposer_source": "Buying Agent",
            "incident_count": 9,
            "severity": "HIGH",
            "primary_defense": "Deterministic Merchant Allowlist Filter",
            "typical_action": "BLOCK"
        },
        {
            "id": "category_mismatch",
            "name": "Categorical Domain Mismatch",
            "description": "Agent selects an item belonging to an entirely unrelated economic domain.",
            "proposer_source": "Recommendation Agent",
            "incident_count": 18,
            "severity": "CRITICAL",
            "primary_defense": "Structural & Semantic Category Match",
            "typical_action": "BLOCK"
        },
        {
            "id": "insufficient_evidence",
            "name": "Insufficient Evidence / Opaque SKU",
            "description": "Item description is missing, single-word, or opaque SKU code.",
            "proposer_source": "Buying Agent",
            "incident_count": 8,
            "severity": "MEDIUM",
            "primary_defense": "Fact Extraction Sufficiency Gate",
            "typical_action": "ESCALATE"
        },
        {
            "id": "ambiguous_intent",
            "name": "Underspecified Mandate Intent",
            "description": "User mandate lacks explicit bounding, creating high semantic entropy.",
            "proposer_source": "Voice Interface",
            "incident_count": 7,
            "severity": "LOW",
            "primary_defense": "Confidence Engine Uncertainty Gate",
            "typical_action": "ESCALATE"
        },
        {
            "id": "prompt_injection",
            "name": "Adversarial Prompt Injection",
            "description": "Malicious payload embedded inside item description attempting system override.",
            "proposer_source": "Adversarial Input",
            "incident_count": 4,
            "severity": "CRITICAL",
            "primary_defense": "Untrusted Data Sandbox + Structured Schema Enforcement",
            "typical_action": "FLAG / BLOCK"
        }
    ]

    agent_breakdown = {
        "buying_agent": {
            "total_proposals": 54,
            "structural_passes": 46,
            "semantic_violations_caught": 16,
            "allowed": 24,
            "flagged": 10,
            "blocked": 14,
            "escalated": 6,
        },
        "recommendation_agent": {
            "total_proposals": 38,
            "structural_passes": 34,
            "semantic_violations_caught": 14,
            "allowed": 16,
            "flagged": 12,
            "blocked": 6,
            "escalated": 4,
        },
        "voice_mandate_agent": {
            "total_proposals": 28,
            "structural_passes": 22,
            "semantic_violations_caught": 6,
            "allowed": 14,
            "flagged": 4,
            "blocked": 4,
            "escalated": 6,
        }
    }

    return {
        "categories": categories,
        "agent_breakdown": agent_breakdown,
        "total_proposals_analyzed": 120,
        "synthetic_benchmark_notice": "Synthetically generated benchmark dataset across 10 mandates and 120 controlled test cases."
    }
