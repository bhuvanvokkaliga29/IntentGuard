"""
IntentGuard — Agent Pipeline

The single IntentGuard Agent. Exact pipeline sequence:

1. get_mandate()
2. get_transaction()
3. check_hard_constraints()
   → IF hard fail: BLOCK, skip semantic, log
4. get_merchant_context()
5. get_product_context()
6. extract_structured_facts()     [LLM Call 1]
7. semantic_compare()             [LLM Call 2 × N samples]
8. compute_confidence()           [deterministic]
9. deterministic_decision()       [deterministic]
10. explain()                     [LLM Call 3 or template]
11. audit_decision()              [deterministic, DB]

Do NOT reorder safety-critical operations.
"""

import logging
import time
import uuid
from typing import Dict, Optional

from backend.config import get_settings
from backend.llm.provider import LLMProvider
from backend.agent.tools import (
    tool_get_mandate,
    tool_get_transaction,
    tool_get_merchant_context,
    tool_get_product_context,
    tool_check_hard_constraints,
    tool_extract_structured_facts,
    tool_semantic_compare,
    tool_compute_confidence,
    tool_decide,
    tool_generate_explanation,
    tool_record_decision,
    tool_audit_decision,
)

logger = logging.getLogger("intentguard.agent")


async def run_evaluation_pipeline(
    session,
    provider: LLMProvider,
    transaction_id: str,
    mandate_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict:
    """
    Run the complete IntentGuard evaluation pipeline.
    
    This is the main agent loop. Each step is independently testable
    and independently logged.
    
    Args:
        session: Database session
        provider: LLM provider instance
        transaction_id: ID of the transaction to evaluate
        mandate_id: Optional mandate ID override (otherwise read from transaction)
        request_id: Optional request ID for tracing
    
    Returns:
        Dict with full decision response including audit trail
    """
    settings = get_settings()
    pipeline_start = time.time()
    request_id = request_id or str(uuid.uuid4())
    tool_call_records = []

    logger.info(f"[REQUEST] Starting evaluation: request={request_id}, transaction={transaction_id}")

    try:
        # ── Step 1: Get Transaction ───────────────────────────
        transaction, tool_record = await tool_get_transaction(session, transaction_id)
        tool_call_records.append(tool_record)

        if transaction is None:
            return _error_response(
                request_id, transaction_id, "Transaction not found",
                tool_call_records, pipeline_start
            )

        logger.info(f"[TOOL] Transaction retrieved: ₹{transaction['amount']:,.2f} at {transaction['merchant_name']}")

        # ── Step 2: Get Mandate ───────────────────────────────
        effective_mandate_id = mandate_id or transaction.get("mandate_id")
        if not effective_mandate_id:
            return _error_response(
                request_id, transaction_id, "No mandate_id specified",
                tool_call_records, pipeline_start
            )

        mandate, tool_record = await tool_get_mandate(session, effective_mandate_id)
        tool_call_records.append(tool_record)

        if mandate is None:
            return _error_response(
                request_id, transaction_id, f"Mandate {effective_mandate_id} not found",
                tool_call_records, pipeline_start
            )

        logger.info(f"[TOOL] Mandate retrieved: {mandate['intent_text'][:80]}...")

        # ── Step 3: Check Hard Constraints ────────────────────
        structural_result, tool_record = await tool_check_hard_constraints(mandate, transaction)
        tool_call_records.append(tool_record)

        logger.info(f"[POLICY] Structural check: {'PASS' if structural_result['overall_pass'] else 'FAIL'}")

        # If hard fail → BLOCK immediately, skip semantic
        if not structural_result["overall_pass"]:
            logger.info("[POLICY] Hard constraint failure → BLOCK (skipping semantic judgment)")

            decision_result, tool_record = await tool_decide(
                structural_result=structural_result,
                majority_verdict=None,
                confidence_score=1.0,  # High confidence in structural rejection
                has_extracted_facts=False,
                evidence_is_sufficient=True,
            )
            tool_call_records.append(tool_record)

            explanation = _build_structural_block_explanation(structural_result, transaction, mandate)

            # Record and audit
            return await _finalize_decision(
                session=session,
                request_id=request_id,
                mandate=mandate,
                transaction=transaction,
                structural_result=structural_result,
                extracted_facts=None,
                semantic_judgment=None,
                confidence_result={"confidence_score": 1.0, "agreement_rate": None, "base_confidence": 1.0},
                decision_result=decision_result,
                explanation=explanation,
                provider=provider,
                tool_call_records=tool_call_records,
                pipeline_start=pipeline_start,
            )

        # ── Step 4: Get Merchant Context ──────────────────────
        merchant_context, tool_record = await tool_get_merchant_context(
            transaction["merchant_name"],
            transaction["merchant_category"],
        )
        tool_call_records.append(tool_record)

        # ── Step 5: Get Product Context ───────────────────────
        product_context, tool_record = await tool_get_product_context(
            transaction["item_description"],
        )
        tool_call_records.append(tool_record)

        # Check if description is too vague for semantic judgment
        is_vague = product_context.get("description_quality") == "insufficient"

        # ── Step 6: Extract Structured Facts (LLM Call 1) ─────
        extracted_facts = None
        if not is_vague:
            extracted_facts, tool_record = await tool_extract_structured_facts(
                provider=provider,
                transaction=transaction,
                mandate_intent=mandate["intent_text"],
            )
            tool_call_records.append(tool_record)

            if extracted_facts is None:
                logger.warning("[LLM] Extraction failed → will ESCALATE")
        else:
            # Still try extraction even for vague descriptions
            extracted_facts, tool_record = await tool_extract_structured_facts(
                provider=provider,
                transaction=transaction,
                mandate_intent=mandate["intent_text"],
            )
            tool_call_records.append(tool_record)

        logger.info(f"[LLM] Facts extracted: {extracted_facts is not None}")

        # ── Step 7: Semantic Judgment (LLM Call 2 × N) ────────
        semantic_judgment_result = None
        semantic_verdicts = []

        if extracted_facts is not None:
            semantic_judgment_result, tool_record = await tool_semantic_compare(
                provider=provider,
                mandate_intent=mandate["intent_text"],
                allowed_categories=mandate.get("allowed_categories", []),
                extracted_facts=extracted_facts,
                transaction=transaction,
                num_samples=settings.self_consistency_samples,
            )
            tool_call_records.append(tool_record)

            if semantic_judgment_result:
                semantic_verdicts = [
                    s["verdict"] for s in semantic_judgment_result.get("samples", [])
                ]
                logger.info(
                    f"[LLM] Semantic judgment: {semantic_judgment_result.get('majority_verdict')}, "
                    f"agreement={semantic_judgment_result.get('agreement_rate')}"
                )
        else:
            logger.warning("[LLM] No extracted facts → skipping semantic judgment")

        # ── Step 8: Compute Confidence (deterministic) ────────
        confidence_result, tool_record = await tool_compute_confidence(
            structural_result=structural_result,
            semantic_verdicts=semantic_verdicts,
            extracted_facts=extracted_facts,
            txn_amount=transaction["amount"],
            mandate_max_amount=mandate["max_amount_per_txn"],
            mandate_location_constraint=mandate.get("location_constraint"),
        )
        tool_call_records.append(tool_record)

        logger.info(f"[POLICY] Confidence: {confidence_result['confidence_score']}")

        # ── Step 9: Deterministic Decision ────────────────────
        majority_verdict = None
        if semantic_judgment_result:
            majority_verdict = semantic_judgment_result.get("majority_verdict")

        decision_result, tool_record = await tool_decide(
            structural_result=structural_result,
            majority_verdict=majority_verdict,
            confidence_score=confidence_result["confidence_score"],
            has_extracted_facts=extracted_facts is not None,
            evidence_is_sufficient=not is_vague and extracted_facts is not None,
        )
        tool_call_records.append(tool_record)

        logger.info(
            f"[DECISION] {decision_result['final_decision']} "
            f"via {decision_result['decision_path']}"
        )

        # ── Step 10: Generate Explanation ─────────────────────
        semantic_rationale = None
        if semantic_judgment_result:
            semantic_rationale = semantic_judgment_result.get("combined_rationale")

        explanation, tool_record = await tool_generate_explanation(
            provider=provider,
            mandate_intent=mandate["intent_text"],
            transaction=transaction,
            structural_result=structural_result,
            extracted_facts=extracted_facts,
            semantic_verdict=majority_verdict,
            semantic_rationale=semantic_rationale,
            confidence_score=confidence_result["confidence_score"],
            final_decision=decision_result["final_decision"],
        )
        tool_call_records.append(tool_record)

        # ── Step 11: Record & Audit ───────────────────────────
        return await _finalize_decision(
            session=session,
            request_id=request_id,
            mandate=mandate,
            transaction=transaction,
            structural_result=structural_result,
            extracted_facts=extracted_facts,
            semantic_judgment=semantic_judgment_result,
            confidence_result=confidence_result,
            decision_result=decision_result,
            explanation=explanation,
            provider=provider,
            tool_call_records=tool_call_records,
            pipeline_start=pipeline_start,
        )

    except Exception as e:
        logger.error(f"[DECISION] Pipeline error: {e}", exc_info=True)
        return _error_response(
            request_id, transaction_id, str(e),
            tool_call_records, pipeline_start
        )


async def _finalize_decision(
    session,
    request_id: str,
    mandate: Dict,
    transaction: Dict,
    structural_result: Dict,
    extracted_facts: Optional[Dict],
    semantic_judgment: Optional[Dict],
    confidence_result: Dict,
    decision_result: Dict,
    explanation: str,
    provider: LLMProvider,
    tool_call_records: list,
    pipeline_start: float,
) -> Dict:
    """Record the decision and audit trail, return the full response."""
    settings = get_settings()
    total_latency_ms = int((time.time() - pipeline_start) * 1000)

    # Build decision data
    decision_id = str(uuid.uuid4())
    audit_id = str(uuid.uuid4())

    decision_data = {
        "id": decision_id,
        "transaction_id": transaction["id"],
        "mandate_id": mandate["id"],
        "structural_check_result": structural_result,
        "extracted_facts": extracted_facts,
        "semantic_judgment": semantic_judgment,
        "confidence_score": confidence_result["confidence_score"],
        "final_decision": decision_result["final_decision"],
        "explanation": explanation,
        "provider": provider.provider_name,
        "model": provider.model_name,
        "prompt_version": f"extraction_{settings.extraction_prompt_version}/"
                         f"semantic_{settings.semantic_prompt_version}/"
                         f"explanation_{settings.explanation_prompt_version}",
        "latency_ms": total_latency_ms,
        "audit_id": audit_id,
    }

    # Record decision
    _, tool_record = await tool_record_decision(session, decision_data)
    tool_call_records.append(tool_record)

    # Record audit
    audit_data = {
        "id": audit_id,
        "decision_id": decision_id,
        "request_id": request_id,
        "mandate_id": mandate["id"],
        "transaction_id": transaction["id"],
        "provider": provider.provider_name,
        "model": provider.model_name,
        "prompt_version": decision_data["prompt_version"],
        "tool_calls": tool_call_records,
        "structural_result": structural_result,
        "extracted_facts": extracted_facts,
        "semantic_samples": semantic_judgment.get("samples") if semantic_judgment else None,
        "confidence_calculation": confidence_result,
        "final_decision": decision_result["final_decision"],
        "explanation": explanation,
        "latency_ms": total_latency_ms,
    }

    _, tool_record = await tool_audit_decision(session, audit_data)
    tool_call_records.append(tool_record)

    logger.info(
        f"[AUDIT] Decision {decision_id} recorded. "
        f"Latency: {total_latency_ms}ms. "
        f"Decision: {decision_result['final_decision']}"
    )

    # Build response
    return {
        "decision_id": decision_id,
        "mandate_id": mandate["id"],
        "transaction_id": transaction["id"],
        "provider": provider.provider_name,
        "model": provider.model_name,
        "structural_result": structural_result,
        "extracted_facts": extracted_facts,
        "semantic_judgment": semantic_judgment,
        "confidence": confidence_result["confidence_score"],
        "confidence_details": confidence_result,
        "final_decision": decision_result["final_decision"],
        "decision_path": decision_result["decision_path"],
        "explanation": explanation,
        "latency_ms": total_latency_ms,
        "audit_id": audit_id,
    }


def _build_structural_block_explanation(
    structural_result: Dict,
    transaction: Dict,
    mandate: Dict,
) -> str:
    """Build explanation for a structural BLOCK."""
    failures = structural_result.get("failure_reasons", [])
    if failures:
        failure_text = " ".join(failures)
    else:
        failure_text = "Hard constraint violation detected."

    return (
        f"Transaction of ₹{transaction['amount']:,.2f} for "
        f"'{transaction['item_description']}' at {transaction['merchant_name']} "
        f"was blocked. {failure_text}"
    )


def _error_response(
    request_id: str,
    transaction_id: str,
    error: str,
    tool_call_records: list,
    pipeline_start: float,
) -> Dict:
    """Build an error response."""
    return {
        "decision_id": None,
        "mandate_id": None,
        "transaction_id": transaction_id,
        "provider": None,
        "model": None,
        "structural_result": None,
        "extracted_facts": None,
        "semantic_judgment": None,
        "confidence": 0.0,
        "final_decision": "ESCALATE",
        "decision_path": "error → ESCALATE",
        "explanation": f"Pipeline error: {error}. Transaction escalated to human review.",
        "latency_ms": int((time.time() - pipeline_start) * 1000),
        "audit_id": None,
        "error": error,
    }
