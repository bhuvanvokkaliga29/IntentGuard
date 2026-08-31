"""
IntentGuard — Semantic Engine Tests

Tests for extraction and entailment with mock LLM responses.
"""

import pytest
from backend.llm.schemas import ExtractionOutput, SemanticOutput


class TestExtractionValidation:
    def test_valid_extraction_output(self):
        """Valid extraction output should parse correctly."""
        raw = {
            "normalized_category": "office_supplies",
            "item_type": "paper_products",
            "domestic_or_international": None,
            "brand_tier": "standard",
            "quantity": 5,
            "specific_product": "A4 printer paper",
            "confidence_notes": None,
        }
        output = ExtractionOutput(**raw)
        assert output.normalized_category == "office_supplies"
        assert output.item_type == "paper_products"

    def test_minimal_extraction_output(self):
        """Extraction with only required fields."""
        raw = {
            "normalized_category": "food_confectionery",
            "item_type": "chocolates",
        }
        output = ExtractionOutput(**raw)
        assert output.normalized_category == "food_confectionery"
        assert output.domestic_or_international is None

    def test_invalid_extraction_missing_required(self):
        """Missing required fields should raise."""
        with pytest.raises(Exception):
            ExtractionOutput(item_type="test")  # missing normalized_category


class TestSemanticOutputValidation:
    def test_valid_fit(self):
        raw = {"verdict": "fit", "rationale": "Item matches mandate purpose."}
        output = SemanticOutput(**raw)
        assert output.verdict == "fit"

    def test_valid_no_fit(self):
        raw = {"verdict": "no_fit", "rationale": "Item does not match."}
        output = SemanticOutput(**raw)
        assert output.verdict == "no_fit"

    def test_valid_ambiguous(self):
        raw = {"verdict": "ambiguous", "rationale": "Unclear whether item fits."}
        output = SemanticOutput(**raw)
        assert output.verdict == "ambiguous"

    def test_missing_verdict(self):
        with pytest.raises(Exception):
            SemanticOutput(rationale="No verdict")

    def test_missing_rationale(self):
        with pytest.raises(Exception):
            SemanticOutput(verdict="fit")
