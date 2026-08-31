"""
Tests for Safe Failure Modes:
Verifies that LLM timeouts, malformed JSON, missing evidence, and low confidence
safely ESCALATE or BLOCK rather than silently ALLOWing.
"""

import pytest
from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide
from backend.models import FinalDecision


def test_insufficient_evidence_escalates():
    """When item description is missing or uninformative, decision must ESCALATE."""
    structural = check_hard_constraints(
        txn_amount=1750.0,
        txn_merchant_name="Stationery Mart",
        txn_merchant_category="stationery",
        txn_item_description="miscellaneous item",
        mandate_max_amount_per_txn=2000.0,
        mandate_budget_cap=8000.0,
        mandate_allowed_categories=["office_supplies", "stationery"],
        mandate_allowed_merchants=["Stationery Mart"],
    )
    assert structural.overall_pass is True

    decision = decide(
        structural_pass=structural.overall_pass,
        majority_verdict="ambiguous",
        confidence_score=0.35,
        has_extracted_facts=False,
        evidence_is_sufficient=False,
    )
    assert decision["final_decision"] == FinalDecision.ESCALATE.value


def test_low_confidence_escalates():
    """Even if verdict is 'fit', confidence below low threshold must ESCALATE."""
    structural = check_hard_constraints(
        txn_amount=1400.0,
        txn_merchant_name="Stationery Mart",
        txn_merchant_category="stationery",
        txn_item_description="some items",
        mandate_max_amount_per_txn=2000.0,
        mandate_budget_cap=8000.0,
        mandate_allowed_categories=["office_supplies", "stationery"],
        mandate_allowed_merchants=["Stationery Mart"],
    )

    decision = decide(
        structural_pass=structural.overall_pass,
        majority_verdict="fit",
        confidence_score=0.30,  # Below confidence threshold (< 0.40)
    )
    assert decision["final_decision"] == FinalDecision.ESCALATE.value


def test_unparseable_output_safe_fallback():
    """Fallback when semantic analyzer cannot parse output."""
    structural = check_hard_constraints(
        txn_amount=1950.0,
        txn_merchant_name="Stationery Mart",
        txn_merchant_category="stationery",
        txn_item_description="test item",
        mandate_max_amount_per_txn=2000.0,
        mandate_budget_cap=8000.0,
        mandate_allowed_categories=["office_supplies", "stationery"],
        mandate_allowed_merchants=["Stationery Mart"],
    )

    decision = decide(
        structural_pass=structural.overall_pass,
        majority_verdict=None,
        confidence_score=0.0,
        has_extracted_facts=False,
    )
    assert decision["final_decision"] == FinalDecision.ESCALATE.value
