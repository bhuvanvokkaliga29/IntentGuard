"""
IntentGuard — Post-Decision Learning Loop

Captures human compliance reviews (APPROVE, REJECT, REQUEST_MORE_INFORMATION)
into structured offline evaluation datasets.

Purposes:
- Offline threshold sensitivity analysis
- Regression test case generation
- Ground-truth validation
- Dataset expansion for CI benchmarks

CRITICAL ARCHITECTURAL INVARIANT:
Human review outcomes DO NOT automatically mutate live deterministic policy rules.
No uncontrolled self-learning authorization loops.
All policy adjustments must be governed, versioned, reviewed, and deployed via code.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("intentguard.evaluation.learning_loop")

LEARNING_DATASET_PATH = Path("backend/data/human_review_learning_dataset.json")


class HumanReviewFeedbackRecord(BaseModel):
    record_id: str
    decision_id: str
    transaction_id: str
    mandate_id: str
    mandate_version: int = 1
    policy_version: str = "2.1.0"
    original_proposal: Dict[str, Any]
    original_decision: str
    reviewer_action: str  # APPROVE, REJECT, REQUEST_MORE_INFORMATION
    reviewer_id: str
    reviewer_notes: Optional[str] = None
    original_risk_profile: Optional[Dict[str, Any]] = None
    original_drift_analysis: Optional[Dict[str, Any]] = None
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def record_human_review_feedback(record: HumanReviewFeedbackRecord) -> None:
    """
    Appends the human review decision to the offline evaluation repository.
    """
    try:
        LEARNING_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        dataset: List[Dict[str, Any]] = []

        if LEARNING_DATASET_PATH.exists():
            try:
                with open(LEARNING_DATASET_PATH, "r", encoding="utf-8") as f:
                    dataset = json.load(f)
            except Exception:
                dataset = []

        dataset.append(record.model_dump())

        with open(LEARNING_DATASET_PATH, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

        logger.info(f"[LEARNING_LOOP] Recorded reviewer feedback for decision {record.decision_id} into offline dataset.")
    except Exception as e:
        logger.error(f"[LEARNING_LOOP] Failed to persist review feedback: {e}")


def load_learning_records() -> List[Dict[str, Any]]:
    """Loads all human review learning records for offline analysis."""
    if not LEARNING_DATASET_PATH.exists():
        return []
    try:
        with open(LEARNING_DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[LEARNING_LOOP] Failed to load learning dataset: {e}")
        return []
