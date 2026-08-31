"""
IntentGuard — Tests for Agent Orchestrator, Tools, Self-Healing, and Observability
"""

import pytest
from backend.db import init_db, get_session
from backend.agent.tools import get_tool_registry
from backend.agent.self_healing import get_self_healing_engine, FailureClassification, RecoveryStrategy
from backend.orchestrator.state_machine import AgentStage, validate_stage_transition
from backend.orchestrator.orchestrator import get_agent_orchestrator
from backend.agent.proficiency import get_proficiency_engine


@pytest.mark.asyncio
async def test_stage_transition_validation():
    """Verify finite state machine transition rules."""
    assert validate_stage_transition(AgentStage.IDLE, AgentStage.INITIALIZING) is True
    assert validate_stage_transition(AgentStage.READING_CONTEXT, AgentStage.PLANNING) is True
    assert validate_stage_transition(AgentStage.TOOL_CALL, AgentStage.OBSERVING) is True
    assert validate_stage_transition(AgentStage.GENERATING_PROPOSAL, AgentStage.VALIDATING_PROPOSAL) is True
    assert validate_stage_transition(AgentStage.VALIDATING_PROPOSAL, AgentStage.SUBMITTING_TO_INTENTGUARD) is True

    # Illegal bypass direct to completed
    assert validate_stage_transition(AgentStage.IDLE, AgentStage.COMPLETED) is False
    assert validate_stage_transition(AgentStage.TOOL_CALL, AgentStage.COMPLETED) is False


@pytest.mark.asyncio
async def test_tool_registry_execution():
    """Verify tool execution and structured telemetry."""
    await init_db()
    registry = get_tool_registry()

    # 1. Catalog search
    res = await registry.execute_tool(
        tool_name="catalog.search",
        arguments={"query": "paper", "max_price": 2000.0},
        run_id="test-run-1",
        agent_id="test_agent",
    )
    assert res["products_found"] >= 1
    assert "summary" in res

    # 2. Merchant lookup
    m_res = await registry.execute_tool(
        tool_name="merchant.lookup",
        arguments={"merchant_name": "Stationery Mart"},
        run_id="test-run-1",
        agent_id="test_agent",
    )
    assert m_res["matched"] is True

    # 3. Pricing calculation
    p_res = await registry.execute_tool(
        tool_name="pricing.lookup",
        arguments={"sku": "prod-stat-paper-pens", "quantity": 2},
        run_id="test-run-1",
        agent_id="test_agent",
    )
    assert p_res["total_price"] > 0


@pytest.mark.asyncio
async def test_self_healing_classification_and_recovery():
    """Verify failure classification and recovery execution."""
    await init_db()
    healing = get_self_healing_engine()

    # Classification
    timeout_err = Exception("Tool 'catalog.search' timed out after 3000ms.")
    assert healing.classify_failure(timeout_err, {}) == FailureClassification.TIMEOUT

    strategy = healing.determine_strategy(FailureClassification.TIMEOUT, attempt=1)
    assert strategy == RecoveryStrategy.RETRY_TOOL

    # Recovery function execution
    retry_count = 0

    async def mock_retry():
        nonlocal retry_count
        retry_count += 1
        return {"status": "recovered"}

    success, res, summary = await healing.execute_recovery(
        run_id="test-heal-run",
        agent_id="test_agent",
        stage="TOOL_CALL",
        error=timeout_err,
        attempt=1,
        retry_fn=mock_retry,
    )
    assert success is True
    assert retry_count == 1
    assert "Self-healing succeeded" in summary


@pytest.mark.asyncio
async def test_orchestrated_buying_agent_run():
    """Verify end-to-end orchestrated buying agent run with IntentGuard gating."""
    await init_db()
    orchestrator = get_agent_orchestrator()

    result = await orchestrator.run_buying_agent(
        mandate_id="mandate-001-office-supplies",
        objective="BEST_RATING",
        injected_failure=None,
    )

    assert result["status"] == "COMPLETED"
    assert "run_id" in result
    assert "proposal" in result
    assert "intentguard_decision" in result
    assert result["latency_ms"] > 0
    assert "catalog.search" in result["tools_used"]


@pytest.mark.asyncio
async def test_orchestrated_buying_agent_self_healing_recovery():
    """Verify buying agent recovers cleanly when tool timeout failure is injected."""
    await init_db()
    orchestrator = get_agent_orchestrator()

    # Inject timeout on first attempt
    result = await orchestrator.run_buying_agent(
        mandate_id="mandate-001-office-supplies",
        objective="LOWEST_PRICE",
        injected_failure="timeout",
    )

    assert result["status"] == "COMPLETED"
    assert "intentguard_decision" in result


@pytest.mark.asyncio
async def test_proficiency_metrics_calculation():
    """Verify proficiency metrics computed strictly from DB records."""
    await init_db()
    engine = get_proficiency_engine()
    async with await get_session() as session:
        metrics = await engine.compute_metrics(session)

    assert "total_runs" in metrics
    assert "task_success_rate" in metrics
    assert "tool_success_rate" in metrics
    assert "health_status" in metrics
    assert metrics["health_status"] in ("HEALTHY", "DEGRADED", "RECOVERING")
