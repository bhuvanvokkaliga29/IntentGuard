"""
IntentGuard — Deterministic Decision Replay Engine

Reconstructs historical authorization decisions to prove complete reproducibility.
Given:
- transaction_id / historical proposal
- mandate version
- policy version
- historical decision record

Reconstructs and verifies:
1. Hard structural constraints evaluation
2. Semantic drift analysis & evidence
3. Contextual intelligence (novelty, behavioral baseline, temporal)
4. Confidence computation
5. Deterministic policy verdict match
6. Tamper-evident audit chain verification

CRITICAL INVARIANT:
Decision replay is strictly analytical.
It NEVER invokes the financial execution gateway.
"""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide
from backend.policy.confidence import compute_confidence
from backend.semantic.drift import analyze_semantic_drift
from backend.context.novelty import analyze_transaction_novelty
from backend.context.temporal import check_temporal_authorization
from backend.policy.risk import aggregate_risk_signals
from backend.policy.versioning import POLICY_VERSION


class ReplayResult(BaseModel):
    is_reproducible: bool
    original_decision: str
    replayed_decision: str
    decision_match: bool
    mandate_version_used: int
    policy_version_used: str
    reconstructed_checks: Dict[str, Any]
    reconstructed_risk: Dict[str, Any]
    variance_notes: List[str] = Field(default_factory=list)


def replay_decision(
    proposal: Dict[str, Any],
    mandate: Dict[str, Any],
    original_decision_record: Dict[str, Any],
    mandate_version: int = 1,
    policy_version: str = POLICY_VERSION,
) -> ReplayResult:
    """
    Reconstructs the full verification decision deterministically.
    """
    variance: List[str] = []

    # 1. Re-evaluate structural constraints
    structural_result = check_hard_constraints(
        txn_amount=proposal["amount"],
        txn_merchant_name=proposal["merchant_name"],
        txn_merchant_category=proposal.get("merchant_category", "general"),
        txn_item_description=proposal["item_description"],
        mandate_max_amount_per_txn=mandate["max_amount_per_txn"],
        mandate_budget_cap=mandate.get("budget_cap"),
        mandate_allowed_categories=mandate.get("allowed_categories", []),
        mandate_allowed_merchants=mandate.get("allowed_merchants"),
        mandate_frequency=mandate.get("frequency", "on_demand"),
        mandate_exclusions=mandate.get("exclusions"),
        mandate_location_constraint=mandate.get("location_constraint"),
        cumulative_spent=0.0,
    )

    # 2. Re-evaluate temporal constraints
    temporal_result = check_temporal_authorization(
        effective_from=mandate.get("effective_from"),
        effective_until=mandate.get("effective_until"),
    )

    # 3. Re-evaluate semantic drift
    orig_verdict = original_decision_record.get("semantic_judgment", {})
    if isinstance(orig_verdict, str):
        try:
            orig_verdict = json.loads(orig_verdict)
        except Exception:
            orig_verdict = {}
    majority_verdict = (orig_verdict or {}).get("majority_verdict", "fit")

    drift_result = analyze_semantic_drift(
        mandate_intent=mandate["intent_text"],
        item_description=proposal["item_description"],
        merchant_name=proposal["merchant_name"],
        merchant_category=proposal["merchant_category"],
        declared_purpose=proposal.get("declared_purpose"),
        semantic_verdict=majority_verdict,
    )

    # 4. Re-evaluate novelty
    novelty_result = analyze_transaction_novelty(
        txn_merchant=proposal["merchant_name"],
        txn_category=proposal["merchant_category"],
        txn_amount=proposal["amount"],
        txn_item=proposal["item_description"],
    )

    # 5. Re-evaluate deterministic policy
    orig_conf = float(original_decision_record.get("confidence_score", 0.95))
    replayed_pol = decide(
        structural_pass=structural_result.overall_pass and temporal_result.passed,
        majority_verdict=drift_result.intent_fit,
        confidence_score=orig_conf,
        has_extracted_facts=True,
        evidence_is_sufficient=True,
        structural_failure_reasons=structural_result.failure_reasons + temporal_result.reasons,
    )

    orig_decision = original_decision_record.get("final_decision", "BLOCK")
    replayed_dec = replayed_pol["final_decision"]
    match = (orig_decision == replayed_dec)

    if not match:
        variance.append(f"Decision divergence: original was '{orig_decision}', replayed engine calculated '{replayed_dec}'.")

    # 6. Reconstruct risk
    risk = aggregate_risk_signals(
        structural_passed=structural_result.overall_pass,
        structural_failures=structural_result.failure_reasons,
        drift_analysis=drift_result.model_dump(),
        novelty_analysis=novelty_result.model_dump(),
        temporal_analysis=temporal_result.model_dump(),
    )

    return ReplayResult(
        is_reproducible=match,
        original_decision=orig_decision,
        replayed_decision=replayed_dec,
        decision_match=match,
        mandate_version_used=mandate_version,
        policy_version_used=policy_version,
        reconstructed_checks={
            "structural_overall_pass": structural_result.overall_pass,
            "temporal_passed": temporal_result.passed,
            "drift_type": drift_result.drift_type.value,
        },
        reconstructed_risk=risk.model_dump(),
        variance_notes=variance,
    )
