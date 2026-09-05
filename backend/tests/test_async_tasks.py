"""
IntentGuard — Asynchronous Task Processing Test Suite

Tests:
1. POST /tasks/evaluate enqueues background task with 202 Accepted.
2. GET /tasks/{task_id} returns task status.
3. GET /tasks/{invalid_id} returns 404 Not Found.
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.db import init_db, get_session, create_mandate, create_transaction


@pytest.mark.asyncio
async def test_async_task_enqueue_and_poll():
    """Verify task enqueuing and status retrieval endpoints."""
    await init_db()

    # Create mandate and transaction to evaluate
    session = await get_session()
    async with session:
        mandate_id = str(uuid.uuid4())
        txn_id = str(uuid.uuid4())
        await create_mandate(session, {
            "id": mandate_id,
            "intent_text": "Buy office stationary",
            "max_amount_per_txn": 2000.0,
            "allowed_categories": ["office_supplies", "stationery"],
        })
        await create_transaction(session, {
            "id": txn_id,
            "mandate_id": mandate_id,
            "amount": 450.0,
            "merchant_name": "Stationery Mart",
            "merchant_category": "stationery",
            "item_description": "printer paper",
        })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Enqueue task
        enqueue_res = await client.post(
            "/tasks/evaluate",
            json={"transaction_id": txn_id, "mandate_id": mandate_id},
        )
        assert enqueue_res.status_code == 202
        data = enqueue_res.json()
        assert "task_id" in data
        assert data["status"] == "PENDING"
        assert f"/tasks/{data['task_id']}" == data["poll_url"]

        task_id = data["task_id"]

        # 2. Poll task status
        poll_res = await client.get(f"/tasks/{task_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        assert poll_data["task_id"] == task_id
        assert poll_data["status"] in ["PENDING", "RUNNING", "COMPLETED"]

        # 3. Non-existent task -> 404
        bad_res = await client.get(f"/tasks/{uuid.uuid4()}")
        assert bad_res.status_code == 404
