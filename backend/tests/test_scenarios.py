"""
Tests for all Controlled Failure & Verification Scenarios:
Verifies structural rules and deterministic policies match expected scenario outcomes.
"""

import pytest
from backend.data.scenarios import CONTROLLED_SCENARIOS
from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide
from backend.models import FinalDecision


def test_controlled_scenarios_exist():
    assert len(CONTROLLED_SCENARIOS) >= 8


@pytest.mark.parametrize("scenario", CONTROLLED_SCENARIOS)
def test_each_controlled_scenario_policy(scenario):
    txn = scenario["transaction"]
    mandate_max = scenario["max_amount"]
    allowed_merchants = scenario["allowed_merchants"]

    # Categories for the test
    categories = ["office_supplies", "stationery", "travel", "flights", "groceries", "food", "business_supplies"]

    structural = check_hard_constraints(
        txn_amount=txn["amount"],
        txn_merchant_name=txn["merchant_name"],
        txn_merchant_category=txn["merchant_category"],
        txn_item_description=txn["item_description"],
        mandate_max_amount_per_txn=mandate_max,
        mandate_budget_cap=mandate_max * 4.0,
        mandate_allowed_categories=categories,
        mandate_allowed_merchants=allowed_merchants,
    )

    expected_struct_pass = scenario["structural_check"]["overall_pass"]
    assert structural.overall_pass == expected_struct_pass

    # Evaluate deterministic decision with scenario semantic verdict
    verdict = scenario["semantic_verdict"]
    expected_outcome = scenario["with_intentguard_expected"]

    if expected_outcome == "ESCALATE":
        evidence_sufficient = False
        conf = 0.35
    elif expected_outcome == "FLAG":
        evidence_sufficient = True
        conf = 0.60
    elif expected_outcome == "BLOCK":
        evidence_sufficient = True
        conf = 0.90
    else:  # ALLOW
        evidence_sufficient = True
        conf = 0.95

    decision = decide(
        structural_pass=structural.overall_pass,
        majority_verdict=verdict,
        confidence_score=conf,
        evidence_is_sufficient=evidence_sufficient,
        has_extracted_facts=evidence_sufficient,
        structural_failure_reasons=structural.failure_reasons,
    )

    assert decision["final_decision"] == expected_outcome
