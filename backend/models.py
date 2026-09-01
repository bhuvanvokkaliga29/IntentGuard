"""
IntentGuard — Data Models

Pydantic models for mandates, transactions, decisions, and audit logs.
SQLAlchemy ORM models for database tables.

CRITICAL: ground_truth_tier and ground_truth_reason exist ONLY on the
Transaction model for dataset/evaluation purposes. They are NEVER passed
to the agent runtime. Runtime schemas explicitly exclude these fields.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────

class FinalDecision(str, Enum):
    """
    Authorization outcomes.
    
    Primary states (used by decision engine):
      ALLOW    — Transaction approved
      BLOCK    — Transaction rejected
      ESCALATE — Insufficient evidence, routed to human review
    
    Deprecated:
      FLAG — Previously used for ambiguous/low-confidence cases.
             Retained for backward compatibility with existing audit data.
             Decision engine now emits ESCALATE for all review-needed cases.
    """
    ALLOW = "ALLOW"
    FLAG = "FLAG"  # Deprecated: retained for backward compat, no longer emitted
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class SemanticVerdict(str, Enum):
    FIT = "fit"
    NO_FIT = "no_fit"
    AMBIGUOUS = "ambiguous"


class GroundTruthTier(str, Enum):
    CLEARLY_IN_SCOPE = "clearly_in_scope"
    CLEARLY_OUT_OF_SCOPE = "clearly_out_of_scope"
    AMBIGUOUS = "ambiguous"
    UNSAFE_TO_DECIDE = "unsafe_to_decide"


# ── Mandate ──────────────────────────────────────────────────

class MandateBase(BaseModel):
    """Base mandate fields."""
    intent_text: str = Field(..., description="Natural language spending intent")
    max_amount_per_txn: float = Field(..., gt=0, description="Maximum amount per transaction")
    budget_cap: Optional[float] = Field(None, gt=0, description="Cumulative budget cap")
    allowed_categories: List[str] = Field(default_factory=list, description="Allowed merchant/item categories")
    allowed_merchants: Optional[List[str]] = Field(None, description="Allowed merchant names")
    frequency: str = Field(default="on_demand", description="Spending frequency: weekly, monthly, on_demand")
    exclusions: Optional[List[str]] = Field(None, description="Explicitly excluded items/categories")
    location_constraint: Optional[str] = Field(None, description="e.g., 'domestic' for travel mandates")
    purpose_context: Optional[str] = Field(None, description="Additional context about the mandate purpose")


class MandateCreate(MandateBase):
    """Schema for creating a new mandate."""
    pass


class Mandate(MandateBase):
    """Full mandate with ID and timestamp."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Transaction ──────────────────────────────────────────────

class TransactionBase(BaseModel):
    """Base transaction fields."""
    mandate_id: str = Field(..., description="Reference to the mandate this transaction is under")
    amount: float = Field(..., gt=0)
    merchant_name: str = Field(...)
    merchant_category: str = Field(...)
    item_description: str = Field(...)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction (runtime — no ground truth)."""
    pass


class Transaction(TransactionBase):
    """Full transaction including dataset-only ground truth fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ground_truth_tier: Optional[str] = Field(None, description="DATASET ONLY — never visible to agent")
    ground_truth_reason: Optional[str] = Field(None, description="DATASET ONLY — never visible to agent")


class TransactionRuntime(TransactionBase):
    """
    Transaction as seen by the agent at runtime.
    CRITICAL: This schema EXCLUDES ground_truth_tier and ground_truth_reason.
    The agent must NEVER see ground truth labels.
    """
    id: str

    @field_validator("*", mode="before")
    @classmethod
    def reject_ground_truth(cls, v: Any, info: Any) -> Any:
        """Ensure no ground truth fields leak into runtime payload."""
        if info.field_name in ("ground_truth_tier", "ground_truth_reason"):
            raise ValueError(f"SECURITY: {info.field_name} must never be in agent runtime payload")
        return v


# ── Structural Check Result ──────────────────────────────────

class ConstraintCheck(BaseModel):
    """Result of a single hard constraint check."""
    constraint_name: str
    passed: bool
    detail: str
    value_checked: Optional[str] = None
    limit: Optional[str] = None


class StructuralResult(BaseModel):
    """Aggregate result of all hard constraint checks."""
    overall_pass: bool
    checks: List[ConstraintCheck]
    failure_reasons: List[str] = Field(default_factory=list)


# ── Extracted Facts (LLM Call 1 output) ──────────────────────

class ExtractedFacts(BaseModel):
    """Structured facts extracted from transaction by LLM."""
    normalized_category: str = Field(..., description="Normalized item category")
    item_type: str = Field(..., description="Type of item being purchased")
    domestic_or_international: Optional[str] = Field(None, description="'domestic', 'international', or null")
    brand_tier: Optional[str] = Field(None, description="'budget', 'standard', 'premium', 'luxury', or null")
    quantity: Optional[int] = Field(None, description="Number of items if inferable")
    specific_product: Optional[str] = Field(None, description="Specific product name if identifiable")
    confidence_notes: Optional[str] = Field(None, description="Notes about extraction confidence")


# ── Semantic Judgment (LLM Call 2 output) ─────────────────────

class SemanticJudgmentSample(BaseModel):
    """Single semantic judgment sample."""
    verdict: SemanticVerdict
    rationale: str = Field(..., description="Evidence-grounded rationale for the verdict")


class SemanticJudgmentResult(BaseModel):
    """Aggregated semantic judgment from self-consistency sampling."""
    samples: List[SemanticJudgmentSample]
    majority_verdict: SemanticVerdict
    agreement_rate: float = Field(..., ge=0.0, le=1.0)
    combined_rationale: str


# ── Decision ─────────────────────────────────────────────────

class DecisionBase(BaseModel):
    """Core decision fields."""
    transaction_id: str
    structural_check_result: Dict[str, Any]
    extracted_facts: Optional[Dict[str, Any]] = None
    semantic_judgment: Optional[Dict[str, Any]] = None
    confidence_score: float
    final_decision: FinalDecision
    explanation: str
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    latency_ms: int = 0


class Decision(DecisionBase):
    """Full decision with ID and timestamp."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mandate_id: str = ""
    audit_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Audit Log ────────────────────────────────────────────────

class ToolCallRecord(BaseModel):
    """Record of a single tool call during evaluation."""
    tool_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(BaseModel):
    """Complete audit trail for a decision."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str
    request_id: Optional[str] = None
    mandate_id: str
    transaction_id: str
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    structural_result: Optional[Dict[str, Any]] = None
    extracted_facts: Optional[Dict[str, Any]] = None
    semantic_samples: Optional[List[Dict[str, Any]]] = None
    confidence_calculation: Optional[Dict[str, Any]] = None
    final_decision: Optional[str] = None
    explanation: Optional[str] = None
    latency_ms: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── API Response ─────────────────────────────────────────────

class DecisionResponse(BaseModel):
    """API response for a decision evaluation."""
    decision_id: str
    mandate_id: str
    transaction_id: str
    provider: Optional[str] = None
    model: Optional[str] = None
    structural_result: Dict[str, Any]
    extracted_facts: Optional[Dict[str, Any]] = None
    semantic_judgment: Optional[Dict[str, Any]] = None
    confidence: float
    final_decision: str
    explanation: str
    latency_ms: int
    audit_id: str


# ── Evaluation ───────────────────────────────────────────────

class EvaluationMetrics(BaseModel):
    """Metrics for a single evaluation run."""
    baseline_name: str
    total_cases: int
    accuracy: float
    precision_per_class: Dict[str, float]
    recall_per_class: Dict[str, float]
    f1_per_class: Dict[str, float]
    confusion_matrix: Dict[str, Dict[str, int]]
    false_allow_rate: float
    false_block_rate: float
    escalation_accuracy: float
    mean_latency_ms: float
    total_llm_calls: int
    estimated_cost_usd: Optional[float] = None


class EvaluationReport(BaseModel):
    """Complete evaluation report comparing baselines."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dataset_size: int
    baselines: List[EvaluationMetrics]
    summary: str
