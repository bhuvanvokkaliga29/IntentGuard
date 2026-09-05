"""
IntentGuard — LLM Provider Interface & Factory

Supports Google Gemini, xAI Grok, and an explicitly labeled Mock Provider.
Do not hard-code one provider.

Environment configuration:
  LLM_PROVIDER=gemini   (or grok, mock)
  GEMINI_API_KEY=...
  XAI_API_KEY=...

If one provider fails:
  Return a safe, visible error.
  Do NOT silently switch providers during a transaction.
  The selected provider must appear in the audit log.
"""

import abc
import logging
from typing import Dict, Optional, Tuple

from backend.config import get_settings

logger = logging.getLogger("intentguard.llm")


class LLMProvider(abc.ABC):
    """Abstract LLM provider interface."""

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'gemini', 'grok', 'mock')."""
        ...

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        ...

    @abc.abstractmethod
    async def structured_extract(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        """
        Run structured extraction (LLM Call 1).
        
        Returns:
            Tuple of (parsed_output_dict, usage_info_dict)
        """
        ...

    @abc.abstractmethod
    async def semantic_judge(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        """
        Run semantic entailment judgment (LLM Call 2).
        
        Returns:
            Tuple of (parsed_output_dict, usage_info_dict)
        """
        ...

    @abc.abstractmethod
    async def generate_explanation(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[str, Dict]:
        """
        Generate a human-readable explanation (LLM Call 3).
        
        Returns:
            Tuple of (explanation_text, usage_info_dict)
        """
        ...


class MockProvider(LLMProvider):
    """
    Explicit Mock LLM Provider for offline evaluation, unit testing, and CI.
    Clearly labeled as LOCAL_MOCK_MODE to maintain honesty.
    """

    def __init__(self, model: str = "mock-semantic-v1"):
        self._model = model

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self._model

    async def structured_extract(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        p_lower = prompt.lower()
        # Isolate transaction data section to avoid matching prompt template instructions
        data_text = p_lower
        if "transaction data:" in p_lower:
            data_text = p_lower.split("transaction data:", 1)[1]
            if "mandate context" in data_text:
                data_text = data_text.split("mandate context", 1)[0]

        if "chocolate" in data_text or "sweet" in data_text:
            category = "food_confectionery"
            item_type = "confectionery"
        elif "flight" in data_text or "airline" in data_text or "dubai" in data_text:
            category = "travel"
            item_type = "airline_ticket"
        elif "spa" in data_text or "skincare" in data_text or "cosmetic" in data_text:
            category = "cosmetics"
            item_type = "luxury_spa"
        elif "paper" in data_text or "pen" in data_text or "stationery" in data_text or "sticky notes" in data_text or "desk" in data_text or "printer" in data_text:
            category = "office_supplies"
            item_type = "stationery"
        elif "air freshener" in data_text or "diffuser" in data_text:
            category = "office_supplies"
            item_type = "ambient_decor"
        else:
            category = "general"
            item_type = "unspecified"

        output = {
            "category": category,
            "normalized_category": category,
            "item_type": item_type,
            "purpose_indicators": ["mock_indicator"],
            "recipient": "self",
            "recurring_signal": False,
            "risk_flags": [],
        }
        usage = {"prompt_tokens": 100, "completion_tokens": 50, "mode": "LOCAL_MOCK_MODE"}
        return output, usage

    async def semantic_judge(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        p_lower = prompt.lower()

        # Isolate item description and original transaction to avoid matching template instructions (e.g. Rule 7 chocolates)
        item_text = p_lower
        if "original transaction:" in p_lower:
            item_text = p_lower.split("original transaction:", 1)[1]
        elif "item:" in p_lower:
            item_text = p_lower.split("item:", 1)[1]

        # Isolate mandate intent
        mandate_part = p_lower
        if "user's spending mandate:" in p_lower:
            mandate_part = p_lower.split("user's spending mandate:", 1)[1]
            if "extracted transaction facts:" in mandate_part:
                mandate_part = mandate_part.split("extracted transaction facts:", 1)[0]

        if ("chocolate" in item_text or "sweet" in item_text or "confectionery" in item_text) and ("office supplies" in mandate_part or "stationery" in mandate_part):
            verdict = "no_fit"
            reasoning = "Chocolates are confectionery and do not fit office supplies mandate intent."
        elif "dubai" in item_text and ("domestic" in mandate_part or "bangalore" in mandate_part):
            verdict = "no_fit"
            reasoning = "International travel violates domestic flight mandate intent."
        elif ("spa" in item_text or "skincare" in item_text or "cosmetic" in item_text) and ("groceries" in mandate_part or "supermarket" in mandate_part):
            verdict = "no_fit"
            reasoning = "Luxury spa package is cosmetics and violates household groceries mandate intent."
        elif "paper" in item_text or "pen" in item_text or "sticky notes" in item_text or "stationery" in item_text or "desk" in item_text or "printer" in item_text:
            verdict = "fit"
            reasoning = "Stationery items directly fit the office supplies mandate."
        elif "air freshener" in item_text or "diffuser" in item_text:
            verdict = "ambiguous"
            reasoning = "Item intent cannot be deterministically verified from description under vague mandate."
        elif "miscellaneous" in item_text:
            verdict = "ambiguous"
            reasoning = "Description 'miscellaneous item' provides insufficient evidence to confirm intent compliance."
        else:
            verdict = "ambiguous"
            reasoning = "Item intent cannot be deterministically verified from description."

        output = {
            "verdict": verdict,
            "confidence": "high",
            "reasoning": reasoning,
            "violates_exclusions": False,
        }
        usage = {"prompt_tokens": 150, "completion_tokens": 60, "mode": "LOCAL_MOCK_MODE"}
        return output, usage

    async def generate_explanation(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[str, Dict]:
        p_lower = prompt.lower()
        # Isolate item description
        item_text = p_lower
        if "item:" in p_lower:
            item_text = p_lower.split("item:", 1)[1]
            if "verdict:" in item_text:
                item_text = item_text.split("verdict:", 1)[0]

        if "chocolate" in item_text:
            explanation = "Item is confectionery/food, violating the stated office supplies intent. Blocked by semantic policy."
        elif "dubai" in item_text:
            explanation = "Flight destination (Dubai) is international, violating the domestic mandate restriction. Blocked."
        elif "spa" in item_text or "skincare" in item_text:
            explanation = "Luxury cosmetic spa bundle violates household groceries mandate. Blocked by semantic verification."
        elif "paper" in item_text or "pen" in item_text or "sticky notes" in item_text or "printer" in item_text:
            explanation = "Standard office supplies from approved merchant well within limit. Approved by semantic verification."
        elif "diffuser" in item_text or "air freshener" in item_text:
            explanation = "Mandate purpose is too underspecified to establish definitive semantic entailment. Escalated for user confirmation."
        elif "miscellaneous" in item_text:
            explanation = "Description 'miscellaneous item' provides insufficient evidence to confirm intent compliance. Safely escalated."
        else:
            explanation = "Decision rendered based on structural constraints and semantic intent assessment."
        usage = {"prompt_tokens": 80, "completion_tokens": 30, "mode": "LOCAL_MOCK_MODE"}
        return explanation, usage


def get_provider() -> LLMProvider:
    """
    Factory function to get the configured LLM provider.
    
    Reads LLM_PROVIDER from environment.
    Returns the appropriate provider instance.
    Raises ValueError if provider is not supported or key is missing.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini. "
                "Set it in your .env file."
            )
        from backend.llm.gemini import GeminiProvider
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            timeout=settings.llm_request_timeout,
            max_retries=settings.llm_max_retries,
        )

    elif provider == "grok":
        if not settings.xai_api_key:
            raise ValueError(
                "XAI_API_KEY is required when LLM_PROVIDER=grok. "
                "Set it in your .env file."
            )
        from backend.llm.grok import GrokProvider
        return GrokProvider(
            api_key=settings.xai_api_key,
            model=settings.xai_model,
            timeout=settings.llm_request_timeout,
            max_retries=settings.llm_max_retries,
        )

    elif provider == "mock":
        return MockProvider()

    else:
        raise ValueError(
            f"Unsupported LLM_PROVIDER: '{provider}'. "
            f"Supported providers: 'gemini', 'grok', 'mock'."
        )


def get_provider_info() -> Dict:
    """Get info about the currently configured provider (without exposing keys)."""
    settings = get_settings()
    provider = settings.llm_provider.lower()

    info = {
        "provider": provider,
        "configured": False,
        "model": None,
        "is_mock": provider == "mock",
    }

    if provider == "gemini":
        info["configured"] = bool(settings.gemini_api_key)
        info["model"] = settings.gemini_model
    elif provider == "grok":
        info["configured"] = bool(settings.xai_api_key)
        info["model"] = settings.xai_model
    elif provider == "mock":
        info["configured"] = True
        info["model"] = "mock-semantic-v1"

    return info
