"""
IntentGuard — Confidence Engine Tests

Unit tests for deterministic confidence computation.
"""

import pytest
from backend.policy.confidence import compute_confidence, compute_agreement_rate
from backend.models import StructuralResult, ConstraintCheck


def _make_structural_result(overall_pass: bool) -> StructuralResult:
    """Helper to create a StructuralResult."""
    return StructuralResult(
        overall_pass=overall_pass,
        checks=[ConstraintCheck(constraint_name="test", passed=overall_pass, detail="test")],
        failure_reasons=[] if overall_pass else ["test failure"],
    )


class TestAgreementRate:
    def test_full_agreement(self):
        assert compute_agreement_rate(["fit", "fit", "fit"]) == 1.0

    def test_partial_agreement(self):
        rate = compute_agreement_rate(["fit", "fit", "ambiguous"])
        assert abs(rate - 0.6667) < 0.01

    def test_no_agreement(self):
        rate = compute_agreement_rate(["fit", "no_fit", "ambiguous"])
        assert abs(rate - 0.3333) < 0.01

    def test_empty(self):
        assert compute_agreement_rate([]) == 0.0


class TestConfidenceComputation:
    def test_high_agreement_high_confidence(self):
        """Full agreement → high confidence."""
        structural = _make_structural_result(True)
        result = compute_confidence(
            structural_result=structural,
            semantic_verdicts=["fit", "fit", "fit"],
            extracted_facts={"normalized_category": "office_supplies", "item_type": "paper", "specific_product": "A4"},
            txn_amount=1400.0,
            mandate_max_amount=2000.0,
        )
        assert result["confidence_score"] >= 0.75

    def test_low_agreement_low_confidence(self):
        """Total disagreement → low confidence."""
        structural = _make_structural_result(True)
        result = compute_confidence(
            structural_result=structural,
            semantic_verdicts=["fit", "no_fit", "ambiguous"],
            extracted_facts={"normalized_category": "unknown", "item_type": "unknown", "specific_product": None},
            txn_amount=1400.0,
            mandate_max_amount=2000.0,
        )
        assert result["confidence_score"] < 0.50

    def test_amount_proximity_penalty(self):
        """Amount near limit reduces confidence."""
        structural = _make_structural_result(True)

        # Well under limit
        result_low = compute_confidence(
            structural_result=structural,
            semantic_verdicts=["fit", "fit", "fit"],
            extracted_facts={"normalized_category": "office_supplies", "item_type": "paper", "specific_product": "A4"},
            txn_amount=500.0,
            mandate_max_amount=2000.0,
        )

        # Near limit
        result_high = compute_confidence(
            structural_result=structural,
            semantic_verdicts=["fit", "fit", "fit"],
            extracted_facts={"normalized_category": "office_supplies", "item_type": "paper", "specific_product": "A4"},
            txn_amount=1950.0,
            mandate_max_amount=2000.0,
        )

        assert result_low["confidence_score"] >= result_high["confidence_score"]

    def test_hard_mismatch_penalty(self):
        """Domestic/international mismatch reduces confidence."""
        structural = _make_structural_result(True)
        result = compute_confidence(
            structural_result=structural,
            semantic_verdicts=["no_fit", "no_fit", "no_fit"],
            extracted_facts={"domestic_or_international": "international", "normalized_category": "travel", "item_type": "flight", "specific_product": None},
            txn_amount=14500.0,
            mandate_max_amount=15000.0,
            mandate_location_constraint="domestic",
        )
        # Should have hard mismatch penalty
        assert "hard_location_mismatch" in result["adjustments"]

    def test_structural_fail_low_confidence(self):
        """Structural failure → low confidence for non-BLOCK decisions."""
        structural = _make_structural_result(False)
        result = compute_confidence(
            structural_result=structural,
            semantic_verdicts=["fit", "fit", "fit"],
            extracted_facts={"normalized_category": "office_supplies", "item_type": "paper", "specific_product": "A4"},
            txn_amount=2500.0,
            mandate_max_amount=2000.0,
        )
        # Structural fail penalty should be applied
        assert "structural_fail_penalty" in result["adjustments"]
