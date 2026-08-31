"""
IntentGuard — ML Module: Feature Extraction

Structured features for the optional XGBoost ambiguity/risk calibration model.
Disabled by default — enabled via ML_ENABLED=true.
"""

from typing import Dict, Optional


def extract_ml_features(
    structural_result: Dict,
    extracted_facts: Optional[Dict],
    semantic_judgment: Optional[Dict],
    txn_amount: float,
    mandate_max_amount: float,
    mandate_allowed_categories: list,
) -> Dict:
    """
    Extract structured features for the ML model.
    
    Features:
    - amount_to_limit_ratio
    - merchant_known (from structural check)
    - category_exact_match
    - semantic_score (agreement rate)
    - mandate_specificity (number of constraints)
    - item_description_length
    - hard_constraint_count
    - evidence_completeness
    """
    # Amount ratio
    amount_ratio = txn_amount / mandate_max_amount if mandate_max_amount > 0 else 1.0

    # Check results from structural
    checks = structural_result.get("checks", [])
    merchant_known = any(
        c.get("constraint_name") == "allowed_merchants" and c.get("passed")
        for c in checks
    )
    category_match = any(
        c.get("constraint_name") == "allowed_categories" and c.get("passed")
        for c in checks
    )
    hard_constraint_count = sum(1 for c in checks if not c.get("passed"))

    # Semantic features
    agreement_rate = 0.0
    if semantic_judgment:
        agreement_rate = semantic_judgment.get("agreement_rate", 0.0)

    # Evidence completeness
    evidence_completeness = 0.0
    if extracted_facts:
        key_fields = ["normalized_category", "item_type", "specific_product"]
        filled = sum(1 for f in key_fields if extracted_facts.get(f))
        evidence_completeness = filled / len(key_fields)

    # Mandate specificity
    mandate_specificity = len(mandate_allowed_categories)

    return {
        "amount_to_limit_ratio": round(amount_ratio, 4),
        "merchant_known": 1.0 if merchant_known else 0.0,
        "category_exact_match": 1.0 if category_match else 0.0,
        "semantic_agreement_rate": round(agreement_rate, 4),
        "mandate_specificity": mandate_specificity,
        "item_description_length": 0,  # Set by caller
        "hard_constraint_fail_count": hard_constraint_count,
        "evidence_completeness": round(evidence_completeness, 4),
    }
