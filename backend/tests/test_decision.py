"""
IntentGuard — Decision Engine Tests

Unit tests for the deterministic policy engine.
The policy engine is testable independently of any LLM.
"""

import pytest
from backend.policy.decision import decide


class TestDecisionEngine:
    def test_structural_fail_blocks(self):
        """Hard constraint failure → BLOCK."""
        result = decide(
            structural_pass=False,
            majority_verdict=None,
            confidence_score=1.0,
            structural_failure_reasons=["Amount exceeds limit"],
        )
        assert result["final_decision"] == "BLOCK"
        assert "structural" in result["decision_path"].lower()

    def test_fit_high_confidence_allows(self):
        """Structural pass + FIT + high confidence → ALLOW."""
        result = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.85,
        )
        assert result["final_decision"] == "ALLOW"

    def test_no_fit_high_confidence_blocks(self):
        """Structural pass + NO_FIT + high confidence → BLOCK."""
        result = decide(
            structural_pass=True,
            majority_verdict="no_fit",
            confidence_score=0.85,
        )
        assert result["final_decision"] == "BLOCK"

    def test_ambiguous_escalates(self):
        """Structural pass + AMBIGUOUS → ESCALATE (human review required)."""
        result = decide(
            structural_pass=True,
            majority_verdict="ambiguous",
            confidence_score=0.70,
        )
        assert result["final_decision"] == "ESCALATE"

    def test_low_confidence_escalates(self):
        """Confidence below high threshold → ESCALATE (human review required)."""
        result = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.50,
        )
        assert result["final_decision"] == "ESCALATE"

    def test_very_low_confidence_escalates(self):
        """Very low confidence → ESCALATE."""
        result = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.20,
        )
        assert result["final_decision"] == "ESCALATE"

    def test_missing_facts_escalates(self):
        """Missing extracted facts → ESCALATE."""
        result = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.85,
            has_extracted_facts=False,
        )
        assert result["final_decision"] == "ESCALATE"

    def test_insufficient_evidence_escalates(self):
        """Insufficient evidence → ESCALATE."""
        result = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.85,
            evidence_is_sufficient=False,
        )
        assert result["final_decision"] == "ESCALATE"

    def test_no_verdict_escalates(self):
        """No semantic verdict → ESCALATE."""
        result = decide(
            structural_pass=True,
            majority_verdict=None,
            confidence_score=0.85,
        )
        assert result["final_decision"] == "ESCALATE"

    def test_decision_path_is_recorded(self):
        """Every decision records the logic path taken."""
        result = decide(
            structural_pass=True,
            majority_verdict="fit",
            confidence_score=0.85,
        )
        assert "decision_path" in result
        assert len(result["decision_path"]) > 0
