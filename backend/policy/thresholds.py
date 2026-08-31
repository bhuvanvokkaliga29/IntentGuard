"""
IntentGuard — Configurable Thresholds

All decision thresholds in one place. Configurable via environment.
Never hard-coded inside LLM prompts or business logic.
"""

from backend.config import get_settings


class Thresholds:
    """Decision thresholds for the policy engine."""

    def __init__(self):
        settings = get_settings()
        self.confidence_high = settings.confidence_threshold_high  # default: 0.75
        self.confidence_low = settings.confidence_threshold_low    # default: 0.40
        self.self_consistency_samples = settings.self_consistency_samples  # default: 3

    # ── Amount proximity thresholds ───────────────────────────
    # When transaction amount is within this fraction of the limit,
    # reduce confidence slightly.
    AMOUNT_PROXIMITY_THRESHOLD = 0.90  # 90% of limit
    AMOUNT_PROXIMITY_PENALTY = 0.05    # Reduce confidence by 5%

    # ── Agreement rate thresholds ─────────────────────────────
    FULL_AGREEMENT_BONUS = 0.10        # Add 10% for unanimous agreement
    PARTIAL_AGREEMENT_PENALTY = 0.10   # Reduce 10% for split agreement
    NO_AGREEMENT_PENALTY = 0.25        # Reduce 25% for total disagreement

    # ── Evidence completeness ─────────────────────────────────
    INCOMPLETE_EVIDENCE_PENALTY = 0.15  # Reduce confidence when evidence is sparse

    # ── Hard categorical mismatch ─────────────────────────────
    HARD_MISMATCH_PENALTY = 0.30       # Major reduction for hard fact mismatches


def get_thresholds() -> Thresholds:
    """Get the current thresholds instance."""
    return Thresholds()
