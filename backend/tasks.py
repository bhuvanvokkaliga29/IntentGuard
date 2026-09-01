"""
IntentGuard — Asynchronous Task Queue & Background Worker Architecture

Offloads heavy multi-sample LLM calls and batch evaluations to background workers.
Now uses persistent SQLite/Postgres backend for state tracking across service restarts.
"""

import asyncio
import json
import uuid
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.future import select

from backend.agent.agent import run_evaluation_pipeline
from backend.db import get_session, AsyncTaskRow
from backend.llm.provider import get_provider

logger = logging.getLogger("intentguard.tasks")


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
    Persists to database and returns immediately with task_id.
    """
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Persist task to database
    session = await get_session()
    async with session:
        task_row = AsyncTaskRow(
            task_id=task_id,
            status=TaskStatus.PENDING,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            proposer_agent_type=proposer_agent_type,
            objective=objective,
            created_at=now,
        )
        session.add(task_row)
        await session.commit()

    # Dispatch background execution
    asyncio.create_task(_execute_background_task(task_id))

    return {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "created_at": now.isoformat(),
        "poll_url": f"/tasks/{task_id}",
    }


async def _execute_background_task(task_id: str) -> None:
    """Internal task runner executing the 11-stage IntentGuard verification pipeline."""
    session = await get_session()
    async with session:
        stmt = select(AsyncTaskRow).where(AsyncTaskRow.task_id == task_id)
        result = await session.execute(stmt)
        task_row = result.scalars().first()
        
        if not task_row:
            logger.error(f"[ASYNC_TASK] Task {task_id} not found in DB")
            return

        task_row.status = TaskStatus.RUNNING
        task_row.started_at = datetime.now(timezone.utc)
        await session.commit()

        logger.info(f"[ASYNC_TASK] Started processing task {task_id} for transaction {task_row.transaction_id}")

        try:
            provider = get_provider()
            decision = await run_evaluation_pipeline(
                session=session,
                provider=provider,
                transaction_id=task_row.transaction_id,
                mandate_id=task_row.mandate_id,
            )

            task_row.status = TaskStatus.COMPLETED
            task_row.completed_at = datetime.now(timezone.utc)
            task_row.result = json.dumps(decision)
            await session.commit()
            logger.info(f"[ASYNC_TASK] Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"[ASYNC_TASK] Task {task_id} failed: {str(e)}", exc_info=True)
            task_row.status = TaskStatus.FAILED
            task_row.completed_at = datetime.now(timezone.utc)
            task_row.error = str(e)
            await session.commit()


async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve current state and result of an asynchronous task from the database."""
    session = await get_session()
    async with session:
        stmt = select(AsyncTaskRow).where(AsyncTaskRow.task_id == task_id)
        result = await session.execute(stmt)
        task_row = result.scalars().first()
        
        if not task_row:
            return None
            
        task_dict = {
            "task_id": task_row.task_id,
            "status": task_row.status,
            "transaction_id": task_row.transaction_id,
            "mandate_id": task_row.mandate_id,
            "proposer_agent_type": task_row.proposer_agent_type,
            "objective": task_row.objective,
            "created_at": task_row.created_at.isoformat() if task_row.created_at else None,
            "started_at": task_row.started_at.isoformat() if task_row.started_at else None,
            "completed_at": task_row.completed_at.isoformat() if task_row.completed_at else None,
            "error": task_row.error,
        }
        
        if task_row.result:
            try:
                task_dict["result"] = json.loads(task_row.result)
            except:
                task_dict["result"] = task_row.result
                
        return task_dict
