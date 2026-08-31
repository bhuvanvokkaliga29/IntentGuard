"""
IntentGuard — Evaluation Baselines

Baseline A: Structural rules only (everything that passes structural checks → ALLOW)
Baseline B: Semantic layer only (skip structural checks)
"""

from typing import Dict, List


def baseline_structural_only(
    structural_pass: bool,
) -> str:
    """
    Baseline A: Structural rules only.
    If structural checks pass → ALLOW.
    If structural checks fail → BLOCK.
    No semantic analysis.
    """
    return "ALLOW" if structural_pass else "BLOCK"


def baseline_semantic_only(
    semantic_verdict: str,
    confidence: float = 0.75,
) -> str:
    """
    Baseline B: Semantic layer only.
    Skip structural pre-checks entirely.
    Demonstrates failure on hard categorical cases.
    """
    if semantic_verdict == "fit" and confidence >= 0.75:
        return "ALLOW"
    elif semantic_verdict == "no_fit" and confidence >= 0.75:
        return "BLOCK"
    elif semantic_verdict == "ambiguous":
        return "FLAG"
    else:
        return "FLAG"
