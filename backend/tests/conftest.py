"""
IntentGuard — Pytest Fixtures & Async Database Lifecycle Management
"""

import pytest
import asyncio
from backend.db import close_db
from backend.orchestrator.event_bus import reset_event_bus


@pytest.fixture(autouse=True)
async def cleanup_db_engine_after_test():
    """Ensure engine, connections, and event bus are properly disposed so closed event loops never leak across test cases."""
    yield
    await close_db()
    reset_event_bus()
    await asyncio.sleep(0.01)


