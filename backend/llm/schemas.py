"""
IntentGuard — LLM Schemas

Pydantic models for LLM inputs and outputs.
Every LLM output must be validated with Pydantic.
Invalid output → retry once → if still invalid → ESCALATE.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ExtractionInput(BaseModel):
    """Input for structured fact extraction (LLM Call 1)."""
    item_description: str
    merchant_name: str
    merchant_category: str
    amount: float
    mandate_intent: str


class ExtractionOutput(BaseModel):
    """Output from structured fact extraction (LLM Call 1)."""
    normalized_category: str = Field(..., description="Normalized item category (e.g., 'office_supplies', 'food', 'travel')")
    item_type: str = Field(..., description="Type of item (e.g., 'writing_instruments', 'confectionery', 'airline_ticket')")
    domestic_or_international: Optional[str] = Field(None, description="'domestic', 'international', or null if not applicable")
    brand_tier: Optional[str] = Field(None, description="'budget', 'standard', 'premium', 'luxury', or null")
    quantity: Optional[int] = Field(None, description="Number of items if inferable, null otherwise")
    specific_product: Optional[str] = Field(None, description="Specific product name if identifiable")
    confidence_notes: Optional[str] = Field(None, description="Notes about extraction uncertainty")


class SemanticInput(BaseModel):
    """Input for semantic entailment judgment (LLM Call 2)."""
    mandate_intent: str
    mandate_allowed_categories: list
    extracted_facts: dict
    item_description: str
    merchant_name: str
    amount: float


class SemanticOutput(BaseModel):
    """Output from semantic entailment judgment (LLM Call 2)."""
    verdict: str = Field(..., description="One of: 'fit', 'no_fit', 'ambiguous'")
    rationale: str = Field(..., description="Evidence-grounded rationale for the verdict")


class ExplanationInput(BaseModel):
    """Input for explanation generation (LLM Call 3)."""
    mandate_intent: str
    transaction_description: str
    structural_result: dict
    extracted_facts: dict
    semantic_verdict: str
    semantic_rationale: str
    confidence_score: float
    final_decision: str


class ExplanationOutput(BaseModel):
    """Output from explanation generation."""
    explanation: str = Field(..., description="Human-readable explanation grounded only in available facts")
