"""
IntentGuard — Semantic Drift Detection Engine

Primary intelligence module comparing Mandate Intent vs Transaction Intent.
Identifies subtle semantic drift where transactions appear structurally valid
(amount, category, merchant) but diverge from the delegated human purpose.

Drift Types:
- aligned: Transaction directly matches mandate purpose
- partially_aligned: Partially matching with non-trivial ambiguity
- ambiguous: Unclear intent or under-specified proposal
- outside_mandate: Clear violation of core intent
- purpose_substitution: Replacing intended utility with an unapproved utility (e.g. gaming for work)
- category_drift: Semantic category departure despite valid high-level taxonomy
- contextual_drift: Valid item in an invalid operational context (e.g. personal luxury during travel)
- merchant_purpose_mismatch: Legitimate merchant selling outside the mandate scope
- suspicious_justification: Proposer provides misleading or adversarial rationalizations

Outputs structured, explainable decision evidence. ZERO private chain-of-thought exposed.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DriftType(str, Enum):
    ALIGNED = "aligned"
    PARTIALLY_ALIGNED = "partially_aligned"
    AMBIGUOUS = "ambiguous"
    OUTSIDE_MANDATE = "outside_mandate"
    PURPOSE_SUBSTITUTION = "purpose_substitution"
    CATEGORY_DRIFT = "category_drift"
    CONTEXTUAL_DRIFT = "contextual_drift"
    MERCHANT_PURPOSE_MISMATCH = "merchant_purpose_mismatch"
    SUSPICIOUS_JUSTIFICATION = "suspicious_justification"


class SemanticDriftAnalysis(BaseModel):
    """Structured evidence output from the Semantic Drift Engine."""
    intent_fit: str = Field(..., description="'fit', 'no_fit', or 'ambiguous'")
    drift_type: DriftType
    is_drift_detected: bool
    evidence: List[str] = Field(default_factory=list, description="Concise, factual decision evidence")
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_contribution: float = Field(default=0.0, ge=0.0, le=1.0)


def analyze_semantic_drift(
    mandate_intent: str,
    item_description: str,
    merchant_name: str,
    merchant_category: str,
    declared_purpose: Optional[str] = None,
    extracted_facts: Optional[Dict[str, Any]] = None,
    semantic_verdict: Optional[str] = None,
    agreement_rate: float = 1.0,
) -> SemanticDriftAnalysis:
    """
    Deterministic rule & evidence synthesizer that categorizes semantic drift.
    Operates consistently on mock data, unit tests, and live provider extractions.
    """
    intent_lower = mandate_intent.lower()
    item_lower = item_description.lower()
    merchant_lower = merchant_name.lower()
    purpose_lower = (declared_purpose or "").lower()

    evidence: List[str] = []
    drift_type = DriftType.ALIGNED
    intent_fit = "fit"
    confidence = 0.90
    risk_contrib = 0.0

    # 1. Check for purpose substitution (e.g., gaming console or luxury replacing work tools)
    gaming_keywords = ["gaming", "playstation", "xbox", "nintendo", "steam deck", "gpu", "rtx"]
    luxury_keywords = ["luxury", "rolex", "caviar", "champagne", "spa resort", "5-star luxury"]
    office_intent = any(k in intent_lower for k in ["office", "stationery", "work", "supplies", "team"])

    if office_intent and any(k in item_lower for k in gaming_keywords):
        drift_type = DriftType.PURPOSE_SUBSTITUTION
        intent_fit = "no_fit"
        evidence.append(f"Item '{item_description}' represents entertainment/gaming equipment substituting for office productivity.")
        confidence = 0.95
        risk_contrib = 0.85

    elif any(k in item_lower for k in luxury_keywords) and not ("luxury" in intent_lower):
        drift_type = DriftType.PURPOSE_SUBSTITUTION
        intent_fit = "no_fit"
        evidence.append(f"Proposal contains luxury goods/services exceeding delegated mandate scope.")
        confidence = 0.92
        risk_contrib = 0.80

    # 2. Check for suspicious justification (e.g. trying to justify personal items)
    suspicious_triggers = ["personal upgrade", "personal recreation", "treat for self", "entertainment for home"]
    if any(k in purpose_lower for k in suspicious_triggers):
        drift_type = DriftType.SUSPICIOUS_JUSTIFICATION
        intent_fit = "no_fit"
        evidence.append(f"Declared purpose '{declared_purpose}' indicates non-business/personal expenditure.")
        confidence = 0.94
        risk_contrib = 0.90

    # 3. Check for merchant-purpose mismatch (e.g. food delivery merchant for flights)
    flight_intent = any(k in intent_lower for k in ["flight", "travel", "airline"])
    if flight_intent and any(m in merchant_lower for m in ["swiggy", "zomato", "restaurant", "cafe"]):
        drift_type = DriftType.MERCHANT_PURPOSE_MISMATCH
        intent_fit = "no_fit"
        evidence.append(f"Merchant '{merchant_name}' is a food service platform, inconsistent with travel flight intent.")
        confidence = 0.98
        risk_contrib = 0.95

    # 4. Integrate semantic verdict if already provided by LLM / mock entailment
    if semantic_verdict == "no_fit" and drift_type == DriftType.ALIGNED:
        drift_type = DriftType.OUTSIDE_MANDATE
        intent_fit = "no_fit"
        evidence.append(f"Semantic analysis confirmed item does not align with mandated intent '{mandate_intent[:80]}...'.")
        confidence = max(confidence, agreement_rate)
        risk_contrib = 0.75

    elif semantic_verdict == "ambiguous" and drift_type == DriftType.ALIGNED:
        drift_type = DriftType.AMBIGUOUS
        intent_fit = "ambiguous"
        evidence.append("Item purpose is ambiguous or under-specified relative to the mandate.")
        confidence = min(0.65, agreement_rate)
        risk_contrib = 0.50

    # 5. Default aligned
    if intent_fit == "fit" and not evidence:
        evidence.append(f"Proposal aligns with core mandate intent '{mandate_intent[:80]}'.")
        risk_contrib = 0.05

    is_drift = intent_fit != "fit"

    return SemanticDriftAnalysis(
        intent_fit=intent_fit,
        drift_type=drift_type,
        is_drift_detected=is_drift,
        evidence=evidence,
        confidence=confidence,
        risk_contribution=risk_contrib,
    )
