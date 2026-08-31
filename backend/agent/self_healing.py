"""
IntentGuard — Agent Self-Healing & Fault Recovery Engine

Provides automated failure classification, bounded recovery strategies, retry management,
and safe-stop mechanisms for autonomous agent executions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from backend.db import create_agent_recovery, get_session
from backend.orchestrator.event_bus import get_event_bus

logger = logging.getLogger("intentguard.self_healing")


class FailureClassification:
    TRANSIENT_TOOL_FAILURE = "TRANSIENT_TOOL_FAILURE"
    TIMEOUT = "TIMEOUT"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    UNAVAILABLE_PRODUCT = "UNAVAILABLE_PRODUCT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    CRITICAL_SECURITY_BREACH = "CRITICAL_SECURITY_BREACH"
    UNKNOWN = "UNKNOWN"


class RecoveryStrategy:
    RETRY_TOOL = "RETRY_TOOL"
    REPAIR_SCHEMA = "REPAIR_SCHEMA"
    SUBSTITUTE_PRODUCT = "SUBSTITUTE_PRODUCT"
    FALLBACK_PROVIDER = "FALLBACK_PROVIDER"
    SAFE_STOP = "SAFE_STOP"
    ESCALATE = "ESCALATE"


class SelfHealingEngine:
    """Classifies runtime failures and executes bounded, safe recovery policies."""

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.event_bus = get_event_bus()

    def classify_failure(self, error: Exception, context: Dict[str, Any]) -> str:
        """Classify the root cause of an execution failure."""
        if hasattr(error, "failure_type") and getattr(error, "failure_type"):
            return getattr(error, "failure_type")
        err_str = str(error).lower()
        if "timeout" in err_str or "timed out" in err_str:
            return FailureClassification.TIMEOUT
        if "unavailable" in err_str or "stock" in err_str:
            return FailureClassification.UNAVAILABLE_PRODUCT
        if "json" in err_str or "parse" in err_str or "schema" in err_str:
            return FailureClassification.MALFORMED_OUTPUT
        if "bypass" in err_str or "override" in err_str or "security" in err_str:
            return FailureClassification.CRITICAL_SECURITY_BREACH
        if "provider" in err_str or "quota" in err_str or "503" in err_str:
            return FailureClassification.PROVIDER_UNAVAILABLE
        return FailureClassification.TRANSIENT_TOOL_FAILURE

    def determine_strategy(self, failure_type: str, attempt: int) -> str:
        """Map classified failure and attempt count to a safe recovery strategy."""
        if failure_type == FailureClassification.CRITICAL_SECURITY_BREACH:
            return RecoveryStrategy.SAFE_STOP

        if attempt >= self.max_retries:
            return RecoveryStrategy.SAFE_STOP

        if failure_type in (FailureClassification.TIMEOUT, FailureClassification.TRANSIENT_TOOL_FAILURE):
            return RecoveryStrategy.RETRY_TOOL
        elif failure_type == FailureClassification.MALFORMED_OUTPUT:
            return RecoveryStrategy.REPAIR_SCHEMA
        elif failure_type == FailureClassification.UNAVAILABLE_PRODUCT:
            return RecoveryStrategy.SUBSTITUTE_PRODUCT
        elif failure_type == FailureClassification.PROVIDER_UNAVAILABLE:
            return RecoveryStrategy.FALLBACK_PROVIDER

        return RecoveryStrategy.SAFE_STOP

    async def execute_recovery(
        self,
        run_id: str,
        agent_id: str,
        stage: str,
        error: Exception,
        attempt: int,
        retry_fn: Callable[[], Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Any, str]:
        """
        Orchestrate a bounded recovery attempt.
        Returns: (success: bool, result: Any, recovery_summary: str)
        """
        ctx = context or {}
        failure_type = self.classify_failure(error, ctx)
        strategy = self.determine_strategy(failure_type, attempt)

        # 1. Publish & Record Recovery Start
        await self.event_bus.publish(
            event_type="agent.recovery.started",
            run_id=run_id,
            agent_id=agent_id,
            stage=stage,
            payload={
                "failure_type": failure_type,
                "strategy": strategy,
                "attempt": attempt,
                "max_attempts": self.max_retries,
                "error_message": str(error),
            },
        )

        try:
            async with await get_session() as session:
                await create_agent_recovery(
                    session=session,
                    run_id=run_id,
                    agent_id=agent_id,
                    failure_type=failure_type,
                    recovery_strategy=strategy,
                    attempt=attempt,
                    max_attempts=self.max_retries,
                    status="IN_PROGRESS",
                    details={"error": str(error), "stage": stage},
                )
        except Exception:
            pass

        # 2. Execute Strategy
        if strategy == RecoveryStrategy.SAFE_STOP:
            summary = f"Recovery abandoned: Reached retry limit or encountered critical security condition. Safe-stopping."
            await self.event_bus.publish(
                event_type="agent.safe_stopped",
                run_id=run_id,
                agent_id=agent_id,
                stage=stage,
                payload={"reason": summary, "failure_type": failure_type},
            )
            return False, None, summary

        # Exponential backoff for tool retries
        backoff = 0.1 * (2 ** (attempt - 1))
        await asyncio.sleep(backoff)

        try:
            recovered_result = await retry_fn()

            summary = f"Self-healing succeeded on attempt {attempt}/{self.max_retries} via strategy '{strategy}'."
            await self.event_bus.publish(
                event_type="agent.recovery.completed",
                run_id=run_id,
                agent_id=agent_id,
                stage=stage,
                payload={
                    "status": "RECOVERED",
                    "strategy": strategy,
                    "attempt": attempt,
                    "summary": summary,
                },
            )
            return True, recovered_result, summary

        except Exception as retry_err:
            summary = f"Self-healing attempt {attempt} failed: {retry_err}"
            return False, None, summary


# Global Singleton
_self_healing_engine: Optional[SelfHealingEngine] = None


def get_self_healing_engine() -> SelfHealingEngine:
    global _self_healing_engine
    if _self_healing_engine is None:
        _self_healing_engine = SelfHealingEngine()
    return _self_healing_engine
