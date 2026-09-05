"""
IntentGuard — Canonical Merchant Normalization Test Suite

Verifies:
1. Positive normalization matches between corporate equivalents (Pvt Ltd, Private Limited, Ltd, LLC, Inc).
2. Negative tests proving non-equivalent or unrelated merchants are rejected (no unsafe fuzzy matching).
"""

import pytest
from backend.policy.hard_constraints import check_merchant_allowed, normalize_merchant_canonical


def test_canonical_normalization_positive_equivalents():
    """Verify legal entity abbreviations normalize to identical canonical representations."""
    # Pvt Ltd vs Private Limited
    assert normalize_merchant_canonical("ABC Stationery Pvt Ltd") == "abc stationery pvt ltd"
    assert normalize_merchant_canonical("ABC Stationery Private Limited") == "abc stationery pvt ltd"
    assert normalize_merchant_canonical("ABC Stationery Pvt. Ltd.") == "abc stationery pvt ltd"

    # Inc vs Incorporated
    assert normalize_merchant_canonical("ABC Tech, Inc.") == "abc tech inc"
    assert normalize_merchant_canonical("ABC Tech Incorporated") == "abc tech inc"

    # LLC vs L.L.C.
    assert normalize_merchant_canonical("Global Goods LLC") == "global goods llc"
    assert normalize_merchant_canonical("Global Goods L.L.C.") == "global goods llc"

    # Ltd vs Limited
    assert normalize_merchant_canonical("Retail Express Ltd") == "retail express ltd"
    assert normalize_merchant_canonical("Retail Express Limited") == "retail express ltd"


def test_merchant_allowed_matches_corporate_variants():
    """Verify check_merchant_allowed accepts valid corporate form variants."""
    allowed = ["ABC Stationery Pvt Ltd", "Global Supplies Inc"]

    # 1. Transaction has 'Private Limited' -> matches 'Pvt Ltd' in allowed list
    res1 = check_merchant_allowed("ABC Stationery Private Limited", allowed)
    assert res1.passed is True
    assert res1.status == "PASS"

    # 2. Transaction has punctuated 'Pvt. Ltd.' -> matches
    res2 = check_merchant_allowed("ABC Stationery Pvt. Ltd.", allowed)
    assert res2.passed is True

    # 3. Transaction has 'Incorporated' -> matches 'Inc'
    res3 = check_merchant_allowed("Global Supplies Incorporated", allowed)
    assert res3.passed is True


def test_merchant_allowed_rejects_unrelated_and_non_matching():
    """Negative tests: verify strict boundary enforcement without fuzzy leakage."""
    allowed = ["ABC Stationery Pvt Ltd"]

    # 1. Completely different merchant -> FAIL
    res_diff = check_merchant_allowed("XYZ Logistics Pvt Ltd", allowed)
    assert res_diff.passed is False
    assert res_diff.status == "FAIL"

    # 2. Different legal entity form (LLC vs Pvt Ltd) -> FAIL
    res_llc = check_merchant_allowed("ABC Stationery LLC", allowed)
    assert res_llc.passed is False

    # 3. Plain name without legal suffix does NOT match Pvt Ltd -> strict separation
    res_plain = check_merchant_allowed("ABC Stationery", allowed)
    assert res_plain.passed is False

    # 4. Partial substring of another merchant -> FAIL
    res_part = check_merchant_allowed("Stationery", allowed)
    assert res_part.passed is False
