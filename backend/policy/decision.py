"""
IntentGuard — Deterministic Policy / Decision Engine

The FINAL decision is ALWAYS deterministic.
The LLM NEVER outputs ALLOW / FLAG / BLOCK / ESCALATE directly.

Decision logic:
- Hard constraint failure → BLOCK (no semantic call needed)
- Structural pass + FIT + confidence >= threshold → ALLOW
- Structural pass + NO_FIT + confidence >= threshold → BLOCK
- Structural pass + AMBIGUOUS → FLAG
- Confidence < threshold → FLAG or ESCALATE
- Missing critical information → ESCALATE

This module is unit-testable independently of any LLM.
"""

from typing import Dict, Optional

from backend.models import FinalDecision, SemanticVerdict
from backend.policy.thresholds import get_thresholds


def decide(
    structural_pass: bool,
    majority_verdict: Optional[str],
    confidence_score: float,
    has_extracted_facts: bool = True,
    evidence_is_sufficient: bool = True,
    structural_failure_reasons: Optional[list] = None,
) -> Dict:
    """
    Deterministic decision engine.
    
    Args:
        structural_pass: Whether all hard constraints passed
        majority_verdict: The majority semantic verdict (fit/no_fit/ambiguous) or None
        confidence_score: Computed confidence score (0.0 to 1.0)
        has_extracted_facts: Whether structured facts were successfully extracted
        evidence_is_sufficient: Whether the evidence is sufficient for a judgment
        structural_failure_reasons: List of reasons for structural failures
    
    Returns:
        Dict with:
        - final_decision: FinalDecision enum value
        - reasoning: str explaining why this decision was made
        - decision_path: str describing which logic branch was taken
    """
    thresholds = get_thresholds()

    # ── Path 1: Hard constraint failure → BLOCK ───────────────
    if not structural_pass:
        reasons = structural_failure_reasons or ["Hard constraint failure"]
        return {
            "final_decision": FinalDecision.BLOCK.value,
            "reasoning": (
                f"Transaction blocked due to hard constraint violation(s): "
                f"{'; '.join(reasons)}. "
                f"No semantic judgment was required."
            ),
            "decision_path": "structural_hard_fail → BLOCK",
        }

    # ── Path 2: Missing critical information → ESCALATE ───────
    if not has_extracted_facts or not evidence_is_sufficient:
        return {
            "final_decision": FinalDecision.ESCALATE.value,
            "reasoning": (
                "Insufficient information to determine whether the transaction "
                "fits the mandate. The transaction requires human review."
            ),
            "decision_path": "insufficient_evidence → ESCALATE",
        }

    # ── Path 3: No semantic verdict available → ESCALATE ──────
    if majority_verdict is None:
        return {
            "final_decision": FinalDecision.ESCALATE.value,
            "reasoning": (
                "Semantic judgment could not be completed. "
                "The transaction requires human review."
            ),
            "decision_path": "no_semantic_verdict → ESCALATE",
        }

    # ── Path 4: Very low confidence → ESCALATE ───────────────
    if confidence_score < thresholds.confidence_low:
        return {
            "final_decision": FinalDecision.ESCALATE.value,
            "reasoning": (
                f"Confidence score ({confidence_score:.2f}) is below the minimum "
                f"threshold ({thresholds.confidence_low:.2f}). "
                f"The system cannot make a reliable determination. "
                f"Human review is required."
            ),
            "decision_path": "very_low_confidence → ESCALATE",
        }

    # ── Path 5: AMBIGUOUS verdict → FLAG ──────────────────────
    if majority_verdict == SemanticVerdict.AMBIGUOUS.value:
        return {
            "final_decision": FinalDecision.FLAG.value,
            "reasoning": (
                f"Semantic judgment is ambiguous (confidence: {confidence_score:.2f}). "
                f"The transaction may or may not fit the mandate purpose. "
                f"Flagged for human review."
            ),
            "decision_path": "semantic_ambiguous → FLAG",
        }

    # ── Path 6: Low confidence on any verdict → FLAG ──────────
    if confidence_score < thresholds.confidence_high:
        return {
            "final_decision": FinalDecision.FLAG.value,
            "reasoning": (
                f"Confidence score ({confidence_score:.2f}) is below the high-confidence "
                f"threshold ({thresholds.confidence_high:.2f}). "
                f"Semantic verdict was '{majority_verdict}' but confidence is insufficient "
                f"for an automatic decision. Flagged for human review."
            ),
            "decision_path": f"low_confidence_{majority_verdict} → FLAG",
        }

    # ── Path 7: High confidence + FIT → ALLOW ────────────────
    if majority_verdict == SemanticVerdict.FIT.value:
        return {
            "final_decision": FinalDecision.ALLOW.value,
            "reasoning": (
                f"Transaction passes all structural checks. "
                f"Semantic judgment indicates the transaction fits the mandate purpose "
                f"(confidence: {confidence_score:.2f}). Approved."
            ),
            "decision_path": "structural_pass + semantic_fit + high_confidence → ALLOW",
        }

    # ── Path 8: High confidence + NO_FIT → BLOCK ─────────────
    if majority_verdict == SemanticVerdict.NO_FIT.value:
        return {
            "final_decision": FinalDecision.BLOCK.value,
            "reasoning": (
                f"Transaction passes structural checks but semantic judgment indicates "
                f"the transaction does NOT fit the mandate purpose "
                f"(confidence: {confidence_score:.2f}). Blocked."
            ),
            "decision_path": "structural_pass + semantic_no_fit + high_confidence → BLOCK",
        }

    # ── Fallback: FLAG ────────────────────────────────────────
    return {
        "final_decision": FinalDecision.FLAG.value,
        "reasoning": (
            f"Unable to resolve to a definitive decision. "
            f"Verdict: '{majority_verdict}', confidence: {confidence_score:.2f}. "
            f"Flagged for human review."
        ),
        "decision_path": "fallback → FLAG",
    }
