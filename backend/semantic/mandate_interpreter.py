"""
IntentGuard — Mandate Interpretation & Authorization Profile Normalizer

Converts natural language user spending mandates into structured,
normalized authorization profiles:
- intent
- purpose
- allowed categories
- allowed merchants
- exclusions
- amount limits
- currency
- geography (domestic/international)
- temporal constraints (effective_from, effective_until, business hours)
- agent scope (proposers allowed)
- contextual conditions
- escalation requirements

CRITICAL ARCHITECTURAL INVARIANT:
The LLM may assist in parsing/interpreting the mandate text.
LLM output MUST NOT directly authorize transactions.
The structured mandate profile is strictly validated and normalized
by deterministic Pydantic schemas before persisting.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.llm.provider import LLMProvider

logger = logging.getLogger("intentguard.mandate_interpreter")


class TemporalConstraint(BaseModel):
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    allowed_days: Optional[List[str]] = None  # e.g. ["MON", "TUE", "WED", "THU", "FRI"]
    business_hours_only: bool = False
    window_description: Optional[str] = None


class StructuredMandateProfile(BaseModel):
    """Normalized structured authorization profile for a spending mandate."""
    mandate_id: str
    version: int = 1
    intent_summary: str
    stated_purpose: str
    max_amount_per_txn: float
    budget_cap: Optional[float] = None
    currency: str = "INR"
    allowed_categories: List[str] = Field(default_factory=list)
    allowed_merchants: Optional[List[str]] = None
    exclusions: List[str] = Field(default_factory=list)
    geography: Optional[str] = "domestic"  # domestic, international, unrestricted
    temporal_constraints: TemporalConstraint = Field(default_factory=TemporalConstraint)
    allowed_agents: List[str] = Field(default_factory=lambda: ["buying_agent", "voice_mandate_agent", "recommendation_agent"])
    escalation_triggers: List[str] = Field(default_factory=lambda: ["ambiguous_intent", "unseen_merchant", "unusual_amount"])
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def normalize_mandate_profile(raw_data: Dict[str, Any], mandate_id: str, version: int = 1) -> StructuredMandateProfile:
    """
    Deterministic rule-based normalization and fallback parser for mandate text.
    Guarantees a valid, validated structured profile even if LLM is unavailable.
    """
    intent_text = str(raw_data.get("intent_text", "")).strip()
    max_amount = float(raw_data.get("max_amount_per_txn", 5000.0))
    budget_cap = raw_data.get("budget_cap")
    if budget_cap is not None:
        budget_cap = float(budget_cap)

    categories = list(raw_data.get("allowed_categories") or [])
    merchants = raw_data.get("allowed_merchants")
    if merchants:
        merchants = [str(m).strip() for m in merchants if str(m).strip()]

    exclusions = list(raw_data.get("exclusions") or [])
    location = raw_data.get("location_constraint") or "domestic"

    # Infer temporal constraints from text if present
    temporal = TemporalConstraint()
    lower_intent = intent_text.lower()
    if "business hours" in lower_intent or "work hours" in lower_intent:
        temporal.business_hours_only = True
    if "weekday" in lower_intent:
        temporal.allowed_days = ["MON", "TUE", "WED", "THU", "FRI"]

    # Extract common exclusions if mentioned in natural language
    if "no alcohol" in lower_intent and "alcohol" not in [e.lower() for e in exclusions]:
        exclusions.append("alcohol")
    if "no electronics" in lower_intent and "electronics" not in [e.lower() for e in exclusions]:
        exclusions.append("electronics")

    return StructuredMandateProfile(
        mandate_id=mandate_id,
        version=version,
        intent_summary=intent_text[:200],
        stated_purpose=raw_data.get("purpose_context") or intent_text[:100],
        max_amount_per_txn=max_amount,
        budget_cap=budget_cap,
        currency="INR",
        allowed_categories=[c.lower().strip() for c in categories],
        allowed_merchants=merchants,
        exclusions=[e.lower().strip() for e in exclusions],
        geography=str(location).lower(),
        temporal_constraints=temporal,
    )


async def interpret_mandate_with_llm(
    provider: Optional[LLMProvider],
    intent_text: str,
    raw_mandate: Dict[str, Any],
    mandate_id: str,
    version: int = 1,
) -> StructuredMandateProfile:
    """
    Interprets user intent using LLM when available, falling back deterministically
    to normalize_mandate_profile on any error, timeout, or mock mode.
    """
    fallback = normalize_mandate_profile(raw_mandate, mandate_id=mandate_id, version=version)
    if not provider or getattr(provider, "provider_name", "") == "mock":
        return fallback

    prompt = f"""You are IntentGuard Mandate Interpreter.
Extract a structured authorization profile from this spending mandate:

Intent Text: {intent_text}
Configured Max Per Txn: {raw_mandate.get('max_amount_per_txn')}
Configured Categories: {raw_mandate.get('allowed_categories')}
Configured Exclusions: {raw_mandate.get('exclusions')}
Configured Location: {raw_mandate.get('location_constraint')}

Respond in valid JSON only with keys:
{{
  "intent_summary": "concise summary",
  "stated_purpose": "intended business purpose",
  "allowed_categories": ["list", "of", "categories"],
  "exclusions": ["list", "of", "prohibited", "items"],
  "geography": "domestic or international or unrestricted",
  "business_hours_only": false
}}"""

    try:
        resp = await provider.generate(prompt=prompt, system_instruction="Output valid JSON only.")
        clean_text = resp.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        data = json.loads(clean_text)

        # Merge LLM extractions strictly through deterministic validation
        return StructuredMandateProfile(
            mandate_id=mandate_id,
            version=version,
            intent_summary=data.get("intent_summary") or fallback.intent_summary,
            stated_purpose=data.get("stated_purpose") or fallback.stated_purpose,
            max_amount_per_txn=fallback.max_amount_per_txn,
            budget_cap=fallback.budget_cap,
            currency="INR",
            allowed_categories=data.get("allowed_categories") or fallback.allowed_categories,
            allowed_merchants=fallback.allowed_merchants,
            exclusions=list(set((data.get("exclusions") or []) + fallback.exclusions)),
            geography=data.get("geography") or fallback.geography,
            temporal_constraints=TemporalConstraint(
                business_hours_only=bool(data.get("business_hours_only", False))
            ),
        )
    except Exception as e:
        logger.warning(f"[MANDATE_INTERPRETER] LLM parsing failed, using deterministic fallback: {e}")
        return fallback
