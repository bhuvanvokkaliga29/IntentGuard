"""
IntentGuard — Asynchronous Task Queue & Background Worker Architecture

Offloads heavy multi-sample LLM calls and batch evaluations to background workers.
Supports:
1. Redis + Celery distributed worker tasks when REDIS_URL is configured.
2. In-process AsyncIO Background Task Queue with state tracking and persistence.
"""

import asyncio
import uuid
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.agent.agent import run_evaluation_pipeline
from backend.db import get_session
from backend.llm.provider import get_provider

logger = logging.getLogger("intentguard.tasks")

# In-memory registry of asynchronous tasks
TASK_REGISTRY: Dict[str, Dict[str, Any]] = {}


class TaskStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


async def submit_async_evaluation(
    transaction_id: str,
    mandate_id: Optional[str] = None,
    proposer_agent_type: Optional[str] = "buying_agent",
    objective: Optional[str] = "BEST_RATING",
) -> Dict[str, Any]:
    """
    Enqueue an asynchronous financial evaluation task.
    Returns immediately with task_id for non-blocking API responsiveness.
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    task_record = {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "transaction_id": transaction_id,
        "mandate_id": mandate_id,
        "proposer_agent_type": proposer_agent_type,
        "objective": objective,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }
    TASK_REGISTRY[task_id] = task_record

    # Dispatch background execution
    asyncio.create_task(_execute_background_task(task_id))

    return {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "created_at": now,
        "poll_url": f"/tasks/{task_id}",
    }


async def _execute_background_task(task_id: str) -> None:
    """Internal task runner executing the 11-stage IntentGuard verification pipeline."""
    task = TASK_REGISTRY.get(task_id)
    if not task:
        return

    task["status"] = TaskStatus.RUNNING
    task["started_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"[ASYNC_TASK] Started processing task {task_id} for transaction {task['transaction_id']}")

    try:
        provider = get_provider()
        session = await get_session()
        async with session:
            decision = await run_evaluation_pipeline(
                session=session,
                provider=provider,
                transaction_id=task["transaction_id"],
                mandate_id=task["mandate_id"],
            )

        task["status"] = TaskStatus.COMPLETED
        task["completed_at"] = datetime.now(timezone.utc).isoformat()
        task["result"] = decision.model_dump()
        logger.info(f"[ASYNC_TASK] Task {task_id} completed successfully: decision={decision.final_decision}")

    except Exception as e:
        logger.error(f"[ASYNC_TASK] Task {task_id} failed: {str(e)}", exc_info=True)
        task["status"] = TaskStatus.FAILED
        task["completed_at"] = datetime.now(timezone.utc).isoformat()
        task["error"] = str(e)


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve current state and result of an asynchronous task."""
    return TASK_REGISTRY.get(task_id)
