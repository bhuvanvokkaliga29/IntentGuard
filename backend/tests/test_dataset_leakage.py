"""
IntentGuard — Dataset Leakage Tests

CRITICAL: Ground truth must NEVER be visible to the agent at runtime.
These tests ensure ground_truth_tier and ground_truth_reason never
leak into the agent's runtime payload.
"""

import pytest


class TestDatasetLeakage:
    def test_ground_truth_not_in_runtime_dict(self):
        """transaction_row_to_dict with include_ground_truth=False must exclude ground truth."""
        from backend.db import transaction_row_to_dict

        # Create a mock row-like object
        class MockRow:
            id = "test-123"
            mandate_id = "mandate-001"
            amount = 1400.0
            merchant_name = "Stationery Mart"
            merchant_category = "stationery"
            item_description = "printer paper"
            timestamp = None
            ground_truth_tier = "clearly_in_scope"
            ground_truth_reason = "Test reason"

        row = MockRow()

        # Default: no ground truth
        result = transaction_row_to_dict(row, include_ground_truth=False)
        assert "ground_truth_tier" not in result
        assert "ground_truth_reason" not in result

    def test_ground_truth_present_when_explicitly_requested(self):
        """transaction_row_to_dict with include_ground_truth=True includes ground truth."""
        from backend.db import transaction_row_to_dict

        class MockRow:
            id = "test-123"
            mandate_id = "mandate-001"
            amount = 1400.0
            merchant_name = "Stationery Mart"
            merchant_category = "stationery"
            item_description = "printer paper"
            timestamp = None
            ground_truth_tier = "clearly_in_scope"
            ground_truth_reason = "Test reason"

        row = MockRow()

        result = transaction_row_to_dict(row, include_ground_truth=True)
        assert "ground_truth_tier" in result
        assert result["ground_truth_tier"] == "clearly_in_scope"

    def test_ground_truth_default_excluded(self):
        """Default behavior must exclude ground truth."""
        from backend.db import transaction_row_to_dict

        class MockRow:
            id = "test-123"
            mandate_id = "mandate-001"
            amount = 1400.0
            merchant_name = "Stationery Mart"
            merchant_category = "stationery"
            item_description = "printer paper"
            timestamp = None
            ground_truth_tier = "clearly_in_scope"
            ground_truth_reason = "Test reason"

        row = MockRow()

        # Default (no argument)
        result = transaction_row_to_dict(row)
        assert "ground_truth_tier" not in result
        assert "ground_truth_reason" not in result

    def test_api_key_never_returned(self):
        """Provider info must not expose API keys."""
        from backend.llm.provider import get_provider_info

        info = get_provider_info()
        assert "api_key" not in str(info).lower()
        assert "key" not in info or info.get("key") is None
