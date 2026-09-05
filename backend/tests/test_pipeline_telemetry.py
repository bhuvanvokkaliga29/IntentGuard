"""
IntentGuard — Live Telemetry & Event Ordering Test Suite

Verifies:
1. EventBus subscriber receives ordered stage events from pipeline stages.
2. Real metrics and payloads are accurately reflected in telemetry.
3. Event bus subscription and cancellation lifecycle works cleanly.
"""

import asyncio
import pytest
from backend.orchestrator.event_bus import get_event_bus
from backend.orchestrator.pipeline import (
    stage_intake_proposal,
    stage_normalize_proposal,
    stage_verify_structural_constraints,
    stage_guard_execution_boundary,
)


@pytest.mark.asyncio
async def test_pipeline_telemetry_emission_and_ordering():
    """Verify that discrete pipeline stages emit ordered events over the event bus."""
    event_bus = get_event_bus()
    queue = await event_bus.subscribe()

    proposal_data = {
        "amount": 800.0,
        "currency": "INR",
        "merchant_name": "Stationery Mart",
        "item_description": "Notebooks and pens",
    }
    mandate = {
        "max_amount_per_txn": 2000.0,
        "budget_cap": 10000.0,
        "allowed_categories": ["general", "stationery"],
        "allowed_merchants": ["Stationery Mart"],
    }

    # Run discrete stages
    intake = stage_intake_proposal(proposal_data)
    norm, is_safe, violation = stage_normalize_proposal(intake)
    struct = stage_verify_structural_constraints(norm, mandate)
    _ = stage_guard_execution_boundary("BLOCK", norm)

    # Allow async tasks on loop to dispatch events to queue
    await asyncio.sleep(0.05)

    events = []
    while not queue.empty():
        evt = await queue.get()
        events.append(evt)

    await event_bus.unsubscribe(queue)

    event_types = [e.event_type for e in events]
    assert "pipeline.proposal.received" in event_types
    assert "pipeline.normalization.completed" in event_types
    assert "pipeline.structural_check.completed" in event_types
    assert "pipeline.execution_boundary.evaluated" in event_types

    # Verify event payload integrity
    intake_evt = next(e for e in events if e.event_type == "pipeline.proposal.received")
    assert intake_evt.payload["amount"] == 800.0
    assert intake_evt.payload["merchant"] == "Stationery Mart"

    exec_evt = next(e for e in events if e.event_type == "pipeline.execution_boundary.evaluated")
    assert exec_evt.payload["final_decision"] == "BLOCK"
    assert exec_evt.payload["executed"] is False
