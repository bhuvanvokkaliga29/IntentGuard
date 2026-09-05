"""
IntentGuard — Hardened Architectural Invariants Test Suite

Verifies the 8 core non-negotiable architectural invariants:
1. LLM output cannot directly authorize financial execution (Supervisory boundary)
2. Structural hard constraints cannot be overridden by semantic fit (Deterministic priority)
3. Ambiguous semantic verification fails safe to ESCALATE (Fail-safe defaults)
4. Provider failure or timeout fails safe to ESCALATE (Resilience & containment)
5. Proposer agents cannot bypass IntentGuard (Controlled delegation boundary)
6. Mandate/policy mutation strictly invalidates semantic cache (Context-complete cache key)
7. Execution idempotency prevents double spend / duplicate settlement (Idempotent execution)
8. Audit chain is observable, sequential, and cryptographically SHA-256 hash-chained
"""

import asyncio
import pytest
import uuid
from typing import Dict, Any

from backend.agent.agent import compute_semantic_cache_key
from backend.db import (
    get_session,
    init_db,
    create_mandate,
    create_transaction,
    create_audit_log,
    verify_audit_chain,
    AuditLogRow,
)
from backend.execution.razorpay_gateway import get_razorpay_gateway, reset_razorpay_gateway
from backend.llm.provider import MockProvider, LLMProvider
from backend.models import TransactionProposalCreate
from backend.orchestrator.pipeline import (
    stage_intake_proposal,
    stage_normalize_proposal,
    stage_verify_structural_constraints,
    stage_evaluate_deterministic_policy,
    stage_guard_execution_boundary,
)
from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide
from backend.security.prompt_defense import (
    evaluate_prompt_defense,
    scan_for_prompt_injection,
    normalize_untrusted_text,
    encapsulate_untrusted_input,
)


@pytest.fixture(autouse=True)
def clean_gateway():
    reset_razorpay_gateway()
    yield
    reset_razorpay_gateway()


# ── Invariant 1: LLM Cannot Directly Authorize Execution ─────
def test_invariant_1_llm_cannot_directly_authorize_execution():
    """
    Even if an LLM output evaluates to 'fit' or claims authorization,
    if structural checks fail, deterministic policy produces BLOCK,
    and the execution boundary strictly forbids payment dispatch.
    """
    # 1. Structural failure: ₹15,000 exceeds ₹2,000 limit
    proposal = {
        "amount": 15000.0,
        "currency": "INR",
        "merchant_name": "Stationery Mart",
        "merchant_category": "stationery",
        "item_description": "printer paper",
        "idempotency_key": "inv1_test_key",
    }
    mandate = {
        "max_amount_per_txn": 2000.0,
        "budget_cap": 20000.0,
        "allowed_categories": ["stationery"],
        "allowed_merchants": ["Stationery Mart"],
    }

    structural = stage_verify_structural_constraints(proposal, mandate)
    assert structural.overall_pass is False

    # 2. LLM verdict 'fit' cannot override structural failure
    decision = stage_evaluate_deterministic_policy(
        structural_result=structural,
        semantic_verdict="fit",  # LLM enthusiastically approved
        confidence_score=0.99,
    )
    assert decision["final_decision"] == "BLOCK"
    assert "structural_hard_constraint_failure" in decision["decision_path"]

    # 3. Execution boundary strictly blocks financial settlement
    exec_result = stage_guard_execution_boundary(decision["final_decision"], proposal)
    assert exec_result["executed"] is False
    assert exec_result["status"] == "BLOCKED_BY_GUARDRAIL"
    assert exec_result["order"] is None


# ── Invariant 2: Structural Hard Constraints Cannot Be Overridden ─
def test_invariant_2_structural_hard_constraints_cannot_be_overridden():
    """
    Fast-path priority: Hard constraints are evaluated deterministically.
    Disallowed merchant or category breaches must reject regardless of semantic fit.
    """
    mandate = {
        "max_amount_per_txn": 5000.0,
        "budget_cap": 20000.0,
        "allowed_categories": ["office_supplies"],
        "allowed_merchants": ["Approved Vendor A"],
    }

    # Case A: Disallowed merchant
    prop_bad_merchant = {
        "amount": 1200.0,
        "merchant_name": "Unapproved Rogue Store",
        "merchant_category": "office_supplies",
        "item_description": "standard office paper",
    }
    res_merchant = stage_verify_structural_constraints(prop_bad_merchant, mandate)
    assert res_merchant.overall_pass is False
    assert any("allowed_merchants" in c.constraint_name for c in res_merchant.checks if not c.passed)

    # Case B: Disallowed category
    prop_bad_cat = {
        "amount": 1200.0,
        "merchant_name": "Approved Vendor A",
        "merchant_category": "gambling_entertainment",
        "item_description": "standard office paper",
    }
    res_cat = stage_verify_structural_constraints(prop_bad_cat, mandate)
    assert res_cat.overall_pass is False
    assert any("allowed_categories" in c.constraint_name for c in res_cat.checks if not c.passed)


# ── Invariant 3: Ambiguous Semantic Verification Fails Safe to ESCALATE ─
def test_invariant_3_ambiguous_semantic_fails_safe_to_escalate():
    """
    Whenever semantic verification produces 'ambiguous' or low confidence,
    the deterministic policy engine strictly outputs ESCALATE (never ALLOW).
    """
    # 1. Ambiguous verdict with borderline confidence
    decision_ambiguous = decide(
        structural_pass=True,
        majority_verdict="ambiguous",
        confidence_score=0.85,
        evidence_is_sufficient=True,
    )
    assert decision_ambiguous["final_decision"] == "ESCALATE"

    # 2. 'Fit' verdict but confidence BELOW threshold (0.65 < 0.75)
    decision_low_conf = decide(
        structural_pass=True,
        majority_verdict="fit",
        confidence_score=0.65,
        evidence_is_sufficient=True,
    )
    assert decision_low_conf["final_decision"] == "ESCALATE"

    # 3. Insufficient evidence
    decision_insufficient = decide(
        structural_pass=True,
        majority_verdict="fit",
        confidence_score=0.95,
        evidence_is_sufficient=False,
    )
    assert decision_insufficient["final_decision"] == "ESCALATE"


# ── Invariant 4: Provider Failure Fails Safe to ESCALATE ──────
@pytest.mark.asyncio
async def test_invariant_4_provider_failure_fails_safe_to_escalate():
    """
    If the LLM provider fails (raises Exception, times out, or returns None),
    IntentGuard catches the error and safely escalates to human review.
    """
    class CrashingProvider(LLMProvider):
        @property
        def provider_name(self) -> str:
            return "crashing_mock"

        @property
        def model_name(self) -> str:
            return "crash-v1"

        async def structured_extract(self, prompt: str, system_instruction: str = ""):
            raise ConnectionError("Upstream LLM cluster unreachable / 503 Overloaded")

        async def semantic_judge(self, prompt: str, system_instruction: str = ""):
            raise ConnectionError("Upstream LLM cluster unreachable / 503 Overloaded")

        async def generate_explanation(self, prompt: str, system_instruction: str = ""):
            raise ConnectionError("Upstream LLM cluster unreachable / 503 Overloaded")

    from backend.agent.agent import _run_evaluation_pipeline_internal
    from backend.db import get_session, create_mandate, create_transaction

    await init_db()
    session_maker = await get_session()
    async with session_maker as session:
        mandate_row = await create_mandate(session, {
            "id": str(uuid.uuid4()),
            "intent_text": "Emergency supplies",
            "max_amount_per_txn": 1000.0,
            "allowed_categories": ["general"],
        })
        txn_row = await create_transaction(session, {
            "id": str(uuid.uuid4()),
            "mandate_id": mandate_row.id,
            "amount": 500.0,
            "merchant_name": "General Store",
            "merchant_category": "general",
            "item_description": "first aid kit",
        })

        result = await _run_evaluation_pipeline_internal(
            session=session,
            provider=CrashingProvider(),
            transaction_id=txn_row.id,
            mandate_id=mandate_row.id,
        )

        assert result["final_decision"] == "ESCALATE"
        assert "ESCALATE" in result["decision_path"]


# ── Invariant 5: Proposer Agents Cannot Bypass IntentGuard ───
def test_invariant_5_proposer_agents_cannot_bypass_intentguard():
    """
    Proposals from autonomous proposer agents (BuyingAgent, RecommendationAgent)
    are unexecuted proposals. They must undergo IntentGuard intake and validation.
    """
    from backend.agent.proposer_buying import BuyingAgent, BuyingObjective

    agent = BuyingAgent()
    mandate = {
        "id": "mandate_office_test",
        "intent_text": "Purchase standard office supplies",
        "max_amount_per_txn": 2000.0,
        "allowed_categories": ["stationery", "office_supplies"],
        "allowed_merchants": ["Stationery Mart"],
    }

    # Proposer generates candidate
    proposal = agent.generate_proposal(mandate, objective=BuyingObjective.BEST_RATING)
    assert hasattr(proposal, "amount")
    assert hasattr(proposal, "item_description")

    # Proposer cannot execute directly: must be evaluated through pipeline
    proposal_dict = proposal.model_dump()
    intake = stage_intake_proposal(proposal_dict)
    assert intake["currency"] == "INR"
    assert intake["amount"] > 0

    # Ensure execution cannot occur without an explicit ALLOW decision
    exec_res = stage_guard_execution_boundary("BLOCK", intake)
    assert exec_res["executed"] is False


# ── Invariant 6: Mandate Mutation Invalidates Semantic Cache ──
def test_invariant_6_mandate_mutation_invalidates_semantic_cache():
    """
    A cached verdict will NEVER survive changes to mandate policies,
    exclusions, allowed merchants, categories, or policy versions.
    """
    base_mandate = {
        "id": "mandate_cache_test",
        "intent_text": "Procure office paper and notebooks",
        "allowed_categories": ["office_supplies"],
        "exclusions": [],
        "allowed_merchants": ["Stationery Mart"],
    }
    transaction = {
        "merchant_name": "Stationery Mart",
        "item_description": "Printer Paper Box",
    }

    key_base = compute_semantic_cache_key(base_mandate, transaction, "v1")

    # Mutation A: Adding an exclusion invalidates cache
    mandate_with_exclusion = dict(base_mandate)
    mandate_with_exclusion["exclusions"] = ["bulk_orders"]
    key_mut_exclusion = compute_semantic_cache_key(mandate_with_exclusion, transaction, "v1")
    assert key_base != key_mut_exclusion

    # Mutation B: Modifying allowed merchants invalidates cache
    mandate_with_merchants = dict(base_mandate)
    mandate_with_merchants["allowed_merchants"] = ["Stationery Mart", "Office Max"]
    key_mut_merchants = compute_semantic_cache_key(mandate_with_merchants, transaction, "v1")
    assert key_base != key_mut_merchants

    # Mutation C: Policy engine version upgrade invalidates cache
    key_v2 = compute_semantic_cache_key(base_mandate, transaction, "v2")
    assert key_base != key_v2


# ── Invariant 7: Execution Idempotency Prevents Double Spend ───
def test_invariant_7_execution_idempotency_prevents_double_spend():
    """
    Replaying the same transaction proposal with identical idempotency key
    returns the existing order and prevents duplicate debits or duplicate orders.
    """
    gateway = get_razorpay_gateway()
    idempotency_key = f"idempotent_test_{uuid.uuid4().hex[:12]}"

    # First settlement attempt
    first_res = gateway.create_order(
        amount=1450.0,
        currency="INR",
        idempotency_key=idempotency_key,
    )
    assert first_res["success"] is True
    assert first_res["idempotent_replay"] is False
    order_id = first_res["order_id"]

    # Second settlement attempt (e.g. network retry or concurrent duplicate request)
    second_res = gateway.create_order(
        amount=1450.0,
        currency="INR",
        idempotency_key=idempotency_key,
    )
    assert second_res["success"] is True
    assert second_res["idempotent_replay"] is True
    assert second_res["order_id"] == order_id, "Idempotent replay must return identical order_id"


# ── Invariant 8: Audit Chain Sequential & SHA-256 Chained ────
@pytest.mark.asyncio
async def test_invariant_8_audit_chain_sequential_and_tamper_evident():
    """
    Audit log entries are strictly sequential and linked via SHA-256 hash chaining.
    Modifying any historical record invalidates the entire subsequent chain.
    """
    await init_db()
    session_maker = await get_session()
    async with session_maker as session:
        # Create 3 sequential audit records
        mandate_id = str(uuid.uuid4())
        record_ids = []
        for i in range(3):
            audit_data = {
                "id": str(uuid.uuid4()),
                "decision_id": str(uuid.uuid4()),
                "mandate_id": mandate_id,
                "transaction_id": str(uuid.uuid4()),
                "structural_result": {"overall_pass": True},
                "final_decision": "ALLOW" if i % 2 == 0 else "BLOCK",
                "explanation": f"Sequential test record {i}",
            }
            row = await create_audit_log(session, audit_data)
            record_ids.append(row.id)

        # Verify chain integrity
        is_valid, errors = await verify_audit_chain(session)
        assert is_valid is True, f"Audit chain verification failed: {errors}"
        assert len(errors) == 0

        # Tamper with the first record to simulate an insider attack
        first_row = await session.get(AuditLogRow, record_ids[0])
        original_decision = first_row.final_decision
        first_row.final_decision = "TAMPERED_ALLOW"
        await session.commit()

        # Chain verification must now catch the tampering
        tamper_valid, tamper_errors = await verify_audit_chain(session)
        assert tamper_valid is False
        assert len(tamper_errors) > 0
        assert any("Hash mismatch" in err or "tampered" in err.lower() for err in tamper_errors)

        # Restore original state for cleanliness
        first_row.final_decision = original_decision
        await session.commit()
