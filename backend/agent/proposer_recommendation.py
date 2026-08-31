"""
IntentGuard — AI Recommendation Agent (Proposer)

Simulates an AI recommendation system influencing an autonomous purchase.
The recommendation agent optimizes for promotional bundles, discount traps,
cross-category upselling, or high vendor ratings.

CRITICAL ARCHITECTURAL ROLE:
The Recommendation Agent is strictly a TRANSACTION-PROPOSING AGENT.
It shows how optimization (discounts, popularity, merchant deals) can drift from intent.
IntentGuard is the gatekeeper that receives and verifies all proposals.
"""

import time
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.agent.catalog import get_catalog, CatalogService


class RecommendationProposalResponse(BaseModel):
    proposal_id: str
    agent_type: str = "recommendation_agent"
    mandate_id: str
    product_id: str
    product_name: str
    merchant_name: str
    merchant_category: str
    amount: float
    item_description: str
    recommendation_basis: str
    observable_factors: Dict[str, str]
    activity_log: List[Dict[str, str]]


class RecommendationAgent:
    def __init__(self, catalog: Optional[CatalogService] = None):
        self.catalog = catalog or get_catalog()

    def generate_recommendation(
        self,
        mandate: Dict,
        recommendation_focus: str = "PROMOTIONAL_UPSELL",
        target_product_id: Optional[str] = None,
    ) -> RecommendationProposalResponse:
        """
        Generate a transaction proposal based on recommendation algorithms.
        """
        logs = []
        now_ts = lambda: time.strftime("%H:%M:%S")

        logs.append({
            "timestamp": now_ts(),
            "actor": "RECOMMENDER",
            "event": "INGEST_MANDATE_CONTEXT",
            "detail": f"Analyzing user mandate intent context: '{mandate.get('intent_text', '')[:60]}...'."
        })

        budget_limit = mandate.get("max_amount_per_txn", 50000.0)
        allowed_merchants = mandate.get("allowed_merchants")

        logs.append({
            "timestamp": now_ts(),
            "actor": "RECOMMENDER",
            "event": "EVALUATE_COMMERCIAL_OFFERS",
            "detail": f"Scanning active merchant discounts and sponsored product feeds matching budget <= ₹{budget_limit:,.2f}."
        })

        candidates = self.catalog.search_candidates(
            allowed_merchants=allowed_merchants,
            max_budget=budget_limit,
        )

        selected_item = None
        if target_product_id:
            for item in candidates:
                if item["id"] == target_product_id:
                    selected_item = item
                    break

        if not selected_item:
            if recommendation_focus == "PROMOTIONAL_UPSELL":
                # Find high discount promoted item
                promos = [c for c in candidates if c.get("is_promoted")]
                selected_item = promos[0] if promos else candidates[0]
                basis = f"AI Recommender identified high-value deal ({selected_item.get('discount_percent', 20)}% promotional discount) with top merchant rating {selected_item.get('merchant_rating')}."
            elif recommendation_focus == "CROSS_CATEGORY":
                # Item in allowed merchant but adjacent category
                selected_item = max(candidates, key=lambda x: (x.get("rating", 0), x.get("discount_percent", 0)))
                basis = f"AI Recommender selected high-engagement item from approved vendor {selected_item['merchant_name']} based on collaborative filtering."
            else:
                selected_item = candidates[0]
                basis = "Standard automated recommendation matching available budget window."
        else:
            basis = f"Selected candidate '{selected_item['name']}' based on recommendation engine scoring ({recommendation_focus})."

        proposal_id = f"prop-rec-{str(uuid.uuid4())[:8]}"

        logs.append({
            "timestamp": now_ts(),
            "actor": "RECOMMENDER",
            "event": "PROPOSAL_GENERATED",
            "detail": f"Recommended '{selected_item['name']}' (₹{selected_item['price']:,.2f}) at {selected_item['merchant_name']}. Reason: {basis}"
        })

        factors = {
            "merchant_name": selected_item["merchant_name"],
            "merchant_rating": f"{selected_item.get('merchant_rating', 4.5)} / 5.0",
            "promotional_discount": f"{selected_item.get('discount_percent', 0)}%",
            "within_budget": "YES" if selected_item["price"] <= budget_limit else "NO",
            "recommendation_strategy": recommendation_focus,
        }

        return RecommendationProposalResponse(
            proposal_id=proposal_id,
            agent_type="recommendation_agent",
            mandate_id=mandate["id"],
            product_id=selected_item["id"],
            product_name=selected_item["name"],
            merchant_name=selected_item["merchant_name"],
            merchant_category=selected_item["merchant_category"],
            amount=float(selected_item["price"]),
            item_description=selected_item["description"],
            recommendation_basis=basis,
            observable_factors=factors,
            activity_log=logs,
        )
