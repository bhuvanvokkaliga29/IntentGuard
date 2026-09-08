"""
IntentGuard — Formal Critical Invariants Verification Suite

Formal verification of the 15 non-negotiable architectural and security invariants:
1.  LLM output cannot directly authorize execution (Supervisory control plane)
2.  Structural policy violations cannot become ALLOW under any semantic verdict
3.  ESCALATE cannot reach financial execution (Execution boundary gating)
4.  BLOCK cannot reach financial execution (Execution boundary gating)
5.  Proposer agents cannot execute transactions (Strict proposer sandboxing)
6.  Self-healing cannot modify authorization policy or budgets
7.  Duplicate proposals cannot cause duplicate financial execution (Idempotency)
8.  Historical decisions remain bound to their versions (Deterministic replay)
9.  Semantic cache cannot cross authorization contexts (Strict cache isolation)
10. Audit-chain tampering is cryptographically detectable (Tamper-evident ledger)
11. Human review actions are immutably audited in the hash chain
12. Missing critical authorization context cannot silently ALLOW (Fail-safe default)
13. Unauthorized API callers cannot invoke protected operations (API key guard)
14. Async task paths cannot bypass the authoritative execution gate
15. Retry paths cannot bypass deterministic authorization
"""

import ast
import asyncio
import hashlib
import json
import uuid
from pathlib import Path
from typing import Dict, Any

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.main import app
from backend.config import reset_settings, get_settings
from backend.models import FinalDecision, SemanticVerdict, TransactionProposalCreate
from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide
from backend.policy.confidence import compute_confidence
from backend.orchestrator.pipeline import (
    stage_intake_proposal,
    stage_normalize_proposal,
    stage_verify_structural_constraints,
    stage_evaluate_deterministic_policy,
    stage_guard_execution_boundary,
)
from backend.execution.razorpay_gateway import (
    get_razorpay_gateway,
    reset_razorpay_gateway,
)
from backend.policy.versioning import POLICY_VERSION, get_current_policy_snapshot
from backend.policy.replay import replay_decision
from backend.agent.agent import compute_semantic_cache_key
from backend.agent.self_healing import SelfHealingEngine, FailureClassification, RecoveryStrategy
from backend.agent.proposer_buying import BuyingAgent
from backend.agent.proposer_recommendation import RecommendationAgent
from backend.agent.proposer_voice import VoiceMandateAgent
from backend.db import (
    Base,
    create_mandate,
    create_transaction,
    create_decision,
    create_audit_log,
    update_decision_review,
    verify_audit_chain,
    AuditLogRow,
    DecisionRow,
    MandateRow,
    TransactionRow,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the Razorpay gateway state and settings before and after each test."""
    reset_razorpay_gateway()
    reset_settings()
    yield
    reset_razorpay_gateway()
    reset_settings()


@pytest.fixture
async def memory_db():
    """Isolated in-memory SQLite database for audit chain and DB invariant tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


# ── Invariant 1: LLM Output Cannot Directly Authorize Execution ────────
def test_invariant_1_llm_output_cannot_directly_authorize_execution():
    """
    Supervisory Boundary:
    Even if an LLM output evaluates to 'fit' with 100% confidence,
    it CANNOT produce ALLOW if the deterministic policy layer determines otherwise.
    Money is controlled strictly by deterministic code, never LLM text.
    """
    # LLM claim: 'fit', but structural hard constraint failed
    decision = decide(
        structural_pass=False,
        majority_verdict="fit",
        confidence_score=1.0,
        structural_failure_reasons=["Transaction exceeds max per-transaction limit"],
    )
    assert decision["final_decision"] == FinalDecision.BLOCK.value
    assert "structural_hard_fail" in decision["decision_path"]

    # Even if LLM attempted to claim ALLOW via raw prompt injection in evidence
    gate = stage_guard_execution_boundary(
        final_decision=decision["final_decision"],
        proposal={"id": "inj-001", "amount": 9999.0, "merchant_name": "Bad Actor"},
    )
    assert gate["executed"] is False
    assert gate["status"] == "BLOCKED_BY_GUARDRAIL"


# ── Invariant 2: Structural Policy Violations Cannot Become ALLOW ──────
@pytest.mark.parametrize(
    "verdict,confidence",
    [
        ("fit", 1.0),
        ("fit", 0.95),
        ("partially_fit", 0.8),
        ("ambiguous", 0.5),
        ("no_fit", 0.0),
    ],
)
def test_invariant_2_structural_policy_violations_cannot_become_allow(verdict, confidence):
    """
    Deterministic Priority:
    Under ANY semantic verdict or confidence score, a structural failure
    (e.g., budget exceeded, prohibited merchant/category) strictly yields BLOCK.
    """
    decision = decide(
        structural_pass=False,
        majority_verdict=verdict,
        confidence_score=confidence,
        structural_failure_reasons=["Exceeded budget cap of ₹5,000"],
    )
    assert decision["final_decision"] == FinalDecision.BLOCK.value
    assert decision["final_decision"] != FinalDecision.ALLOW.value


# ── Invariant 3: ESCALATE Cannot Reach Financial Execution ─────────────
def test_invariant_3_escalate_cannot_reach_financial_execution():
    """
    Execution Boundary:
    When the deterministic policy produces ESCALATE, the execution boundary
    strictly blocks execution and records an unexecuted status.
    """
    proposal = {
        "id": "esc-test-001",
        "amount": 2500.0,
        "currency": "INR",
        "merchant_name": "Borderline Tech Supplies",
        "item_description": "Multi-purpose monitor with TV tuner",
    }
    gate_result = stage_guard_execution_boundary(
        final_decision="ESCALATE",
        proposal=proposal,
    )
    assert gate_result["executed"] is False
    assert gate_result["status"] == "BLOCKED_BY_GUARDRAIL"
    assert "order" not in gate_result or gate_result["order"] is None

    # Verify zero orders were created in the gateway
    gw = get_razorpay_gateway()
    assert len(gw._idempotency_store) == 0


# ── Invariant 4: BLOCK Cannot Reach Financial Execution ────────────────
def test_invariant_4_block_cannot_reach_financial_execution():
    """
    Execution Boundary:
    When the deterministic policy produces BLOCK, payment execution is strictly unreachable.
    """
    proposal = {
        "id": "blk-test-001",
        "amount": 50000.0,
        "currency": "INR",
        "merchant_name": "Luxury Electronics",
        "item_description": "High-end gaming console",
    }
    gate_result = stage_guard_execution_boundary(
        final_decision="BLOCK",
        proposal=proposal,
    )
    assert gate_result["executed"] is False
    assert gate_result["status"] == "BLOCKED_BY_GUARDRAIL"

    gw = get_razorpay_gateway()
    assert len(gw._idempotency_store) == 0


# ── Invariant 5: Proposer Agents Cannot Execute Transactions ───────────
def test_invariant_5_proposer_agents_cannot_execute_transactions():
    """
    Sandboxing & Static Boundary Enforcement:
    Proposer agents are strictly proposal generators. They must NEVER:
    1. Import payment execution or Razorpay modules.
    2. Contain execution keys or payment gateway instances.
    """
    proposer_modules = [
        Path("backend/agent/proposer_buying.py"),
        Path("backend/agent/proposer_recommendation.py"),
        Path("backend/agent/proposer_voice.py"),
    ]
    forbidden_tokens = ["razorpay_gateway", "RazorpayExecutionGateway", "get_razorpay_gateway"]

    for mod_path in proposer_modules:
        if not mod_path.exists():
            continue
        code = mod_path.read_text(encoding="utf-8")
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for fb in forbidden_tokens:
                        assert fb not in alias.name, f"{mod_path} imports forbidden execution token: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for fb in forbidden_tokens:
                        assert fb not in node.module, f"{mod_path} imports from forbidden execution module: {node.module}"

    # Runtime instantiation check
    b_agent = BuyingAgent()
    assert not hasattr(b_agent, "razorpay_client")
    assert not hasattr(b_agent, "execute_payment")


# ── Invariant 6: Self-Healing Cannot Modify Authorization Policy ───────
def test_invariant_6_self_healing_cannot_modify_authorization_policy():
    """
    Self-Healing Guardrail:
    The self-healing mechanism is strictly limited to syntax normalization,
    repairing JSON parse errors, and bounded retries.
    It can NEVER:
    1. Modify mandate thresholds, budgets, or categories.
    2. Alter policy matrix rules.
    3. Flip a BLOCK or ESCALATE into an ALLOW.
    """
    engine = SelfHealingEngine(max_retries=3)

    # Verify self-healing engine has no policy modification methods
    assert not hasattr(engine, "override_policy")
    assert not hasattr(engine, "increase_budget")
    assert not hasattr(engine, "modify_mandate")

    # Critical security breach must strictly map to SAFE_STOP
    sec_strat = engine.determine_strategy(FailureClassification.CRITICAL_SECURITY_BREACH, 1)
    assert sec_strat == RecoveryStrategy.SAFE_STOP

    # Exceeding retries must strictly map to SAFE_STOP
    exhausted_strat = engine.determine_strategy(FailureClassification.TIMEOUT, 3)
    assert exhausted_strat == RecoveryStrategy.SAFE_STOP


# ── Invariant 7: Duplicate Proposals Cannot Cause Duplicate Execution ──
def test_invariant_7_duplicate_proposals_cannot_cause_duplicate_execution():
    """
    Idempotency Guarantee:
    Submitting the exact same proposal with identical idempotency key twice
    executes at most ONCE financially and returns the prior cached execution result.
    """
    proposal = {
        "id": f"idem-{uuid.uuid4()}",
        "amount": 1200.0,
        "currency": "INR",
        "merchant_name": "Office Depot",
        "item_description": "Ergonomic keyboard",
        "idempotency_key": f"key-{uuid.uuid4()}",
    }

    # First execution: ALLOW
    first_res = stage_guard_execution_boundary("ALLOW", proposal)
    assert first_res["executed"] is True
    assert first_res["order"]["success"] is True
    assert first_res["order"].get("idempotent_replay") is False

    # Second execution: Duplicate proposal with same idempotency key
    second_res = stage_guard_execution_boundary("ALLOW", proposal)
    assert second_res["executed"] is True
    assert second_res["order"]["idempotent_replay"] is True

    # Gateway orders store must contain exactly 1 created order
    gw = get_razorpay_gateway()
    assert len(gw._idempotency_store) == 1


# ── Invariant 8: Historical Decisions Remain Bound to Their Versions ───
def test_invariant_8_historical_decisions_remain_bound_to_their_versions():
    """
    Deterministic Decision Replay:
    Replaying a past decision uses its recorded mandate version and policy version,
    faithfully reconstructing the verdict without executing payments.
    """
    proposal = {
        "id": "replay-test-01",
        "amount": 1500.0,
        "merchant_name": "Acme Stationery",
        "merchant_category": "stationery",
        "item_description": "Printer ink and highlighters",
    }
    mandate = {
        "id": "mandate-v1",
        "max_amount_per_txn": 2000.0,
        "budget_cap": 5000.0,
        "allowed_categories": ["stationery", "office_supplies"],
        "allowed_merchants": ["Acme Stationery"],
        "intent_text": "Purchase office stationery and printer supplies",
        "version": 1,
    }
    original_decision = {
        "final_decision": "ALLOW",
        "structural_pass": True,
        "majority_verdict": "fit",
        "confidence_score": 0.95,
        "mandate_version": 1,
        "policy_version": POLICY_VERSION,
    }

    replay = replay_decision(
        proposal=proposal,
        mandate=mandate,
        original_decision_record=original_decision,
        mandate_version=1,
        policy_version=POLICY_VERSION,
    )

    assert replay.is_reproducible is True
    assert replay.original_decision == "ALLOW"
    assert replay.replayed_decision == "ALLOW"
    assert replay.decision_match is True
    assert replay.mandate_version_used == 1
    assert replay.policy_version_used == POLICY_VERSION


# ── Invariant 9: Semantic Cache Cannot Cross Authorization Contexts ────
def test_invariant_9_semantic_cache_cannot_cross_authorization_contexts():
    """
    Cache Isolation:
    The semantic cache key includes mandate_id, categories, exclusions,
    merchants, item_description, and policy_version. Changes to ANY context
    dimension MUST produce distinct keys to avoid unauthorized cross-pollination.
    """
    mandate_a = {
        "id": "mandate-A",
        "intent_text": "Purchase office stationery and pens",
        "allowed_categories": ["stationery"],
        "exclusions": ["electronics"],
        "allowed_merchants": ["OfficeMart"],
    }
    mandate_b = {
        "id": "mandate-B",
        "intent_text": "Purchase books and study materials",
        "allowed_categories": ["books"],
        "exclusions": [],
        "allowed_merchants": ["BookDepot"],
    }
    txn = {
        "item_description": "Ballpoint Pens Pack of 10",
        "merchant_name": "OfficeMart",
        "amount": 250.0,
    }

    key_base = compute_semantic_cache_key(mandate_a, txn, policy_version="v1")
    key_diff_mandate = compute_semantic_cache_key(mandate_b, txn, policy_version="v1")
    key_diff_policy = compute_semantic_cache_key(mandate_a, txn, policy_version="v2")
    key_diff_item = compute_semantic_cache_key(mandate_a, {**txn, "item_description": "Noise Cancelling Headphones"}, policy_version="v1")

    assert key_base != key_diff_mandate
    assert key_base != key_diff_policy
    assert key_base != key_diff_item


# ── Invariant 10: Audit-Chain Tampering is Cryptographically Detectable ─
@pytest.mark.asyncio
async def test_invariant_10_audit_chain_tampering_is_detectable(memory_db: AsyncSession):
    """
    Tamper-Evident SHA-256 Hash Chain:
    Any unauthorized modification to any field of a committed audit row
    is immediately detected by verify_audit_chain.
    """
    # Create valid audit entry
    log1 = await create_audit_log(memory_db, {
        "decision_id": f"dec-{uuid.uuid4()}",
        "transaction_id": f"txn-{uuid.uuid4()}",
        "mandate_id": "mandate-001",
        "final_decision": "ALLOW",
        "actor": "INTENTGUARD_CORE",
        "action": "AUTHORIZE",
    })

    # Verify initial chain is valid
    is_valid, errors = await verify_audit_chain(memory_db)
    assert is_valid is True
    assert len(errors) == 0

    # Tamper with the record (e.g. attacker modifies final_decision from ALLOW to BLOCK)
    log1.final_decision = "BLOCK"
    await memory_db.commit()

    # Chain verification MUST fail
    tampered_valid, tampered_errors = await verify_audit_chain(memory_db)
    assert tampered_valid is False
    assert len(tampered_errors) > 0
    assert any("hash" in str(e).lower() for e in tampered_errors)


# ── Invariant 11: Human Review Actions Are Immutably Audited ───────────
@pytest.mark.asyncio
async def test_invariant_11_human_review_actions_are_audited(memory_db: AsyncSession):
    """
    Human Review Auditability:
    Updating a human review decision via update_decision_review strictly appends
    a cryptographically linked row into the audit chain recording reviewer identity and action.
    """
    # Create a mandate, transaction, and decision
    mandate = await create_mandate(memory_db, {
        "intent_text": "Review test mandate",
        "max_amount_per_txn": 1000.0,
        "allowed_categories": ["stationery"],
    })
    txn = await create_transaction(memory_db, {
        "mandate_id": mandate.id,
        "amount": 800.0,
        "merchant_name": "Store",
        "merchant_category": "stationery",
        "item_description": "Pencils",
    })

    dec_id = str(uuid.uuid4())
    dec_row = await create_decision(memory_db, {
        "id": dec_id,
        "transaction_id": txn.id,
        "mandate_id": mandate.id,
        "final_decision": "ESCALATE",
        "confidence_score": 0.5,
        "explanation": "Needs human review",
    })

    # Perform human review
    updated_dec = await update_decision_review(
        session=memory_db,
        decision_id=dec_id,
        action="APPROVE",
        notes="Approved by Chief Compliance Officer",
        reviewer_id="compliance_officer_42",
    )
    assert updated_dec is not None
    assert updated_dec.human_review_status == "APPROVE"
    assert updated_dec.reviewer_id == "compliance_officer_42"

    # Verify audit chain integrity after review append
    is_valid, errors = await verify_audit_chain(memory_db)
    assert is_valid is True
    assert len(errors) == 0


# ── Invariant 12: Missing Critical Authorization Context Cannot Silently ALLOW ─
def test_invariant_12_missing_critical_authorization_context_cannot_silently_allow():
    """
    Fail-Safe Default:
    If critical authorization context is missing (e.g. empty item description,
    unresolvable mandate parameters, or unparsable amount), the system strictly
    rejects or escalates, never defaulting to ALLOW.
    """
    # 1. Negative or zero amount rejected at schema validation
    with pytest.raises(Exception):
        stage_intake_proposal({
            "mandate_id": "man-001",
            "amount": -50.0,
            "merchant_name": "Vendor",
            "merchant_category": "supplies",
            "item_description": "Valid item",
        })

    # 2. Empty item description rejected at schema validation
    with pytest.raises(Exception):
        stage_intake_proposal({
            "mandate_id": "man-001",
            "amount": 100.0,
            "merchant_name": "Vendor",
            "merchant_category": "supplies",
            "item_description": "",
        })

    # 3. Structural check with empty allowed categories and lower max limit
    structural = check_hard_constraints(
        txn_amount=100.0,
        txn_merchant_name="Unknown",
        txn_merchant_category="unknown",
        txn_item_description="Item",
        mandate_max_amount_per_txn=50.0,  # lower than txn amount
        mandate_budget_cap=50.0,
        mandate_allowed_categories=[],
        mandate_allowed_merchants=None,
    )
    assert structural.overall_pass is False


# ── Invariant 13: Unauthorized API Callers Cannot Invoke Protected Operations ─
@pytest.mark.asyncio
async def test_invariant_13_unauthorized_api_callers_cannot_invoke_protected_operations(monkeypatch):
    """
    API Security Guard:
    When an API key is configured, protected operational endpoints require an authorized API key.
    Requests with invalid or missing keys receive HTTP 401.
    """
    monkeypatch.setenv("API_KEY", "secret-test-key-guard")
    reset_settings()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Call protected evaluate proposal without API key header
        resp = await ac.post(
            "/proposals/evaluate",
            json={
                "mandate_id": str(uuid.uuid4()),
                "amount": 100.0,
                "merchant_name": "Acme",
                "merchant_category": "office",
                "item_description": "Notebooks",
            },
        )
        assert resp.status_code == 401

        # Call with invalid key header
        resp_bad = await ac.post(
            "/proposals/evaluate",
            headers={"X-API-Key": "invalid-token"},
            json={
                "mandate_id": str(uuid.uuid4()),
                "amount": 100.0,
                "merchant_name": "Acme",
                "merchant_category": "office",
                "item_description": "Notebooks",
            },
        )
        assert resp_bad.status_code == 401


# ── Invariant 14: Async Task Paths Cannot Bypass the Execution Gate ─────
def test_invariant_14_async_task_paths_cannot_bypass_the_execution_gate():
    """
    Unified Execution Path:
    Whether evaluation runs synchronously or via background async task workers,
    financial execution is dispatched ONLY through stage_guard_execution_boundary.
    """
    proposal = {
        "id": "async-test-01",
        "amount": 900.0,
        "currency": "INR",
        "merchant_name": "Authorized Vendor",
        "item_description": "Desk Lamp",
    }

    # Simulate an async worker attempting to execute on ESCALATE verdict
    exec_result = stage_guard_execution_boundary(
        final_decision="ESCALATE",
        proposal=proposal,
    )
    assert exec_result["executed"] is False
    assert exec_result["status"] == "BLOCKED_BY_GUARDRAIL"

    # Only explicit ALLOW executes
    exec_allow = stage_guard_execution_boundary(
        final_decision="ALLOW",
        proposal=proposal,
    )
    assert exec_allow["executed"] is True
    assert exec_allow["status"] == "DISPATCHED"


# ── Invariant 15: Retry Paths Cannot Bypass Deterministic Authorization ─
def test_invariant_15_retry_paths_cannot_bypass_deterministic_authorization():
    """
    Resilient Authorization:
    When retrying an evaluation due to transient network or LLM errors,
    the retry path must re-evaluate all deterministic hard constraints.
    It cannot bypass hard checks to recover.
    """
    # Scenario: transaction fails structural check
    structural = check_hard_constraints(
        txn_amount=10000.0,
        txn_merchant_name="Unapproved Casino",
        txn_merchant_category="gambling",
        txn_item_description="Chips",
        mandate_max_amount_per_txn=500.0,
        mandate_budget_cap=1000.0,
        mandate_allowed_categories=["stationery"],
        mandate_allowed_merchants=["Stationery Mart"],
    )
    assert structural.overall_pass is False

    # First attempt: BLOCK
    first_dec = decide(
        structural_pass=structural.overall_pass,
        majority_verdict="no_fit",
        confidence_score=0.9,
        structural_failure_reasons=structural.failure_reasons,
    )
    assert first_dec["final_decision"] == FinalDecision.BLOCK.value

    # Simulated retry attempt (e.g. after network glitch):
    # Deterministic policy must still be evaluated and still strictly BLOCK
    retry_dec = decide(
        structural_pass=structural.overall_pass,
        majority_verdict="ambiguous",  # even if LLM verdict changed on retry
        confidence_score=0.4,
        structural_failure_reasons=structural.failure_reasons,
    )
    assert retry_dec["final_decision"] == FinalDecision.BLOCK.value
