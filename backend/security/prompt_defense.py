"""
IntentGuard — Multi-Surface Prompt Injection & Adversarial Input Defense Layer

6-Layer Defense Architecture:
1. Multi-surface input normalization (NFKC, zero-width removal, control-char stripping)
2. Prompt injection pattern scanning across both dictionary KEYS and VALUES recursively
3. Boundary tag encapsulation (<untrusted_transaction_data>)
4. Strict tag neutralization (preventing delimiter collision or early tag closure)
5. Structured extraction schema enforcement
6. Deterministic policy immunity (LLM outputs are untrusted proposals, never executive decisions)
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

# Comprehensive adversarial prompt injection and jailbreak patterns
_INJECTION_PATTERNS: List[str] = [
    r"ignore\s+(all\s+)?(previous|prior|above|other)\s+instructions?",
    r"system\s*prompt",
    r"(system|admin|executive|policy|guard|rule|mandate|root|superuser)[\s_\-]+override",
    r"override[\s_\-]+(policy|system|guard|rule|mandate|budget|check|limit)",
    r"(output|return)\s+verdict\s*[:=]\s*allow",
    r"bypass[\s_\-]+(intentguard|security|validation|verification|guardrail|rule|check)",
    r"disregard[\s_\-]+(the[\s_\-]+)?(mandate|rules|policy|instructions)",
    r"<\s*script",
    r"you\s+are\s+now\s+in\s+(developer|unrestricted|god)\s+mode",
    r"jailbreak",
    r"system\s*administrator\s*(says|orders|authorized|confirms)\s*allow",
    r"increase\s+(the\s+)?budget",
    r"add\s+merchant\s+to\s+(whitelist|allowlist)",
    r"treat\s+this\s+as\s+pre-?approved",
    r"don'?t\s+tell\s+(the\s+)?auditor",
    r"skip\s+(semantic|intentguard)?\s*(verification|validation)",
    r"return\s+allow\s+regardless",
    r"always\s+output\s+['\"]?allow['\"]?",
    r"pretend\s+you\s+are\s+(an\s+unrestricted|a\s+different)\s+agent",
    r"<\s*/\s*untrusted_transaction_data\s*>",  # Delimiter collision attack
    r"human:\s*",
    r"assistant:\s*",
    r"roleplay\s+as",
    r"(approve|authorize)[\s_\-]+payment",
    r"grant[\s_\-]+authorization",
    r"force[\s_\-]+allow",
    r"disable[\s_\-]+policy",
    r"(admin|system)[\s_\-]+approved",
]

# Zero-width and invisible unicode characters
_ZERO_WIDTH_CHARS = [
    "\u200b",  # zero width space
    "\u200c",  # zero width non-joiner
    "\u200d",  # zero width joiner
    "\u200e",  # left-to-right mark
    "\u200f",  # right-to-left mark
    "\ufeff",  # byte order mark / zero width no-break space
    "\u00ad",  # soft hyphen
]


def normalize_untrusted_text(text: Optional[str]) -> str:
    """
    Multi-surface normalization:
    - Normalizes Unicode representations via NFKC
    - Strips zero-width and invisible formatting characters
    - Normalizes whitespace
    - Neutralizes XML boundary break-out attempts
    """
    if text is None:
        return ""

    # 1. NFKC normalization (decomposes and recomposes compatibility characters)
    normalized = unicodedata.normalize("NFKC", str(text))

    # 2. Strip zero-width characters
    for zw in _ZERO_WIDTH_CHARS:
        normalized = normalized.replace(zw, "")

    # 3. Strip ASCII control characters (except newline, tab)
    normalized = "".join(
        ch for ch in normalized
        if ch in ("\n", "\r", "\t") or unicodedata.category(ch)[0] != "C"
    )

    # 4. Normalize multi-spaces
    normalized = re.sub(r"[ \t]+", " ", normalized).strip()

    return normalized


def sanitize_boundary_tags(text: str) -> str:
    """
    Neutralize any attempt to break out of <untrusted_transaction_data> boundaries.
    Replaces delimiter tags with safe literal text representations.
    """
    if not text:
        return ""
    sanitized = re.sub(
        r"<\s*/?\s*untrusted_transaction_data\s*>",
        "[TAG_DEFUSED]",
        text,
        flags=re.IGNORECASE,
    )
    return sanitized


def scan_for_prompt_injection(text: str) -> Optional[str]:
    """
    Scan normalized text for known adversarial prompt injection patterns.
    Checks both literal normalized text and snake_case/kebab-case separated tokens.
    Returns the matched substring if an injection pattern is detected, else None.
    """
    if not text:
        return None

    normalized = normalize_untrusted_text(text)
    lower = normalized.lower()

    # 1. Check direct normalized form
    for pattern in _INJECTION_PATTERNS:
        match = re.search(pattern, lower, re.IGNORECASE)
        if match:
            return match.group(0)

    # 2. Check tokenized form with punctuation/underscores/dashes converted to spaces
    lower_spaced = re.sub(r"[_\-]+", " ", lower)
    if lower_spaced != lower:
        for pattern in _INJECTION_PATTERNS:
            match = re.search(pattern, lower_spaced, re.IGNORECASE)
            if match:
                return match.group(0)

    return None


def evaluate_prompt_defense(*inputs: Any) -> Tuple[bool, Optional[str]]:
    """
    Recursively scan all untrusted input surfaces for adversarial prompt injection:
    - Dictionary keys AND dictionary values
    - Nested dictionaries and nested arrays/lists/sets/tuples
    - Metadata fields and structured proposal fields
    - Detects hidden unicode, zero-width characters, and injection tokens

    Args:
        *inputs: Any number of strings, dictionaries, lists, or objects to inspect.

    Returns:
        (is_safe, violation_reason)
    """
    for item in inputs:
        if item is None:
            continue

        if isinstance(item, dict):
            for k, v in item.items():
                # Check dictionary KEY
                safe_k, reason_k = evaluate_prompt_defense(k)
                if not safe_k:
                    return False, f"Malicious dictionary key detected: {reason_k}"

                # Check dictionary VALUE
                safe_v, reason_v = evaluate_prompt_defense(v)
                if not safe_v:
                    return False, reason_v

        elif isinstance(item, (list, tuple, set)):
            for element in item:
                safe, reason = evaluate_prompt_defense(element)
                if not safe:
                    return False, reason

        elif hasattr(item, "model_dump") and callable(item.model_dump):
            safe, reason = evaluate_prompt_defense(item.model_dump())
            if not safe:
                return False, reason

        else:
            trigger = scan_for_prompt_injection(str(item))
            if trigger:
                return False, f"Adversarial prompt injection pattern detected: '{trigger}'"

    return True, None


def encapsulate_untrusted_input(data: str) -> str:
    """
    Wrap untrusted transaction text in boundary tags to inform LLM of untrusted context.
    Neutralizes internal boundary breakout attempts prior to wrapping.
    """
    safe_data = sanitize_boundary_tags(normalize_untrusted_text(data))
    return f"<untrusted_transaction_data>\n{safe_data}\n</untrusted_transaction_data>"
