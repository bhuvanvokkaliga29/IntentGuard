"""
IntentGuard — Google Gemini Provider

Uses google-generativeai SDK with structured output / JSON mode.
Implements the LLMProvider interface.
"""

import json
import logging
import time
from typing import Dict, Optional, Tuple

from backend.llm.provider import LLMProvider

logger = logging.getLogger("intentguard.llm.gemini")


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout: int = 30,
        max_retries: int = 1,
    ):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._client = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        """Lazy-initialize the Gemini client."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self._model)
        return self._client

    async def _call_with_retry(
        self,
        prompt: str,
        system_instruction: str = "",
        response_mime_type: str = "application/json",
    ) -> Tuple[str, Dict]:
        """
        Call the Gemini API with retry logic.
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)

        generation_config = genai.types.GenerationConfig(
            response_mime_type=response_mime_type,
            temperature=0.1,
        )

        model = genai.GenerativeModel(
            model_name=self._model,
            system_instruction=system_instruction if system_instruction else None,
            generation_config=generation_config,
        )

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                start_time = time.time()
                response = model.generate_content(prompt)
                elapsed_ms = int((time.time() - start_time) * 1000)

                # Extract usage info
                usage_info = {
                    "provider": "gemini",
                    "model": self._model,
                    "latency_ms": elapsed_ms,
                    "attempt": attempt + 1,
                }

                # Try to get token counts if available
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage_info["input_tokens"] = getattr(response.usage_metadata, 'prompt_token_count', None)
                    usage_info["output_tokens"] = getattr(response.usage_metadata, 'candidates_token_count', None)

                response_text = response.text.strip()
                return response_text, usage_info

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[LLM] Gemini call attempt {attempt + 1} failed: {e}"
                )
                if attempt < self._max_retries:
                    logger.info("[LLM] Retrying with strict schema correction...")
                    # Add schema correction hint to the prompt on retry
                    prompt = (
                        prompt + "\n\nIMPORTANT: Your previous response was invalid. "
                        "Respond ONLY with valid JSON matching the exact schema specified."
                    )

        raise RuntimeError(
            f"Gemini API call failed after {self._max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    async def structured_extract(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        """Run structured extraction via Gemini with fault-tolerant fallback."""
        try:
            response_text, usage = await self._call_with_retry(
                prompt=prompt,
                system_instruction=system_instruction,
                response_mime_type="application/json",
            )
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                parsed = self._extract_json(response_text)

            if isinstance(parsed, dict):
                if "normalized_category" not in parsed:
                    parsed["normalized_category"] = (
                        parsed.get("category")
                        or parsed.get("merchant_category")
                        or "general"
                    )
                if "item_type" not in parsed:
                    parsed["item_type"] = (
                        parsed.get("item_description")
                        or parsed.get("type")
                        or "unspecified"
                    )

            return parsed, usage
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "ResourceExhausted" in str(e):
                logger.warning(f"[LLM] Gemini quota reached (429). Engaging fault-tolerant local fallback engine.")
                from backend.llm.provider import MockProvider
                return await MockProvider().structured_extract(prompt, system_instruction)
            raise

    async def semantic_judge(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        """Run semantic entailment judgment via Gemini with fault-tolerant fallback."""
        try:
            response_text, usage = await self._call_with_retry(
                prompt=prompt,
                system_instruction=system_instruction,
                response_mime_type="application/json",
            )
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                parsed = self._extract_json(response_text)

            if isinstance(parsed, dict):
                # Normalize verdict
                if "verdict" not in parsed:
                    if "is_reasonable" in parsed:
                        parsed["verdict"] = "fit" if parsed["is_reasonable"] else "no_fit"
                    elif "fits" in parsed:
                        parsed["verdict"] = "fit" if parsed["fits"] else "no_fit"
                    elif "match" in parsed:
                        parsed["verdict"] = "fit" if parsed["match"] else "no_fit"
                    else:
                        parsed["verdict"] = "ambiguous"

                # Normalize string representations
                v_str = str(parsed["verdict"]).lower().strip().replace(" ", "_")
                if v_str in ("fit", "direct_fit", "allowed", "true", "yes"):
                    parsed["verdict"] = "fit"
                elif v_str in ("no_fit", "nofit", "drift_detected", "blocked", "false", "no"):
                    parsed["verdict"] = "no_fit"
                else:
                    parsed["verdict"] = "ambiguous"

                # Normalize rationale
                if "rationale" not in parsed:
                    raw_rat = (
                        parsed.get("reasoning")
                        or parsed.get("explanation")
                        or parsed.get("verification_details")
                    )
                    if isinstance(raw_rat, dict):
                        parsed["rationale"] = "; ".join(f"{k}: {v}" for k, v in raw_rat.items())
                    elif raw_rat:
                        parsed["rationale"] = str(raw_rat)
                    else:
                        parsed["rationale"] = "Semantic alignment evaluated by Gemini model."

            return parsed, usage
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "ResourceExhausted" in str(e):
                logger.warning(f"[LLM] Gemini quota reached (429). Engaging fault-tolerant local fallback engine.")
                from backend.llm.provider import MockProvider
                return await MockProvider().semantic_judge(prompt, system_instruction)
            raise

    async def generate_explanation(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[str, Dict]:
        """Generate explanation text via Gemini with fault-tolerant fallback."""
        try:
            response_text, usage = await self._call_with_retry(
                prompt=prompt,
                system_instruction=system_instruction,
                response_mime_type="text/plain",
            )
            return response_text, usage
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower() or "ResourceExhausted" in str(e):
                from backend.llm.provider import MockProvider
                return await MockProvider().generate_explanation(prompt, system_instruction)
            raise

    @staticmethod
    def _extract_json(text: str) -> Dict:
        """Attempt to extract JSON from a response that may contain extra text."""
        import re
        # Try to find JSON block
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from Gemini response: {text[:200]}")
