"""
IntentGuard — Policy Versioning Engine

Maintains immutable, reproducible policy snapshots:
- Policy version string (e.g. 2.1.0)
- Active confidence thresholds
- Active hard constraint definitions
- Decision matrix configuration
- SHA-256 policy configuration hash

Every transaction decision is permanently bound to:
mandate_version + policy_version + configuration_hash
"""

import hashlib
import json
from typing import Any, Dict
from pydantic import BaseModel, Field

from backend.policy.thresholds import get_thresholds

POLICY_VERSION = "2.1.0"


class PolicySnapshot(BaseModel):
    version: str = POLICY_VERSION
    confidence_high: float
    confidence_low: float
    self_consistency_samples: int
    structural_rules: list = Field(default_factory=lambda: [
        "max_amount_per_txn",
        "budget_cap",
        "allowed_categories",
        "allowed_merchants",
        "exclusions",
        "location_constraint",
        "temporal_constraint",
    ])
    decision_matrix_rules: list = Field(default_factory=lambda: [
        "security_violation -> BLOCK",
        "structural_failure -> BLOCK",
        "temporal_failure -> BLOCK or ESCALATE",
        "insufficient_evidence -> ESCALATE",
        "semantic_ambiguous -> ESCALATE",
        "semantic_fit + high_confidence -> ALLOW",
        "semantic_no_fit + high_confidence -> BLOCK",
        "low_confidence -> ESCALATE",
    ])
    config_hash: str


def get_current_policy_snapshot() -> PolicySnapshot:
    """Returns canonical immutable policy snapshot with SHA-256 fingerprint."""
    thresh = get_thresholds()
    payload = {
        "version": POLICY_VERSION,
        "confidence_high": thresh.confidence_high,
        "confidence_low": thresh.confidence_low,
        "samples": 3,
        "matrix": "ALLOW_BLOCK_ESCALATE_v2",
    }
    canonical = json.dumps(payload, sort_keys=True)
    cfg_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return PolicySnapshot(
        confidence_high=thresh.confidence_high,
        confidence_low=thresh.confidence_low,
        self_consistency_samples=3,
        config_hash=cfg_hash,
    )
