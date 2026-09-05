"""
IntentGuard — Modular 8-Stage Supervisory Control Pipeline

Architectural Invariant:
Autonomous agents propose transactions; IntentGuard verifies; deterministic policy controls; financial execution follows.
The LLM must NEVER have direct financial authorization.

8 Discrete Lifecycle Stages:
1. intake_proposal: Schema verification, constraint validation, idempotency tagging
2. normalize_proposal: Unicode normalization, zero-width stripping, prompt injection defense
3. verify_structural_constraints: Deterministic hard constraint checks (Fast-path rejection)
4. verify_semantic_intent: Boundary-encapsulated extraction + multi-sample semantic consistency
5. assess_confidence: Deterministic confidence scoring based on evidence and agreement
6. evaluate_deterministic_policy: Deterministic policy decision (ALLOW, BLOCK, ESCALATE)
7. record_audit_event: Immutable, SHA-256 hash-chained audit logging
8. guard_execution_boundary: Strict execution gatekeeper (Razorpay order only on ALLOW)
"""

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.config import get_settings
from backend.execution.razorpay_gateway import get_razorpay_gateway
from backend.llm.provider import LLMProvider
from backend.models import (
    ConstraintCheck,
    DecisionResponse,
    FinalDecision,
    StructuralResult,
    TransactionProposalCreate,
)
from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide
from backend.security.prompt_defense import (
    encapsulate_untrusted_input,
    evaluate_prompt_defense,
    normalize_untrusted_text,
)

logger = logging.getLogger("intentguard.orchestrator.pipeline")


# ── Stage 1: Intake Proposal ─────────────────────────────────
def stage_intake_proposal(
    proposal_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Stage 1: Intake and strictly validate incoming transaction proposal.
    Ensures positive amount, valid currency (INR), non-empty merchant/description,
    and assigns or validates idempotency keys.
    """
    amount = float(proposal_data.get("amount", 0.0))
    if amount <= 0:
        raise ValueError(f"Proposal amount must be positive. Received: ₹{amount}")

    currency = str(proposal_data.get("currency", "INR")).strip().upper()
    if currency != "INR":
        raise ValueError(f"Only INR currency is supported. Received: {currency}")

    merchant_name = str(proposal_data.get("merchant_name", "")).strip()
    if not merchant_name:
        raise ValueError("Merchant name cannot be empty")

    item_description = str(proposal_data.get("item_description", "")).strip()
    if not item_description:
        raise ValueError("Item description cannot be empty")

    idempotency_key = (
        proposal_data.get("idempotency_key")
        or proposal_data.get("id")
        or f"prop_{hashlib.sha256(f'{merchant_name}:{amount}:{item_description}'.encode()).hexdigest()[:16]}"
    )

    intake = dict(proposal_data)
    intake["id"] = proposal_data.get("id") or str(uuid.uuid4())
    intake["amount"] = amount
    intake["currency"] = currency
    intake["merchant_name"] = merchant_name
    intake["merchant_category"] = str(proposal_data.get("merchant_category", "general")).strip().lower()
    intake["item_description"] = item_description
    intake["idempotency_key"] = idempotency_key
    intake["proposer_agent"] = str(proposal_data.get("proposer_agent", "AutonomousAgent")).strip()
    intake["declared_purpose"] = str(proposal_data.get("declared_purpose", "")).strip()

    return intake


# ── Stage 2: Normalize & Sanitize Proposal ───────────────────
def stage_normalize_proposal(
    proposal: Dict[str, Any],
) -> Tuple[Dict[str, Any], bool, Optional[str]]:
    """
    Stage 2: Normalize untrusted strings and evaluate prompt-injection defense.
    Returns: (normalized_proposal, is_safe, violation_reason)
    """
    normalized = dict(proposal)
    normalized["merchant_name"] = normalize_untrusted_text(proposal.get("merchant_name", ""))
    normalized["item_description"] = normalize_untrusted_text(proposal.get("item_description", ""))
    normalized["notes"] = normalize_untrusted_text(proposal.get("notes", ""))
    normalized["declared_purpose"] = normalize_untrusted_text(proposal.get("declared_purpose", ""))

    # Evaluate multi-surface prompt defense
    is_safe, violation = evaluate_prompt_defense(
        normalized.get("item_description", ""),
        normalized.get("merchant_name", ""),
        normalized.get("notes", ""),
        normalized.get("declared_purpose", ""),
        normalized.get("metadata", {}),
    )

    return normalized, is_safe, violation


# ── Stage 3: Verify Structural Constraints (Fast Path) ──────
def stage_verify_structural_constraints(
    proposal: Dict[str, Any],
    mandate: Dict[str, Any],
    cumulative_spent: float = 0.0,
) -> StructuralResult:
    """
    Stage 3: Pure deterministic check of mandate hard constraints.
    Zero LLM involvement. Fast-path fail if any hard constraint is breached.
    """
    return check_hard_constraints(
        txn_amount=proposal["amount"],
        txn_merchant_name=proposal["merchant_name"],
        txn_merchant_category=proposal.get("merchant_category", "general"),
        txn_item_description=proposal["item_description"],
        mandate_max_amount_per_txn=mandate["max_amount_per_txn"],
        mandate_budget_cap=mandate.get("budget_cap"),
        mandate_allowed_categories=mandate.get("allowed_categories", []),
        mandate_allowed_merchants=mandate.get("allowed_merchants"),
        mandate_frequency=mandate.get("frequency", "on_demand"),
        mandate_exclusions=mandate.get("exclusions"),
        mandate_location_constraint=mandate.get("location_constraint"),
        cumulative_spent=cumulative_spent,
        transaction_location_hint=proposal.get("location_hint"),
    )


# ── Stage 4: Verify Semantic Intent (LLM Isolation) ─────────
async def stage_verify_semantic_intent(
    proposal: Dict[str, Any],
    mandate: Dict[str, Any],
    provider: LLMProvider,
    num_samples: int = 3,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], List[str]]:
    """
    Stage 4: Semantic verification with prompt boundary encapsulation.
    Wraps all untrusted transaction inputs in <untrusted_transaction_data>.
    Returns: (extracted_facts, semantic_judgment_result, semantic_verdicts)
    """
    from backend.agent.tools import tool_extract_structured_facts, tool_semantic_compare

    # Untrusted inputs are encapsulated
    safe_transaction = dict(proposal)
    safe_transaction["item_description"] = encapsulate_untrusted_input(proposal.get("item_description", ""))
    safe_transaction["merchant_name"] = encapsulate_untrusted_input(proposal.get("merchant_name", ""))

    extracted_facts, _ = await tool_extract_structured_facts(
        provider=provider,
        transaction=safe_transaction,
        mandate_intent=mandate.get("intent_text", ""),
    )

    if not extracted_facts:
        logger.warning("[SEMANTIC] Fact extraction returned None; fail-safe will apply.")
        return None, None, []

    semantic_judgment, _ = await tool_semantic_compare(
        provider=provider,
        mandate_intent=mandate.get("intent_text", ""),
        allowed_categories=mandate.get("allowed_categories", []),
        extracted_facts=extracted_facts,
        transaction=safe_transaction,
        num_samples=num_samples,
    )

    semantic_verdicts = []
    if semantic_judgment and "samples" in semantic_judgment:
        semantic_verdicts = [s.get("verdict") for s in semantic_judgment["samples"]]

    return extracted_facts, semantic_judgment, semantic_verdicts


# ── Stage 5: Assess Confidence (Deterministic) ───────────────
async def stage_assess_confidence(
    structural_result: StructuralResult,
    semantic_verdicts: List[str],
    extracted_facts: Optional[Dict[str, Any]],
    proposal: Dict[str, Any],
    mandate: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Stage 5: Deterministic confidence scoring.
    Combines agreement rate, evidence completeness, and structural margins.
    """
    from backend.agent.tools import tool_compute_confidence

    confidence_dict, _ = await tool_compute_confidence(
        structural_result=structural_result.model_dump() if hasattr(structural_result, "model_dump") else dict(structural_result),
        semantic_verdicts=semantic_verdicts,
        extracted_facts=extracted_facts,
        txn_amount=proposal["amount"],
        mandate_max_amount=mandate["max_amount_per_txn"],
        mandate_location_constraint=mandate.get("location_constraint"),
    )
    return confidence_dict


# ── Stage 6: Evaluate Deterministic Policy ───────────────────
def stage_evaluate_deterministic_policy(
    structural_result: Any,
    semantic_verdict: Optional[str],
    confidence_score: float,
    evidence_is_sufficient: bool = True,
    security_violation: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stage 6: Deterministic policy decision engine.
    Applies strict priority:
    1. Security violation (prompt injection) -> BLOCK
    2. Structural hard failure -> BLOCK (Fast Path)
    3. Missing / insufficient evidence -> ESCALATE
    4. Semantic "fit" with confidence >= threshold -> ALLOW
    5. Semantic "no_fit" with confidence >= threshold -> BLOCK
    6. Borderline / ambiguous / low confidence -> ESCALATE
    """
    settings = get_settings()

    if security_violation:
        return {
            "final_decision": "BLOCK",
            "decision_path": "security_guardrail_violation -> BLOCK",
            "explanation": f"Transaction blocked: {security_violation}.",
        }

    struct_dict = (
        structural_result.model_dump()
        if hasattr(structural_result, "model_dump")
        else dict(structural_result)
    )

    if not struct_dict.get("overall_pass", False):
        failures = struct_dict.get("failure_reasons", [])
        detail = " ".join(failures) if failures else "Mandate hard constraint violation."
        return {
            "final_decision": "BLOCK",
            "decision_path": "structural_hard_constraint_failure -> BLOCK",
            "explanation": f"Transaction rejected by structural hard constraints. {detail}",
        }

    # If structural passed, evaluate deterministic policy via decision engine
    return decide(
        structural_pass=True,
        majority_verdict=semantic_verdict,
        confidence_score=confidence_score,
        has_extracted_facts=True,
        evidence_is_sufficient=evidence_is_sufficient,
    )


# ── Stage 7: Record Audit Event (SHA-256 Chained) ────────────
async def stage_record_audit_event(
    session,
    proposal: Dict[str, Any],
    mandate: Dict[str, Any],
    decision_data: Dict[str, Any],
    audit_data: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Stage 7: Record decision and cryptographic audit log.
    Ensures sequential sequence_number and SHA-256 hash chaining.
    """
    from backend.db import create_audit_log, create_decision

    dec_row = await create_decision(session, decision_data)
    audit_row = await create_audit_log(session, audit_data)

    return dec_row.id, audit_row.id


# ── Stage 8: Guard Financial Execution Boundary ──────────────
def stage_guard_execution_boundary(
    final_decision: str,
    proposal: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Stage 8: Strict execution boundary enforcement.
    CRITICAL INVARIANT:
    Financial execution can ONLY occur if the decision is explicitly 'ALLOW'.
    Under BLOCK or ESCALATE, execution is strictly forbidden and rejected.
    """
    if final_decision != "ALLOW":
        logger.info(
            f"[EXECUTION_BOUNDARY] Execution prevented: decision is '{final_decision}' "
            f"(only ALLOW decisions can be dispatched for settlement)"
        )
        return {
            "executed": False,
            "status": "BLOCKED_BY_GUARDRAIL",
            "reason": f"Execution gate rejected transaction: final decision is '{final_decision}'",
            "order": None,
        }

    # Transaction is officially authorized by IntentGuard
    gateway = get_razorpay_gateway()
    idempotency_key = (
        proposal.get("idempotency_key")
        or proposal.get("id")
        or f"exec_{proposal['merchant_name']}_{proposal['amount']}"
    )

    logger.info(
        f"[EXECUTION_BOUNDARY] Dispatching approved transaction to Razorpay gateway: "
        f"₹{proposal['amount']:,.2f} at {proposal['merchant_name']} (Key: {idempotency_key})"
    )

    order = gateway.create_order(
        amount=proposal["amount"],
        currency=proposal.get("currency", "INR"),
        receipt=f"rcpt_{proposal.get('id', 'intentguard')[:16]}",
        idempotency_key=idempotency_key,
    )

    return {
        "executed": order.get("success", False),
        "status": "DISPATCHED" if order.get("success") else "DISPATCH_FAILED",
        "order": order,
    }
