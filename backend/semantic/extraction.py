"""
IntentGuard — Structured Fact Extraction (LLM Call 1)

Extracts structured facts from transaction metadata using the LLM.
Output is validated with Pydantic.
Invalid output → retry once with strict schema correction.
If still invalid → ESCALATE.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

from backend.llm.provider import LLMProvider
from backend.llm.schemas import ExtractionOutput
from backend.config import get_settings

logger = logging.getLogger("intentguard.semantic.extraction")


def _load_prompt_template() -> str:
    """Load the extraction prompt template."""
    settings = get_settings()
    version = settings.extraction_prompt_version
    prompt_path = settings.prompts_dir / f"extraction_{version}.txt"
    return prompt_path.read_text(encoding="utf-8")


def _build_extraction_prompt(
    item_description: str,
    merchant_name: str,
    merchant_category: str,
    amount: float,
    mandate_intent: str,
) -> str:
    """Build the extraction prompt from the template."""
    template = _load_prompt_template()

    transaction_data = (
        f"Item description: {item_description}\n"
        f"Merchant: {merchant_name}\n"
        f"Merchant category: {merchant_category}\n"
        f"Amount: ₹{amount:,.2f}"
    )

    return template.replace("{transaction_data}", transaction_data).replace(
        "{mandate_context}", mandate_intent
    )


def _validate_extraction(raw: Dict) -> Tuple[Optional[ExtractionOutput], Optional[str]]:
    """
    Validate extraction output against the Pydantic schema.
    
    Returns:
        Tuple of (validated_output, error_message)
    """
    try:
        validated = ExtractionOutput(**raw)
        return validated, None
    except Exception as e:
        return None, str(e)


async def extract_structured_facts(
    provider: LLMProvider,
    item_description: str,
    merchant_name: str,
    merchant_category: str,
    amount: float,
    mandate_intent: str,
) -> Tuple[Optional[Dict], Dict]:
    """
    Extract structured facts from a transaction using the LLM.
    
    Args:
        provider: The LLM provider to use
        item_description: Transaction item description
        merchant_name: Merchant name
        merchant_category: Merchant category
        amount: Transaction amount
        mandate_intent: The mandate's intent text (for context)
    
    Returns:
        Tuple of (extracted_facts_dict, usage_info_dict)
        If extraction fails after retries, extracted_facts_dict will be None.
    """
    prompt = _build_extraction_prompt(
        item_description=item_description,
        merchant_name=merchant_name,
        merchant_category=merchant_category,
        amount=amount,
        mandate_intent=mandate_intent,
    )

    system_instruction = (
        "You are a precise fact extraction system. "
        "Output ONLY valid JSON matching the specified schema. "
        "Never invent facts not present in the input data."
    )

    try:
        raw_output, usage = await provider.structured_extract(
            prompt=prompt,
            system_instruction=system_instruction,
        )

        # Validate with Pydantic
        validated, error = _validate_extraction(raw_output)

        if validated:
            logger.info(
                f"[LLM] Extraction successful: category={validated.normalized_category}, "
                f"item_type={validated.item_type}"
            )
            return validated.model_dump(), usage
        else:
            logger.warning(f"[LLM] Extraction validation failed: {error}")
            # The provider already retries internally, so if we get here
            # with invalid output, we return None to trigger ESCALATE
            return None, usage

    except Exception as e:
        logger.error(f"[LLM] Extraction failed: {e}")
        return None, {"provider": provider.provider_name, "error": str(e)}
