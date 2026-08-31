"""
IntentGuard — xAI Grok Provider

Uses the OpenAI-compatible API endpoint for xAI Grok.
Implements the LLMProvider interface.
"""

import json
import logging
import time
from typing import Dict, Optional, Tuple

from backend.llm.provider import LLMProvider

logger = logging.getLogger("intentguard.llm.grok")


class GrokProvider(LLMProvider):
    """xAI Grok LLM provider implementation (OpenAI-compatible API)."""

    XAI_BASE_URL = "https://api.x.ai/v1"

    def __init__(
        self,
        api_key: str,
        model: str = "grok-3-mini",
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
        return "grok"

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        """Lazy-initialize the OpenAI-compatible client for xAI."""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self.XAI_BASE_URL,
                timeout=self._timeout,
            )
        return self._client

    async def _call_with_retry(
        self,
        prompt: str,
        system_instruction: str = "",
        response_format: Optional[Dict] = None,
    ) -> Tuple[str, Dict]:
        """
        Call the xAI API with retry logic.
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        client = self._get_client()

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        last_error = None
        for attempt in range(self._max_retries + 1):
            try:
                start_time = time.time()

                kwargs = {
                    "model": self._model,
                    "messages": messages,
                    "temperature": 0.1,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                response = await client.chat.completions.create(**kwargs)
                elapsed_ms = int((time.time() - start_time) * 1000)

                usage_info = {
                    "provider": "grok",
                    "model": self._model,
                    "latency_ms": elapsed_ms,
                    "attempt": attempt + 1,
                }

                if response.usage:
                    usage_info["input_tokens"] = response.usage.prompt_tokens
                    usage_info["output_tokens"] = response.usage.completion_tokens

                response_text = response.choices[0].message.content.strip()
                return response_text, usage_info

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[LLM] Grok call attempt {attempt + 1} failed: {e}"
                )
                if attempt < self._max_retries:
                    logger.info("[LLM] Retrying with strict schema correction...")
                    # Update the last user message with a correction hint
                    messages[-1]["content"] = (
                        prompt + "\n\nIMPORTANT: Your previous response was invalid. "
                        "Respond ONLY with valid JSON matching the exact schema specified."
                    )

        raise RuntimeError(
            f"Grok API call failed after {self._max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    async def structured_extract(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        """Run structured extraction via Grok."""
        response_text, usage = await self._call_with_retry(
            prompt=prompt,
            system_instruction=system_instruction,
            response_format={"type": "json_object"},
        )

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            parsed = self._extract_json(response_text)

        return parsed, usage

    async def semantic_judge(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[Dict, Dict]:
        """Run semantic entailment judgment via Grok."""
        response_text, usage = await self._call_with_retry(
            prompt=prompt,
            system_instruction=system_instruction,
            response_format={"type": "json_object"},
        )

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            parsed = self._extract_json(response_text)

        return parsed, usage

    async def generate_explanation(
        self,
        prompt: str,
        system_instruction: str = "",
    ) -> Tuple[str, Dict]:
        """Generate explanation text via Grok."""
        response_text, usage = await self._call_with_retry(
            prompt=prompt,
            system_instruction=system_instruction,
        )

        return response_text, usage

    @staticmethod
    def _extract_json(text: str) -> Dict:
        """Attempt to extract JSON from a response that may contain extra text."""
        import re
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from Grok response: {text[:200]}")
