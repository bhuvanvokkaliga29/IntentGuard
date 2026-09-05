"""
IntentGuard — Pytest Fixtures & Async Database Lifecycle Management
"""

import pytest
from backend.db import close_db


@pytest.fixture(autouse=True)
async def cleanup_db_engine_after_test():
    """Ensure engine and connections are properly disposed so closed event loops never leak across test cases."""
    yield
    await close_db()
