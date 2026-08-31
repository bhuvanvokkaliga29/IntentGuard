"""
IntentGuard — Distributed Celery Worker Service

For scalable Kubernetes / multi-container production deployments.
Runs background workers consuming evaluation tasks from Redis message queue.
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import get_settings

logger = logging.getLogger("intentguard.worker")

# Optional Celery integration when celery is installed and REDIS_URL is configured
try:
    from celery import Celery

    settings = get_settings()
    redis_broker = settings.redis_url or "redis://localhost:6379/0"

    celery_app = Celery(
        "intentguard_worker",
        broker=redis_broker,
        backend=redis_broker,
    )

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 min hard limit
    )

    @celery_app.task(name="tasks.evaluate_proposal_async", bind=True)
    def celery_evaluate_proposal(self, transaction_id: str, mandate_id: str):
        """Celery worker task for distributed evaluation."""
        import asyncio
        from backend.tasks import _execute_background_task, submit_async_evaluation

        logger.info(f"[CELERY_WORKER] Processing task for transaction {transaction_id}")
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(
            submit_async_evaluation(transaction_id=transaction_id, mandate_id=mandate_id)
        )
        return res

except ImportError:
    celery_app = None
    logger.info("[WORKER] Celery not installed. Using native in-process AsyncIO Task Queue.")


if __name__ == "__main__":
    if celery_app:
        celery_app.start()
    else:
        print("Celery not installed. Run 'pip install celery redis' for distributed worker mode.")
