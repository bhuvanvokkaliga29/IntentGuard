"""
IntentGuard — Pipeline Evaluator

Top-level orchestration that wires the agent pipeline to the API layer.
Handles provider initialization, error handling, and provider failure handling.
"""

import logging
from typing import Dict, Optional

from backend.config import get_settings
from backend.llm.provider import get_provider, LLMProvider

logger = logging.getLogger("intentguard.evaluator")


async def evaluate_transaction(
    session,
    transaction_id: str,
    mandate_id: Optional[str] = None,
    request_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict:
    """
    Evaluate a transaction through the full IntentGuard pipeline.
    
    This is the main entry point for transaction evaluation.
    Handles provider initialization and failure.
    """
    from backend.agent.agent import run_evaluation_pipeline

    # Initialize provider
    try:
        provider = get_provider()
        logger.info(
            f"[LLM] Provider initialized: {provider.provider_name} "
            f"({provider.model_name})"
        )
    except ValueError as e:
        logger.error(f"[LLM] Provider initialization failed: {e}")
        return {
            "decision_id": None,
            "transaction_id": transaction_id,
            "final_decision": "ESCALATE",
            "explanation": f"LLM provider initialization failed: {e}. Transaction escalated to human review.",
            "error": str(e),
            "latency_ms": 0,
        }

    # Run pipeline
    try:
        result = await run_evaluation_pipeline(
            session=session,
            provider=provider,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )
        return result

    except Exception as e:
        logger.error(f"[PIPELINE] Evaluation failed: {e}")
        return {
            "decision_id": None,
            "transaction_id": transaction_id,
            "final_decision": "ESCALATE",
            "explanation": f"Pipeline evaluation failed: {e}. Transaction escalated to human review.",
            "error": str(e),
            "latency_ms": 0,
        }
