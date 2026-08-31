"""
IntentGuard — Critical System Invariant Tests

Validates the 10+ core security, policy, and architectural invariants
that make IntentGuard safe, robust, and defensible.
"""

import pytest
from backend.policy.hard_constraints import check_hard_constraints, check_exclusions
from backend.policy.confidence import compute_confidence
from backend.policy.decision import decide
from backend.models import (
    FinalDecision,
    SemanticVerdict,
    TransactionRuntime,
    Transaction,
)


class TestCriticalInvariants:
    """Rigorous verification of the architectural and security invariants."""

    def test_invariant_1_structural_failure_never_needs_semantic(self):
        """Invariant: If hard constraint fails, decision is BLOCK without needing semantic judgment."""
        structural = check_hard_constraints(
            txn_amount=5000.0,
            txn_merchant_name="Unapproved Shop",
            txn_merchant_category="electronics",
            txn_item_description="premium gadget",
            mandate_max_amount_per_txn=2000.0,
            mandate_budget_cap=2000.0,
            mandate_allowed_categories=["stationery"],
            mandate_allowed_merchants=["Stationery Mart"],
        )
        assert structural.overall_pass is False

        # Policy decision given structural failure must BLOCK regardless of majority_verdict
        decision = decide(
            structural_pass=structural.overall_pass,
            majority_verdict="fit",  # Even if hypothetical semantic verdict was fit
            confidence_score=1.0,
            structural_failure_reasons=structural.failure_reasons,
        )
        assert decision["final_decision"] == FinalDecision.BLOCK.value
        assert "structural_hard_fail" in decision["decision_path"]

    def test_invariant_2_llm_cannot_directly_authorize(self):
        """Invariant: Semantic verdict alone cannot produce ALLOW if structural checks fail."""
        decision = decide(
            structural_pass=False,
            majority_verdict="fit",
            confidence_score=0.99,
            structural_failure_reasons=["Budget exceeded"],
        )
        assert decision["final_decision"] == FinalDecision.BLOCK.value

    def test_invariant_3_safe_fallback_on_llm_failure_is_escalate(self):
        """Invariant: If LLM fails (no verdict), system escalates to human review, never auto-allows."""
        decision = decide(
            structural_pass=True,
            majority_verdict=None,  # LLM failure or timeout
            confidence_score=0.0,
            has_extracted_facts=False,
            evidence_is_sufficient=False,
        )
        assert decision["final_decision"] == FinalDecision.ESCALATE.value
        assert "ESCALATE" in decision["decision_path"]

    def test_invariant_4_low_confidence_forces_escalation(self):
        """Invariant: Sub-threshold confidence score cannot auto-allow even if verdict is fit."""
        decision = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.55,  # Below high threshold (0.75)
            has_extracted_facts=True,
            evidence_is_sufficient=True,
        )
        assert decision["final_decision"] == FinalDecision.ESCALATE.value

    def test_invariant_5_missing_evidence_forces_escalation(self):
        """Invariant: When evidence is insufficient, system escalates to human review."""
        decision = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.90,
            has_extracted_facts=True,
            evidence_is_sufficient=False,  # e.g., description too vague
        )
        assert decision["final_decision"] == FinalDecision.ESCALATE.value

    def test_invariant_6_ambiguous_verdict_forces_escalation(self):
        """Invariant: AMBIGUOUS semantic verdict routes safely to ESCALATE."""
        decision = decide(
            structural_pass=True,
            majority_verdict="ambiguous",
            confidence_score=0.70,
            has_extracted_facts=True,
            evidence_is_sufficient=True,
        )
        assert decision["final_decision"] == FinalDecision.ESCALATE.value

    def test_invariant_7_confident_semantic_rejection_blocks(self):
        """Invariant: High-confidence NO_FIT on structural pass produces BLOCK."""
        decision = decide(
            structural_pass=True,
            majority_verdict="no_fit",
            confidence_score=0.88,
            has_extracted_facts=True,
            evidence_is_sufficient=True,
        )
        assert decision["final_decision"] == FinalDecision.BLOCK.value

    def test_invariant_8_ground_truth_never_leaks_to_runtime_model(self):
        """Invariant: TransactionRuntime schema contains zero ground truth fields."""
        runtime_fields = TransactionRuntime.model_fields.keys()
        assert "ground_truth_tier" not in runtime_fields
        assert "ground_truth_reason" not in runtime_fields

    def test_invariant_9_confidence_score_is_mathematically_bounded(self):
        """Invariant: Computed confidence score is always strictly in [0.0, 1.0]."""
        structural_mock = {"overall_pass": True}
        # Test across extremes
        for verdicts in [["fit", "fit", "fit"], ["fit", "no_fit", "ambiguous"], [], ["no_fit"]]:
            for amount in [100.0, 1950.0, 10000.0]:
                conf = compute_confidence(
                    structural_result=structural_mock,
                    semantic_verdicts=verdicts,
                    extracted_facts=None,
                    txn_amount=amount,
                    mandate_max_amount=2000.0,
                )
                score = conf["confidence_score"]
                assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for {verdicts}, {amount}"

    def test_invariant_10_exact_three_authorization_outcomes(self):
        """Invariant: Primary decision engine outputs only ALLOW, BLOCK, or ESCALATE."""
        outcomes = {FinalDecision.ALLOW.value, FinalDecision.BLOCK.value, FinalDecision.ESCALATE.value}
        
        # ALLOW case
        d1 = decide(True, "fit", 0.95)
        assert d1["final_decision"] in outcomes
        
        # BLOCK case
        d2 = decide(True, "no_fit", 0.95)
        assert d2["final_decision"] in outcomes
        
        # ESCALATE case
        d3 = decide(True, "ambiguous", 0.50)
        assert d3["final_decision"] in outcomes
