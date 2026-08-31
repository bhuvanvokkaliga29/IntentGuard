"""
Tests for Autonomous Proposer Agents:
- BuyingAgent
- RecommendationAgent
- VoiceMandateAgent
"""

import pytest
from backend.agent.proposer_buying import BuyingAgent, BuyingObjective
from backend.agent.proposer_recommendation import RecommendationAgent
from backend.agent.proposer_voice import VoiceMandateAgent
from backend.data.seed_data import SEED_MANDATES


def test_buying_agent_proposes_within_budget():
    agent = BuyingAgent()
    mandate = SEED_MANDATES[0]  # Office supplies ≤ 2000

    proposal = agent.generate_proposal(mandate, objective=BuyingObjective.BEST_RATING)
    assert proposal.agent_type == "buying_agent"
    assert proposal.amount <= mandate["max_amount_per_txn"]
    assert proposal.merchant_name in mandate["allowed_merchants"]
    assert proposal.proposal_id.startswith("prop-buy-")
    assert len(proposal.activity_log) >= 3


def test_buying_agent_lowest_price_objective():
    agent = BuyingAgent()
    mandate = SEED_MANDATES[0]

    proposal = agent.generate_proposal(mandate, objective=BuyingObjective.LOWEST_PRICE)
    assert proposal.objective_used == "LOWEST_PRICE"
    assert proposal.amount <= 1000.0  # Lowest price items like sticky notes or paper are cheap


def test_recommendation_agent_promotional_focus():
    agent = RecommendationAgent()
    mandate = SEED_MANDATES[0]

    proposal = agent.generate_recommendation(mandate, recommendation_focus="PROMOTIONAL_UPSELL")
    assert proposal.agent_type == "recommendation_agent"
    assert proposal.proposal_id.startswith("prop-rec-")
    assert "recommendation_strategy" in proposal.observable_factors
    assert proposal.amount > 0


def test_voice_mandate_agent_parses_natural_language():
    transcript = "Every week get the normal supplies I need for my office. Don't spend more than two thousand."
    res = VoiceMandateAgent.parse_natural_language(transcript)

    assert res.parsed_mandate.max_amount_per_txn == 2000.0
    assert res.parsed_mandate.frequency == "weekly"
    assert "office_supplies" in res.parsed_mandate.allowed_categories
    assert "Stationery Mart" in (res.parsed_mandate.allowed_merchants or [])
    assert res.confidence_of_parsing > 0.8
