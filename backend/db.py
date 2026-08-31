"""
IntentGuard — Database Layer

SQLAlchemy async engine with SQLite (dev) / PostgreSQL (prod).
Provides CRUD operations for mandates, transactions, decisions, and audit logs.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Boolean,
    create_engine,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.config import get_settings


# ── ORM Base ─────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── ORM Models ───────────────────────────────────────────────

class MandateRow(Base):
    __tablename__ = "mandates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    intent_text: Mapped[str] = mapped_column(Text, nullable=False)
    max_amount_per_txn: Mapped[float] = mapped_column(Float, nullable=False)
    budget_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    allowed_categories: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    allowed_merchants: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array or null
    frequency: Mapped[str] = mapped_column(String(50), nullable=False, default="on_demand")
    exclusions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array or null
    location_constraint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purpose_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TransactionRow(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mandate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    merchant_category: Mapped[str] = mapped_column(String(255), nullable=False)
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ground_truth_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ground_truth_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False)
    mandate_id: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    structural_check_result: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON
    extracted_facts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    semantic_judgment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_decision: Mapped[str] = mapped_column(String(20), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    audit_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    human_review_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # APPROVED, REJECTED, REQUEST_INFO
    human_review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    mandate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tool_calls: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON
    structural_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_facts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    semantic_samples: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_calculation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvaluationRunRow(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelVersionRow(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentRunRow(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    task_id: Mapped[str] = mapped_column(String(50), nullable=False)
    mandate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING")
    current_stage: Mapped[str] = mapped_column(String(50), default="INITIALIZING")
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    tools_used: Mapped[str] = mapped_column(Text, default="[]")
    proposal_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    decision_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observable_summary: Mapped[str] = mapped_column(Text, default="{}")


class AgentEventRow(Base):
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ToolCallRow(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(50), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, default="{}")
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="STARTED")
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AgentRecoveryRow(Base):
    __tablename__ = "agent_recoveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recovery_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(30), default="IN_PROGRESS")
    details: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Engine Management ────────────────────────────────────────

_engine = None
_session_factory = None


async def get_engine():
    """Get or create the async engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True,
        )
    return _engine


async def get_session_factory():
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncSession:
    """Get a new database session."""
    factory = await get_session_factory()
    return factory()


async def init_db():
    """Initialize the database — create all tables and apply column migrations."""
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Safe column migrations for existing databases
        for col_def in [
            "ALTER TABLE decisions ADD COLUMN human_review_status VARCHAR(50)",
            "ALTER TABLE decisions ADD COLUMN human_review_notes TEXT",
            "ALTER TABLE decisions ADD COLUMN human_reviewed_at DATETIME",
        ]:
            try:
                await conn.execute(text(col_def))
            except Exception:
                pass


async def reset_db():
    """Drop and recreate all tables (for testing/development)."""
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


# ── CRUD Operations ──────────────────────────────────────────

def _json_loads_safe(value: Optional[str]) -> Any:
    """Safely load JSON from a nullable string."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _json_dumps_safe(value: Any) -> str:
    """Safely dump value to JSON string."""
    if value is None:
        return "null"
    return json.dumps(value, default=str)


# ── Mandate CRUD ─────────────────────────────────────────────

async def create_mandate(session: AsyncSession, mandate_data: dict) -> MandateRow:
    """Create a new mandate."""
    row = MandateRow(
        id=mandate_data.get("id", str(uuid.uuid4())),
        intent_text=mandate_data["intent_text"],
        max_amount_per_txn=mandate_data["max_amount_per_txn"],
        budget_cap=mandate_data.get("budget_cap"),
        allowed_categories=json.dumps(mandate_data.get("allowed_categories", [])),
        allowed_merchants=json.dumps(mandate_data["allowed_merchants"]) if mandate_data.get("allowed_merchants") else None,
        frequency=mandate_data.get("frequency", "on_demand"),
        exclusions=json.dumps(mandate_data["exclusions"]) if mandate_data.get("exclusions") else None,
        location_constraint=mandate_data.get("location_constraint"),
        purpose_context=mandate_data.get("purpose_context"),
        created_at=mandate_data.get("created_at", datetime.utcnow()),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_mandate(session: AsyncSession, mandate_id: str) -> Optional[MandateRow]:
    """Fetch a mandate by ID."""
    result = await session.get(MandateRow, mandate_id)
    return result


async def list_mandates(session: AsyncSession) -> List[MandateRow]:
    """List all mandates."""
    from sqlalchemy import select
    result = await session.execute(select(MandateRow).order_by(MandateRow.created_at))
    return list(result.scalars().all())


def mandate_row_to_dict(row: MandateRow) -> dict:
    """Convert a MandateRow to a dictionary with parsed JSON fields."""
    return {
        "id": row.id,
        "intent_text": row.intent_text,
        "max_amount_per_txn": row.max_amount_per_txn,
        "budget_cap": row.budget_cap,
        "allowed_categories": _json_loads_safe(row.allowed_categories) or [],
        "allowed_merchants": _json_loads_safe(row.allowed_merchants),
        "frequency": row.frequency,
        "exclusions": _json_loads_safe(row.exclusions),
        "location_constraint": row.location_constraint,
        "purpose_context": row.purpose_context,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# ── Transaction CRUD ─────────────────────────────────────────

async def create_transaction(session: AsyncSession, txn_data: dict) -> TransactionRow:
    """Create a new transaction."""
    row = TransactionRow(
        id=txn_data.get("id", str(uuid.uuid4())),
        mandate_id=txn_data["mandate_id"],
        amount=txn_data["amount"],
        merchant_name=txn_data["merchant_name"],
        merchant_category=txn_data["merchant_category"],
        item_description=txn_data["item_description"],
        timestamp=txn_data.get("timestamp", datetime.utcnow()),
        ground_truth_tier=txn_data.get("ground_truth_tier"),
        ground_truth_reason=txn_data.get("ground_truth_reason"),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_transaction(session: AsyncSession, txn_id: str) -> Optional[TransactionRow]:
    """Fetch a transaction by ID."""
    result = await session.get(TransactionRow, txn_id)
    return result


async def list_transactions(session: AsyncSession, mandate_id: Optional[str] = None) -> List[TransactionRow]:
    """List transactions, optionally filtered by mandate."""
    from sqlalchemy import select
    query = select(TransactionRow)
    if mandate_id:
        query = query.where(TransactionRow.mandate_id == mandate_id)
    query = query.order_by(TransactionRow.timestamp)
    result = await session.execute(query)
    return list(result.scalars().all())


def transaction_row_to_dict(row: TransactionRow, include_ground_truth: bool = False) -> dict:
    """Convert a TransactionRow to a dictionary."""
    d = {
        "id": row.id,
        "mandate_id": row.mandate_id,
        "amount": row.amount,
        "merchant_name": row.merchant_name,
        "merchant_category": row.merchant_category,
        "item_description": row.item_description,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
    }
    if include_ground_truth:
        d["ground_truth_tier"] = row.ground_truth_tier
        d["ground_truth_reason"] = row.ground_truth_reason
    return d


# ── Decision CRUD ────────────────────────────────────────────

async def create_decision(session: AsyncSession, decision_data: dict) -> DecisionRow:
    """Create a new decision record."""
    row = DecisionRow(
        id=decision_data.get("id", str(uuid.uuid4())),
        transaction_id=decision_data["transaction_id"],
        mandate_id=decision_data.get("mandate_id", ""),
        structural_check_result=_json_dumps_safe(decision_data.get("structural_check_result")),
        extracted_facts=_json_dumps_safe(decision_data.get("extracted_facts")),
        semantic_judgment=_json_dumps_safe(decision_data.get("semantic_judgment")),
        confidence_score=decision_data["confidence_score"],
        final_decision=decision_data["final_decision"],
        explanation=decision_data["explanation"],
        provider=decision_data.get("provider"),
        model=decision_data.get("model"),
        prompt_version=decision_data.get("prompt_version"),
        latency_ms=decision_data.get("latency_ms", 0),
        audit_id=decision_data.get("audit_id"),
        created_at=decision_data.get("created_at", datetime.utcnow()),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_decision(session: AsyncSession, decision_id: str) -> Optional[DecisionRow]:
    """Fetch a decision by ID."""
    return await session.get(DecisionRow, decision_id)


async def list_decisions(session: AsyncSession) -> List[DecisionRow]:
    """List all decisions."""
    from sqlalchemy import select
    result = await session.execute(select(DecisionRow).order_by(DecisionRow.created_at.desc()))
    return list(result.scalars().all())


def decision_row_to_dict(row: DecisionRow) -> dict:
    """Convert a DecisionRow to a dictionary."""
    return {
        "id": row.id,
        "decision_id": row.id,
        "transaction_id": row.transaction_id,
        "mandate_id": row.mandate_id,
        "structural_result": _json_loads_safe(row.structural_check_result),
        "extracted_facts": _json_loads_safe(row.extracted_facts),
        "semantic_judgment": _json_loads_safe(row.semantic_judgment),
        "confidence": row.confidence_score,
        "final_decision": row.final_decision,
        "explanation": row.explanation,
        "provider": row.provider,
        "model": row.model,
        "prompt_version": row.prompt_version,
        "latency_ms": row.latency_ms,
        "audit_id": row.audit_id,
        "human_review_status": row.human_review_status,
        "human_review_notes": row.human_review_notes,
        "human_reviewed_at": row.human_reviewed_at.isoformat() if row.human_reviewed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def update_decision_review(
    session: AsyncSession,
    decision_id: str,
    action: str,
    notes: Optional[str] = None,
) -> Optional[DecisionRow]:
    """Update human review decision for a flagged or escalated record."""
    row = await get_decision(session, decision_id)
    if row is None:
        return None
    row.human_review_status = action.upper()
    row.human_review_notes = notes
    row.human_reviewed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(row)
    return row


# ── Audit CRUD ───────────────────────────────────────────────

async def create_audit_log(session: AsyncSession, audit_data: dict) -> AuditLogRow:
    """Create a new audit log entry."""
    row = AuditLogRow(
        id=audit_data.get("id", str(uuid.uuid4())),
        decision_id=audit_data["decision_id"],
        request_id=audit_data.get("request_id"),
        mandate_id=audit_data["mandate_id"],
        transaction_id=audit_data["transaction_id"],
        provider=audit_data.get("provider"),
        model=audit_data.get("model"),
        prompt_version=audit_data.get("prompt_version"),
        tool_calls=_json_dumps_safe(audit_data.get("tool_calls", [])),
        structural_result=_json_dumps_safe(audit_data.get("structural_result")),
        extracted_facts=_json_dumps_safe(audit_data.get("extracted_facts")),
        semantic_samples=_json_dumps_safe(audit_data.get("semantic_samples")),
        confidence_calculation=_json_dumps_safe(audit_data.get("confidence_calculation")),
        final_decision=audit_data.get("final_decision"),
        explanation=audit_data.get("explanation"),
        latency_ms=audit_data.get("latency_ms", 0),
        timestamp=audit_data.get("timestamp", datetime.utcnow()),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_audit_log(session: AsyncSession, decision_id: str) -> Optional[AuditLogRow]:
    """Fetch an audit log by decision ID."""
    from sqlalchemy import select
    result = await session.execute(
        select(AuditLogRow).where(AuditLogRow.decision_id == decision_id)
    )
    return result.scalar_one_or_none()


async def list_audit_logs(session: AsyncSession) -> List[AuditLogRow]:
    """List all audit logs."""
    from sqlalchemy import select
    result = await session.execute(select(AuditLogRow).order_by(AuditLogRow.timestamp.desc()))
    return list(result.scalars().all())


def audit_row_to_dict(row: AuditLogRow) -> dict:
    """Convert an AuditLogRow to a dictionary."""
    return {
        "id": row.id,
        "decision_id": row.decision_id,
        "request_id": row.request_id,
        "mandate_id": row.mandate_id,
        "transaction_id": row.transaction_id,
        "provider": row.provider,
        "model": row.model,
        "prompt_version": row.prompt_version,
        "tool_calls": _json_loads_safe(row.tool_calls) or [],
        "structural_result": _json_loads_safe(row.structural_result),
        "extracted_facts": _json_loads_safe(row.extracted_facts),
        "semantic_samples": _json_loads_safe(row.semantic_samples),
        "confidence_calculation": _json_loads_safe(row.confidence_calculation),
        "final_decision": row.final_decision,
        "explanation": row.explanation,
        "latency_ms": row.latency_ms,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
    }


# ── Evaluation CRUD ──────────────────────────────────────────

async def save_evaluation_report(session: AsyncSession, report_json: str) -> EvaluationRunRow:
    """Save an evaluation report."""
    row = EvaluationRunRow(
        id=str(uuid.uuid4()),
        report_json=report_json,
        created_at=datetime.utcnow(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_latest_evaluation(session: AsyncSession) -> Optional[EvaluationRunRow]:
    """Get the latest evaluation run."""
    from sqlalchemy import select
    result = await session.execute(
        select(EvaluationRunRow).order_by(EvaluationRunRow.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


# ── Agent Orchestrator CRUD ──────────────────────────────────

async def create_agent_run(
    session: AsyncSession,
    agent_id: str,
    agent_type: str,
    task_id: str,
    mandate_id: str,
    run_id: Optional[str] = None,
    max_retries: int = 3,
) -> AgentRunRow:
    """Create and record an agent run."""
    row = AgentRunRow(
        id=run_id or str(uuid.uuid4()),
        agent_id=agent_id,
        agent_type=agent_type,
        task_id=task_id,
        mandate_id=mandate_id,
        status="RUNNING",
        current_stage="INITIALIZING",
        attempt=1,
        max_retries=max_retries,
        tools_used="[]",
        started_at=datetime.utcnow(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_agent_run(
    session: AsyncSession,
    run_id: str,
    status: Optional[str] = None,
    current_stage: Optional[str] = None,
    attempt: Optional[int] = None,
    tools_used: Optional[List[str]] = None,
    proposal_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    latency_ms: Optional[float] = None,
    failure_reason: Optional[str] = None,
    observable_summary: Optional[Dict[str, Any]] = None,
) -> Optional[AgentRunRow]:
    """Update an existing agent run."""
    from sqlalchemy import select
    result = await session.execute(select(AgentRunRow).where(AgentRunRow.id == run_id))
    row = result.scalar_one_or_none()
    if not row:
        return None

    if status is not None:
        row.status = status
        if status in ("COMPLETED", "FAILED", "SAFE_STOPPED"):
            row.completed_at = datetime.utcnow()
    if current_stage is not None:
        row.current_stage = current_stage
    if attempt is not None:
        row.attempt = attempt
    if tools_used is not None:
        row.tools_used = json.dumps(tools_used)
    if proposal_id is not None:
        row.proposal_id = proposal_id
    if decision_id is not None:
        row.decision_id = decision_id
    if latency_ms is not None:
        row.latency_ms = latency_ms
    if failure_reason is not None:
        row.failure_reason = failure_reason
    if observable_summary is not None:
        row.observable_summary = json.dumps(observable_summary)

    await session.commit()
    await session.refresh(row)
    return row


async def get_agent_run(session: AsyncSession, run_id: str) -> Optional[AgentRunRow]:
    """Get an agent run by ID."""
    from sqlalchemy import select
    result = await session.execute(select(AgentRunRow).where(AgentRunRow.id == run_id))
    return result.scalar_one_or_none()


async def list_agent_runs(session: AsyncSession, limit: int = 50) -> List[AgentRunRow]:
    """List agent runs ordered by started_at desc."""
    from sqlalchemy import select
    result = await session.execute(
        select(AgentRunRow).order_by(AgentRunRow.started_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def create_agent_event(
    session: AsyncSession,
    run_id: str,
    agent_id: str,
    event_type: str,
    stage: str,
    payload: Dict[str, Any],
) -> AgentEventRow:
    """Create an agent lifecycle event record."""
    row = AgentEventRow(
        id=str(uuid.uuid4()),
        run_id=run_id,
        agent_id=agent_id,
        event_type=event_type,
        stage=stage,
        payload=json.dumps(payload),
        timestamp=datetime.utcnow(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_agent_events(session: AsyncSession, run_id: str) -> List[AgentEventRow]:
    """List events for a specific run."""
    from sqlalchemy import select
    result = await session.execute(
        select(AgentEventRow).where(AgentEventRow.run_id == run_id).order_by(AgentEventRow.timestamp.asc())
    )
    return list(result.scalars().all())


async def create_tool_call(
    session: AsyncSession,
    run_id: str,
    agent_id: str,
    tool_name: str,
    input_summary: Dict[str, Any],
    call_id: Optional[str] = None,
) -> ToolCallRow:
    """Record the initiation of a tool call."""
    row = ToolCallRow(
        id=call_id or str(uuid.uuid4()),
        run_id=run_id,
        agent_id=agent_id,
        tool_name=tool_name,
        input_summary=json.dumps(input_summary),
        status="STARTED",
        started_at=datetime.utcnow(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def update_tool_call(
    session: AsyncSession,
    call_id: str,
    status: str,
    result_summary: Optional[Dict[str, Any]] = None,
    latency_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> Optional[ToolCallRow]:
    """Update a tool call with its outcome."""
    from sqlalchemy import select
    result = await session.execute(select(ToolCallRow).where(ToolCallRow.id == call_id))
    row = result.scalar_one_or_none()
    if not row:
        return None

    row.status = status
    row.completed_at = datetime.utcnow()
    if result_summary is not None:
        row.result_summary = json.dumps(result_summary)
    if latency_ms is not None:
        row.latency_ms = latency_ms
    if error is not None:
        row.error = error

    await session.commit()
    await session.refresh(row)
    return row


async def list_tool_calls(session: AsyncSession, run_id: str) -> List[ToolCallRow]:
    """List tool calls for a run."""
    from sqlalchemy import select
    result = await session.execute(
        select(ToolCallRow).where(ToolCallRow.run_id == run_id).order_by(ToolCallRow.started_at.asc())
    )
    return list(result.scalars().all())


async def create_agent_recovery(
    session: AsyncSession,
    run_id: str,
    agent_id: str,
    failure_type: str,
    recovery_strategy: str,
    attempt: int = 1,
    max_attempts: int = 3,
    status: str = "IN_PROGRESS",
    details: Optional[Dict[str, Any]] = None,
) -> AgentRecoveryRow:
    """Record an agent recovery attempt."""
    row = AgentRecoveryRow(
        id=str(uuid.uuid4()),
        run_id=run_id,
        agent_id=agent_id,
        failure_type=failure_type,
        recovery_strategy=recovery_strategy,
        attempt=attempt,
        max_attempts=max_attempts,
        status=status,
        details=json.dumps(details or {}),
        timestamp=datetime.utcnow(),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_agent_recoveries(session: AsyncSession, run_id: str) -> List[AgentRecoveryRow]:
    """List recovery records for a run."""
    from sqlalchemy import select
    result = await session.execute(
        select(AgentRecoveryRow).where(AgentRecoveryRow.run_id == run_id).order_by(AgentRecoveryRow.timestamp.asc())
    )
    return list(result.scalars().all())

