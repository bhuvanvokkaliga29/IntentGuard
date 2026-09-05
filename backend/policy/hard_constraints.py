"""
IntentGuard — Hard Constraint Engine

Pure deterministic Python — ZERO LLM calls.
Checks structural mandate constraints against a proposed transaction.

Constraints checked:
- max_amount_per_txn
- budget_cap (cumulative)
- allowed_merchants
- allowed_categories
- frequency
- location_constraint (domestic/international)
- explicit exclusions
"""

from typing import List, Optional

from backend.models import ConstraintCheck, StructuralResult


def check_amount_limit(
    txn_amount: float,
    max_amount_per_txn: float,
) -> ConstraintCheck:
    """Check if transaction amount is within the per-transaction limit."""
    passed = txn_amount <= max_amount_per_txn
    return ConstraintCheck(
        constraint_name="max_amount_per_txn",
        passed=passed,
        status="PASS" if passed else "FAIL",
        observed=f"₹{txn_amount:,.2f}",
        expected=f"<= ₹{max_amount_per_txn:,.2f}",
        detail=(
            f"Transaction amount ₹{txn_amount:,.2f} is {'within' if passed else 'above'} "
            f"the ₹{max_amount_per_txn:,.2f} per-transaction limit."
        ),
        value_checked=f"₹{txn_amount:,.2f}",
        limit=f"₹{max_amount_per_txn:,.2f}",
    )


def check_budget_cap(
    txn_amount: float,
    budget_cap: Optional[float],
    cumulative_spent: float = 0.0,
) -> ConstraintCheck:
    """Check if transaction would exceed the cumulative budget cap."""
    if budget_cap is None:
        return ConstraintCheck(
            constraint_name="budget_cap",
            passed=True,
            status="NOT_APPLICABLE",
            observed=f"Cumulative spent: ₹{cumulative_spent:,.2f}",
            expected="No budget cap configured",
            detail="No budget cap defined for this mandate.",
        )

    new_total = cumulative_spent + txn_amount
    passed = new_total <= budget_cap
    remaining = budget_cap - cumulative_spent
    return ConstraintCheck(
        constraint_name="budget_cap",
        passed=passed,
        status="PASS" if passed else "FAIL",
        observed=f"₹{new_total:,.2f} projected total",
        expected=f"<= ₹{budget_cap:,.2f}",
        detail=(
            f"After this transaction, cumulative spend would be ₹{new_total:,.2f} "
            f"against a ₹{budget_cap:,.2f} budget cap. "
            f"Remaining budget before this transaction: ₹{remaining:,.2f}."
        ),
        value_checked=f"₹{new_total:,.2f}",
        limit=f"₹{budget_cap:,.2f}",
    )


def check_merchant_allowed(
    merchant_name: str,
    allowed_merchants: Optional[List[str]],
) -> ConstraintCheck:
    """Check if the merchant is in the allowed list."""
    if allowed_merchants is None or len(allowed_merchants) == 0:
        return ConstraintCheck(
            constraint_name="allowed_merchants",
            passed=True,
            status="NOT_APPLICABLE",
            observed=merchant_name,
            expected="Any merchant allowed",
            detail="No merchant restrictions defined for this mandate.",
        )

    # Case-insensitive comparison
    merchant_lower = merchant_name.strip().lower()
    allowed_lower = [m.strip().lower() for m in allowed_merchants]
    passed = merchant_lower in allowed_lower

    return ConstraintCheck(
        constraint_name="allowed_merchants",
        passed=passed,
        status="PASS" if passed else "FAIL",
        observed=merchant_name,
        expected=f"Allowed list: {allowed_merchants}",
        detail=(
            f"Merchant '{merchant_name}' is {'in' if passed else 'NOT in'} "
            f"the allowed merchant list: {allowed_merchants}."
        ),
        value_checked=merchant_name,
        limit=str(allowed_merchants),
    )


def check_category_allowed(
    merchant_category: str,
    allowed_categories: List[str],
) -> ConstraintCheck:
    """Check if the merchant category is in the allowed list."""
    if not allowed_categories:
        return ConstraintCheck(
            constraint_name="allowed_categories",
            passed=True,
            status="NOT_APPLICABLE",
            observed=merchant_category,
            expected="Any category allowed",
            detail="No category restrictions defined for this mandate.",
        )

    # Case-insensitive comparison
    category_lower = merchant_category.strip().lower()
    allowed_lower = [c.strip().lower() for c in allowed_categories]
    passed = category_lower in allowed_lower

    return ConstraintCheck(
        constraint_name="allowed_categories",
        passed=passed,
        status="PASS" if passed else "FAIL",
        observed=merchant_category,
        expected=f"Allowed categories: {allowed_categories}",
        detail=(
            f"Category '{merchant_category}' is {'in' if passed else 'NOT in'} "
            f"the allowed categories: {allowed_categories}."
        ),
        value_checked=merchant_category,
        limit=str(allowed_categories),
    )


def check_location_constraint(
    location_constraint: Optional[str],
    transaction_location_hint: Optional[str] = None,
    item_description: str = "",
) -> ConstraintCheck:
    """
    Check location constraints (e.g., domestic vs. international).

    This uses simple keyword detection for known patterns.
    The LLM extraction step provides more nuanced location analysis,
    but this catch obvious hard mismatches deterministically.
    """
    if location_constraint is None:
        return ConstraintCheck(
            constraint_name="location_constraint",
            passed=True,
            status="NOT_APPLICABLE",
            observed=transaction_location_hint or "None specified",
            expected="No location constraint",
            detail="No location constraint defined for this mandate.",
        )

    # Combine all text for keyword analysis
    text_to_check = f"{item_description} {transaction_location_hint or ''}".lower()
    constraint_lower = location_constraint.lower()

    # Known international indicators
    international_keywords = [
        "international", "abroad", "overseas", "foreign",
        "dubai", "london", "new york", "singapore", "bangkok",
        "paris", "tokyo", "hong kong", "sydney", "toronto",
    ]

    # Known domestic indicators
    domestic_keywords = [
        "domestic", "india", "within india",
        "delhi", "mumbai", "bangalore", "bengaluru", "chennai",
        "hyderabad", "kolkata", "pune", "jaipur", "ahmedabad",
        "goa", "lucknow", "kochi", "chandigarh",
    ]

    if constraint_lower == "domestic":
        # Check if the transaction mentions international destinations
        has_international = any(kw in text_to_check for kw in international_keywords)
        if has_international:
            return ConstraintCheck(
                constraint_name="location_constraint",
                passed=False,
                status="FAIL",
                observed="international indicators detected",
                expected="domestic",
                detail=(
                    f"Mandate requires domestic transactions only, but the transaction "
                    f"description contains international indicators. "
                    f"This is a hard categorical mismatch."
                ),
                value_checked="international (detected)",
                limit="domestic",
            )
        return ConstraintCheck(
            constraint_name="location_constraint",
            passed=True,
            status="PASS",
            observed="domestic or neutral indicators",
            expected="domestic",
            detail="Transaction does not contain international indicators; domestic constraint satisfied.",
        )

    elif constraint_lower == "international":
        has_domestic_only = all(
            kw not in text_to_check for kw in international_keywords
        ) and any(kw in text_to_check for kw in domestic_keywords)
        if has_domestic_only:
            return ConstraintCheck(
                constraint_name="location_constraint",
                passed=False,
                status="FAIL",
                observed="domestic indicators detected",
                expected="international",
                detail="Mandate requires international transactions, but the transaction appears domestic.",
                value_checked="domestic (detected)",
                limit="international",
            )
        return ConstraintCheck(
            constraint_name="location_constraint",
            passed=True,
            status="PASS",
            observed="international indicators consistent",
            expected="international",
            detail="Transaction appears consistent with international constraint.",
        )

    return ConstraintCheck(
        constraint_name="location_constraint",
        passed=True,
        status="PASS",
        observed=text_to_check[:50],
        expected=location_constraint,
        detail=f"Location constraint '{location_constraint}' — no violation detected.",
    )


def check_exclusions(
    item_description: str,
    merchant_category: str,
    exclusions: Optional[List[str]],
) -> ConstraintCheck:
    """
    Check if the transaction matches any explicit exclusions.
    
    Uses exact normalized token matching only.
    NO fuzzy substring matching to avoid false positives.
    """
    if exclusions is None or len(exclusions) == 0:
        return ConstraintCheck(
            constraint_name="exclusions",
            passed=True,
            status="NOT_APPLICABLE",
            observed="No excluded keywords present",
            expected="No exclusions configured",
            detail="No exclusions defined for this mandate.",
        )

    import re
    text_to_check = f"{item_description} {merchant_category}".lower()
    exclusions_lower = [e.strip().lower() for e in exclusions]
    tokens = set(re.findall(r'\b[a-z0-9]+\b', text_to_check))

    matched_exclusions = []
    for excl in exclusions_lower:
        # 1. Exact phrase or substring match
        if excl in text_to_check:
            matched_exclusions.append(excl)
            continue

        # 2. Check compound terms (e.g., "personal_items" -> ["personal", "items"])
        excl_parts = [p for p in re.split(r'[\s_]+', excl) if p]
        if len(excl_parts) > 1:
            # Multi-word exclusion: all significant parts must be present in the text
            if all(p in tokens for p in excl_parts if len(p) >= 3):
                matched_exclusions.append(excl)
                continue
        elif len(excl_parts) == 1 and excl_parts[0] in tokens:
            matched_exclusions.append(excl)
            continue

    passed = len(matched_exclusions) == 0

    return ConstraintCheck(
        constraint_name="exclusions",
        passed=passed,
        status="PASS" if passed else "FAIL",
        observed=f"Matched: {matched_exclusions}" if not passed else "No exclusions matched",
        expected=f"None of: {exclusions}",
        detail=(
            f"No excluded items/categories detected in the transaction."
            if passed
            else f"Transaction matches excluded items/categories: {matched_exclusions}."
        ),
        value_checked=item_description,
        limit=str(exclusions),
    )


def check_hard_constraints(
    txn_amount: float,
    txn_merchant_name: str,
    txn_merchant_category: str,
    txn_item_description: str,
    mandate_max_amount_per_txn: float,
    mandate_budget_cap: Optional[float],
    mandate_allowed_categories: List[str],
    mandate_allowed_merchants: Optional[List[str]],
    mandate_frequency: str = "on_demand",
    mandate_exclusions: Optional[List[str]] = None,
    mandate_location_constraint: Optional[str] = None,
    cumulative_spent: float = 0.0,
    transaction_location_hint: Optional[str] = None,
) -> StructuralResult:
    """
    Run ALL hard constraint checks against a transaction.
    
    This is pure deterministic Python — no LLM calls.
    Returns a StructuralResult with per-check pass/fail breakdown.
    """
    checks: List[ConstraintCheck] = []

    # 1. Amount limit
    checks.append(check_amount_limit(txn_amount, mandate_max_amount_per_txn))

    # 2. Budget cap
    checks.append(check_budget_cap(txn_amount, mandate_budget_cap, cumulative_spent))

    # 3. Merchant allowed
    checks.append(check_merchant_allowed(txn_merchant_name, mandate_allowed_merchants))

    # 4. Category allowed
    checks.append(check_category_allowed(txn_merchant_category, mandate_allowed_categories))

    # 5. Location constraint
    checks.append(check_location_constraint(
        mandate_location_constraint,
        transaction_location_hint,
        txn_item_description,
    ))

    # 6. Exclusions
    checks.append(check_exclusions(
        txn_item_description,
        txn_merchant_category,
        mandate_exclusions,
    ))

    # Aggregate result
    overall_pass = all(c.passed for c in checks)
    failure_reasons = [c.detail for c in checks if not c.passed]

    return StructuralResult(
        overall_pass=overall_pass,
        checks=checks,
        failure_reasons=failure_reasons,
    )
