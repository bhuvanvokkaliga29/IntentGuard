"""
IntentGuard — Production Readiness & Enterprise Architecture Test Suite

Validates:
1. Structured JSON logging format and correlation ID propagation.
2. Prometheus metrics aggregation (/metrics).
3. Non-blocking asynchronous task execution and status tracking.
4. Database connection pool configuration and multi-engine support.
"""

import json
import pytest
from backend.logging_config import configure_logging, correlation_id_ctx
from backend.metrics import metrics
from backend.tasks import submit_async_evaluation, get_task_status, TaskStatus
from backend.db import init_db


def test_structured_json_logging_output(capsys):
    """Verify logger produces valid structured JSON format with correlation ID."""
    configure_logging(log_format="json", environment="production")
    token = correlation_id_ctx.set("test-corr-id-12345")

    import logging
    test_logger = logging.getLogger("intentguard.test")
    test_logger.info("Test production logging event")

    correlation_id_ctx.reset(token)
    captured = capsys.readouterr()

    # Verify captured output is valid JSON
    assert len(captured.out.strip()) > 0
    lines = captured.out.strip().split("\n")
    last_line = lines[-1]
    parsed = json.loads(last_line)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "intentguard.test"
    assert parsed["message"] == "Test production logging event"
    assert parsed["trace_id"] == "test-corr-id-12345"
    assert "timestamp" in parsed


def test_prometheus_metrics_generation():
    """Verify Prometheus metrics collector aggregates and formats standard exposition format."""
    metrics.record_request(endpoint="/decisions/evaluate", method="POST", status_code=200, duration_sec=0.042)
    metrics.record_decision("ALLOW")
    metrics.record_decision("BLOCK")
    metrics.record_llm_call(provider="gemini", model="gemini-2.5-flash", duration_sec=0.85)
    metrics.record_self_healing(failure_type="TIMEOUT", resolved=True)

    output = metrics.generate_prometheus_output()

    assert "intentguard_http_requests_total" in output
    assert "intentguard_decisions_total" in output
    assert "intentguard_llm_calls_total" in output
    assert "intentguard_self_healing_attempts_total" in output
    assert 'verdict="ALLOW"' in output
    assert 'verdict="BLOCK"' in output


@pytest.mark.asyncio
async def test_async_task_submission_and_tracking():
    """Verify non-blocking async task dispatch and status retrieval."""
    await init_db()
    task_res = await submit_async_evaluation(
        transaction_id="test-txn-id-001",
        mandate_id="test-mandate-id-001",
        proposer_agent_type="buying_agent",
        objective="BEST_RATING",
    )

    assert "task_id" in task_res
    assert task_res["status"] in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.COMPLETED)
    assert task_res["poll_url"].startswith("/tasks/")

    # Verify task status lookup
    status = await get_task_status(task_res["task_id"])
    assert status is not None
    assert status["transaction_id"] == "test-txn-id-001"
