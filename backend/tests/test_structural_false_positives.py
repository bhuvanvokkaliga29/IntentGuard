"""
IntentGuard — Tests for Structural Policy False Positives

Ensures that realistic legitimate items (e.g. printer accessories, multi-item descriptions,
valid merchants) are never falsely rejected by exclusion rules or constraint logic.
"""

import pytest
from backend.policy.hard_constraints import check_hard_constraints, check_exclusions


class TestStructuralFalsePositives:
    """Verifies that legitimate purchases do not get falsely blocked by brittle keyword matches."""

    def test_personal_printer_not_blocked_by_personal_items_exclusion(self):
        """A personal office printer is an office supply, not personal grooming."""
        result = check_exclusions(
            item_description="HP DeskJet personal office printer",
            merchant_category="office_supplies",
            exclusions=["electronics_gadgets", "luxury_personal_items"],
        )
        assert result.passed is True

    def test_cleaning_supplies_not_blocked_by_food_exclusion(self):
        """Disinfectant spray or paper towels must not match food exclusions."""
        result = check_exclusions(
            item_description="Surface disinfectant cleaner and paper towels",
            merchant_category="office_supplies",
            exclusions=["food", "beverages", "alcohol"],
        )
        assert result.passed is True

    def test_case_insensitive_merchant_match(self):
        """Merchant matching must tolerate varied casing without false rejections."""
        result = check_hard_constraints(
            txn_amount=1200.0,
            txn_merchant_name="stationery mart",
            txn_merchant_category="stationery",
            txn_item_description="A4 printing paper reams",
            mandate_max_amount_per_txn=2000.0,
            mandate_budget_cap=5000.0,
            mandate_allowed_categories=["stationery"],
            mandate_allowed_merchants=["Stationery Mart"],
        )
        assert result.overall_pass is True

    def test_exact_budget_boundary_passes(self):
        """A transaction exactly equal to max_amount_per_txn must pass."""
        result = check_hard_constraints(
            txn_amount=2000.0,
            txn_merchant_name="Stationery Mart",
            txn_merchant_category="stationery",
            txn_item_description="executive notebook binder",
            mandate_max_amount_per_txn=2000.0,
            mandate_budget_cap=2000.0,
            mandate_allowed_categories=["stationery"],
            mandate_allowed_merchants=["Stationery Mart"],
        )
        assert result.overall_pass is True
