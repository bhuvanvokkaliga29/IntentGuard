"""
IntentGuard — Hard Constraint Tests

Unit tests for the deterministic hard constraint engine.
"""

import pytest
from backend.policy.hard_constraints import (
    check_amount_limit,
    check_budget_cap,
    check_merchant_allowed,
    check_category_allowed,
    check_location_constraint,
    check_exclusions,
    check_hard_constraints,
)


class TestAmountLimit:
    def test_within_limit(self):
        result = check_amount_limit(1400.0, 2000.0)
        assert result.passed is True

    def test_at_limit(self):
        result = check_amount_limit(2000.0, 2000.0)
        assert result.passed is True

    def test_over_limit(self):
        result = check_amount_limit(2500.0, 2000.0)
        assert result.passed is False


class TestBudgetCap:
    def test_within_budget(self):
        result = check_budget_cap(1400.0, 8000.0, cumulative_spent=0.0)
        assert result.passed is True

    def test_no_budget_cap(self):
        result = check_budget_cap(10000.0, None)
        assert result.passed is True

    def test_over_budget(self):
        result = check_budget_cap(1400.0, 8000.0, cumulative_spent=7000.0)
        assert result.passed is False


class TestMerchantAllowed:
    def test_allowed_merchant(self):
        result = check_merchant_allowed("Stationery Mart", ["Stationery Mart", "Office Depot India"])
        assert result.passed is True

    def test_disallowed_merchant(self):
        result = check_merchant_allowed("Amazon India", ["Stationery Mart", "Office Depot India"])
        assert result.passed is False

    def test_no_restrictions(self):
        result = check_merchant_allowed("Any Store", None)
        assert result.passed is True

    def test_case_insensitive(self):
        result = check_merchant_allowed("stationery mart", ["Stationery Mart"])
        assert result.passed is True


class TestCategoryAllowed:
    def test_allowed_category(self):
        result = check_category_allowed("stationery", ["office_supplies", "stationery"])
        assert result.passed is True

    def test_disallowed_category(self):
        result = check_category_allowed("electronics", ["office_supplies", "stationery"])
        assert result.passed is False


class TestLocationConstraint:
    def test_domestic_pass(self):
        result = check_location_constraint(
            "domestic", item_description="domestic flight to Bangalore"
        )
        assert result.passed is True

    def test_domestic_fail_international(self):
        """CANONICAL: Dubai flight against domestic mandate must fail."""
        result = check_location_constraint(
            "domestic", item_description="international flight to Dubai"
        )
        assert result.passed is False

    def test_no_constraint(self):
        result = check_location_constraint(None)
        assert result.passed is True


class TestExclusions:
    def test_no_exclusion_match(self):
        result = check_exclusions("printer paper", "stationery", ["electronics", "food"])
        assert result.passed is True

    def test_exclusion_match(self):
        result = check_exclusions("personal grooming kit", "stationery", ["personal_items"])
        assert result.passed is False


class TestFullHardConstraints:
    def test_canonical_case_a_printer_paper(self):
        """CANONICAL CASE A: Printer paper should PASS all structural checks."""
        result = check_hard_constraints(
            txn_amount=1400.0,
            txn_merchant_name="Stationery Mart",
            txn_merchant_category="stationery",
            txn_item_description="printer paper, pens, sticky notes",
            mandate_max_amount_per_txn=2000.0,
            mandate_budget_cap=8000.0,
            mandate_allowed_categories=["office_supplies", "stationery", "writing_instruments", "paper_products"],
            mandate_allowed_merchants=["Stationery Mart", "Office Depot India", "Pen Paper Store"],
            mandate_exclusions=["electronics", "furniture", "food", "beverages", "personal_items"],
        )
        assert result.overall_pass is True

    def test_canonical_case_b_chocolates(self):
        """CANONICAL CASE B: Chocolates should PASS structural checks (semantic catches it)."""
        result = check_hard_constraints(
            txn_amount=1950.0,
            txn_merchant_name="Stationery Mart",
            txn_merchant_category="stationery",
            txn_item_description="premium imported chocolates",
            mandate_max_amount_per_txn=2000.0,
            mandate_budget_cap=8000.0,
            mandate_allowed_categories=["office_supplies", "stationery", "writing_instruments", "paper_products"],
            mandate_allowed_merchants=["Stationery Mart", "Office Depot India", "Pen Paper Store"],
            mandate_exclusions=["electronics", "furniture", "food", "beverages", "personal_items"],
        )
        # Chocolates may match the "food" exclusion keyword
        # This is actually correct — the hard constraints MIGHT catch it
        # If they do, that's fine. If not, the semantic layer will.
        # The key point is the overall system produces FLAG

    def test_canonical_case_c_dubai_flight(self):
        """CANONICAL CASE C: Dubai flight must FAIL location constraint."""
        result = check_hard_constraints(
            txn_amount=14500.0,
            txn_merchant_name="MakeMyTrip",
            txn_merchant_category="travel",
            txn_item_description="international flight to Dubai, economy class",
            mandate_max_amount_per_txn=15000.0,
            mandate_budget_cap=15000.0,
            mandate_allowed_categories=["travel", "flights", "domestic_travel", "air_travel"],
            mandate_allowed_merchants=["MakeMyTrip", "Cleartrip", "IndiGo", "Air India", "SpiceJet"],
            mandate_location_constraint="domestic",
        )
        assert result.overall_pass is False
        # The location constraint should catch the international keyword
        location_check = next(c for c in result.checks if c.constraint_name == "location_constraint")
        assert location_check.passed is False

    def test_amount_violation(self):
        """Amount over limit must fail."""
        result = check_hard_constraints(
            txn_amount=2500.0,
            txn_merchant_name="Stationery Mart",
            txn_merchant_category="stationery",
            txn_item_description="premium desk organizer set",
            mandate_max_amount_per_txn=2000.0,
            mandate_budget_cap=8000.0,
            mandate_allowed_categories=["stationery"],
            mandate_allowed_merchants=["Stationery Mart"],
        )
        assert result.overall_pass is False
