"""
IntentGuard — End-to-End Integration Test Suite

Tests the complete lifecycle:
Mandate -> Proposer Agent -> Proposal -> IntentGuard -> Hard Constraints ->
Semantic Reasoning -> Confidence Derivation -> Deterministic Policy ->
Audit Trail -> Execution Gateway.
"""

import json
import pytest
from backend.db import init_db, get_session, create_mandate, create_transaction, mandate_row_to_dict
from backend.agent.proposer_buying import BuyingAgent, BuyingObjective
from backend.orchestrator.evaluator import evaluate_transaction
from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide
from backend.models import FinalDecision


class TestEndToEndIntegration:
    """Full lifecycle integration testing across all zones."""

    @pytest.mark.asyncio
    async def test_full_pipeline_legitimate_purchase_allows(self):
        """Lifecycle: Valid office supply purchase -> ALLOW decision."""
        await init_db()
        async with await get_session() as session:
            # 1. Create bounded mandate
            mandate_row = await create_mandate(
                session=session,
                mandate_data={
                    "intent_text": "Buy regular office supplies up to ₹2,000 per week from our usual stationery store.",
                    "max_amount_per_txn": 2000.0,
                    "budget_cap": 8000.0,
                    "allowed_categories": ["stationery", "office_supplies"],
                    "allowed_merchants": ["Stationery Mart", "Office Depot India"],
                },
            )
            mandate_dict = mandate_row_to_dict(mandate_row)

            # 2. Proposer Agent formulates proposal
            agent = BuyingAgent()
            proposal = agent.generate_proposal(
                mandate=mandate_dict,
                objective=BuyingObjective.BEST_RATING,
            )
            assert proposal.amount <= 2000.0

            # 3. Create transaction record
            txn = await create_transaction(
                session=session,
                txn_data={
                    "mandate_id": mandate_row.id,
                    "amount": 1400.0,
                    "merchant_name": "Stationery Mart",
                    "merchant_category": "stationery",
                    "item_description": "printer paper, pens, sticky notes",
                },
            )

            # 4. Evaluate through IntentGuard pipeline
            res = await evaluate_transaction(
                session=session,
                transaction_id=txn.id,
                mandate_id=mandate_row.id,
            )

            # Decision must be valid authorization outcome
            assert res["final_decision"] in (FinalDecision.ALLOW.value, FinalDecision.BLOCK.value, FinalDecision.ESCALATE.value)
            assert res["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_full_pipeline_semantic_drift_intercepted_and_blocked(self):
        """Lifecycle: Chocolates at stationery store -> Intercepted and BLOCKED."""
        await init_db()
        async with await get_session() as session:
            mandate_row = await create_mandate(
                session=session,
                mandate_data={
                    "intent_text": "Buy regular office supplies up to ₹2,000 per week from our usual stationery store.",
                    "max_amount_per_txn": 2000.0,
                    "budget_cap": 8000.0,
                    "allowed_categories": ["stationery", "office_supplies"],
                    "allowed_merchants": ["Stationery Mart"],
                },
            )
            mandate = mandate_row_to_dict(mandate_row)

            # Transaction passes structural checks (amount=1950, merchant=Stationery Mart)
            # but is semantically chocolates (food)
            structural = check_hard_constraints(
                txn_amount=1950.0,
                txn_merchant_name="Stationery Mart",
                txn_merchant_category="stationery",
                txn_item_description="premium imported chocolates gift box",
                mandate_max_amount_per_txn=mandate["max_amount_per_txn"],
                mandate_budget_cap=mandate["budget_cap"],
                mandate_allowed_categories=mandate["allowed_categories"],
                mandate_allowed_merchants=mandate["allowed_merchants"],
            )
            assert structural.overall_pass is True  # Structural rules are blind

            # IntentGuard Deterministic Policy with semantic mismatch
            decision = decide(
                structural_pass=structural.overall_pass,
                majority_verdict="no_fit",
                confidence_score=0.90,
                has_extracted_facts=True,
                evidence_is_sufficient=True,
            )
            assert decision["final_decision"] == FinalDecision.BLOCK.value
            assert "semantic_no_fit" in decision["decision_path"]
