"""
IntentGuard — Cryptographic Audit Ledger Hash Chain Tests

Tests tamper-evident verification:
1. Valid chain generation and verification
2. Tampered content detection
3. Tampered previous_hash detection
4. Deleted intermediate record detection
5. Reordered records detection
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from backend.db import (
    Base,
    AuditLogRow,
    GENESIS_HASH,
    compute_record_hash,
    create_audit_log,
    verify_audit_chain,
)


@pytest.fixture
async def memory_db_session():
    """Isolated in-memory SQLite database for audit chain tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_empty_audit_chain_is_valid(memory_db_session: AsyncSession):
    """An empty audit log should pass verification cleanly."""
    is_valid, errors = await verify_audit_chain(memory_db_session)
    assert is_valid is True
    assert errors == []


@pytest.mark.asyncio
async def test_valid_sequential_audit_chain(memory_db_session: AsyncSession):
    """Multiple sequential audit log entries should form an unbroken, valid hash chain."""
    for i in range(5):
        await create_audit_log(
            memory_db_session,
            {
                "decision_id": f"dec-{i}",
                "mandate_id": "mandate-001",
                "transaction_id": f"txn-{i}",
                "final_decision": "ALLOW" if i % 2 == 0 else "BLOCK",
                "explanation": f"Test explanation {i}",
                "structural_result": {"overall_pass": True},
            },
        )

    is_valid, errors = await verify_audit_chain(memory_db_session)
    assert is_valid is True
    assert len(errors) == 0

    # Verify first entry has GENESIS_HASH
    result = await memory_db_session.execute(
        select(AuditLogRow).order_by(AuditLogRow.timestamp.asc(), AuditLogRow.id.asc())
    )
    rows = list(result.scalars().all())
    assert len(rows) == 5
    assert rows[0].previous_record_hash == GENESIS_HASH
    for i in range(1, 5):
        assert rows[i].previous_record_hash == rows[i - 1].current_record_hash


@pytest.mark.asyncio
async def test_tampered_record_content_fails_verification(memory_db_session: AsyncSession):
    """Modifying the content of an audit record must cause verification to fail."""
    for i in range(3):
        await create_audit_log(
            memory_db_session,
            {
                "decision_id": f"dec-{i}",
                "mandate_id": "mandate-001",
                "transaction_id": f"txn-{i}",
                "final_decision": "BLOCK",
            },
        )

    # Tamper with middle record: illegally flip BLOCK to ALLOW
    result = await memory_db_session.execute(
        select(AuditLogRow).where(AuditLogRow.decision_id == "dec-1")
    )
    row = result.scalar_one()
    row.final_decision = "ALLOW"
    await memory_db_session.commit()

    is_valid, errors = await verify_audit_chain(memory_db_session)
    assert is_valid is False
    assert any("Record content tampered" in err for err in errors)


@pytest.mark.asyncio
async def test_deleted_intermediate_record_breaks_chain(memory_db_session: AsyncSession):
    """Deleting a record from the chain breaks previous_record_hash link."""
    for i in range(4):
        await create_audit_log(
            memory_db_session,
            {
                "decision_id": f"dec-{i}",
                "mandate_id": "mandate-001",
                "transaction_id": f"txn-{i}",
                "final_decision": "ALLOW",
            },
        )

    # Delete record #2
    result = await memory_db_session.execute(
        select(AuditLogRow).where(AuditLogRow.decision_id == "dec-2")
    )
    row = result.scalar_one()
    await memory_db_session.delete(row)
    await memory_db_session.commit()

    is_valid, errors = await verify_audit_chain(memory_db_session)
    assert is_valid is False
    assert any("Chain broken" in err for err in errors)


@pytest.mark.asyncio
async def test_reordered_records_breaks_chain(memory_db_session: AsyncSession):
    """Reordering records in the chain breaks sequence and previous hash linkages."""
    for i in range(3):
        await create_audit_log(
            memory_db_session,
            {
                "decision_id": f"dec-{i}",
                "mandate_id": "mandate-001",
                "transaction_id": f"txn-{i}",
                "final_decision": "ALLOW",
            },
        )

    # Swap sequence_numbers between record 1 and 2
    res1 = await memory_db_session.execute(select(AuditLogRow).where(AuditLogRow.decision_id == "dec-0"))
    res2 = await memory_db_session.execute(select(AuditLogRow).where(AuditLogRow.decision_id == "dec-1"))
    row1 = res1.scalar_one()
    row2 = res2.scalar_one()
    
    row1.sequence_number, row2.sequence_number = row2.sequence_number, row1.sequence_number
    await memory_db_session.commit()

    is_valid, errors = await verify_audit_chain(memory_db_session)
    assert is_valid is False
    assert len(errors) > 0
