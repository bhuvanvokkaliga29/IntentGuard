"""
IntentGuard — Autonomous Buying Agent (Proposer)

Simulates an autonomous purchasing agent acting on behalf of a user under a mandate.
The buying agent selects products from a synthetic catalog according to configurable
optimization objectives:
- LOWEST_PRICE
- BEST_RATING
- PROMOTION
- CONVENIENCE
- MERCHANT_LOYALTY
- CATEGORY_MATCH

CRITICAL ARCHITECTURAL ROLE:
The Buying Agent is strictly a TRANSACTION-PROPOSING AGENT.
It cannot authorize or execute payments. It emits transaction proposals
which MUST pass through IntentGuard.
"""

import time
import uuid
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from backend.agent.catalog import get_catalog, CatalogService


class BuyingObjective(str, Enum):
    LOWEST_PRICE = "LOWEST_PRICE"
    BEST_RATING = "BEST_RATING"
    PROMOTION = "PROMOTION"
    CONVENIENCE = "CONVENIENCE"
    MERCHANT_LOYALTY = "MERCHANT_LOYALTY"
    CATEGORY_MATCH = "CATEGORY_MATCH"


class BuyingProposalResponse(BaseModel):
    proposal_id: str
    agent_type: str = "buying_agent"
    mandate_id: str
    product_id: str
    product_name: str
    merchant_name: str
    merchant_category: str
    amount: float
    item_description: str
    objective_used: str
    selection_reason: str
    observable_factors: Dict[str, str]
    activity_log: List[Dict[str, str]]


class BuyingAgent:
    def __init__(self, catalog: Optional[CatalogService] = None):
        self.catalog = catalog or get_catalog()

    def generate_proposal(
        self,
        mandate: Dict,
        objective: BuyingObjective = BuyingObjective.BEST_RATING,
        target_product_id: Optional[str] = None,
    ) -> BuyingProposalResponse:
        """
        Execute autonomous selection logic over the synthetic catalog.
        
        Args:
            mandate: Dict of user mandate (id, intent_text, max_amount_per_txn, allowed_merchants, etc.)
            objective: Configurable optimization objective
            target_product_id: Optional explicit product override for canonical failure demos
        """
        logs = []
        now_ts = lambda: time.strftime("%H:%M:%S")

        logs.append({
            "timestamp": now_ts(),
            "actor": "BUYING_AGENT",
            "event": "MANDATE_LOADED",
            "detail": f"Loaded mandate '{mandate.get('intent_text', '')[:60]}...' with budget limit ₹{mandate.get('max_amount_per_txn', 0):,.2f}."
        })

        allowed_merchants = mandate.get("allowed_merchants")
        budget_limit = mandate.get("max_amount_per_txn", 50000.0)

        logs.append({
            "timestamp": now_ts(),
            "actor": "BUYING_AGENT",
            "event": "CATALOG_SEARCH_STARTED",
            "detail": f"Searching catalog for merchants matching: {allowed_merchants or 'All Merchants'} under ₹{budget_limit:,.2f}."
        })

        all_candidates = self.catalog.search_candidates(
            allowed_merchants=allowed_merchants,
            max_budget=budget_limit,
        )

        logs.append({
            "timestamp": now_ts(),
            "actor": "BUYING_AGENT",
            "event": "CANDIDATES_DISCOVERED",
            "detail": f"Discovered {len(all_candidates)} eligible candidate products across {len(set(c['merchant_name'] for c in all_candidates))} merchants."
        })

        # Filter to allowed merchants if strict loyalty
        eligible = [c for c in all_candidates if c["is_approved_merchant"] and c["is_within_budget"]]
        if not eligible:
            eligible = all_candidates

        # If specific target product requested (e.g. for canonical scenario reproduction)
        selected_item = None
        if target_product_id:
            for item in all_candidates:
                if item["id"] == target_product_id:
                    selected_item = item
                    break

        if not selected_item:
            # Optimize according to objective
            if objective == BuyingObjective.BEST_RATING:
                selected_item = max(eligible, key=lambda x: (x.get("rating", 0), -x.get("price", 0)))
                reason = f"Selected highest rated item ({selected_item.get('rating')} stars) from preferred merchant {selected_item['merchant_name']}."
            elif objective == BuyingObjective.PROMOTION:
                selected_item = max(eligible, key=lambda x: (x.get("discount_percent", 0), x.get("rating", 0)))
                reason = f"Selected item with maximum promotional discount ({selected_item.get('discount_percent')}% off) within available budget."
            elif objective == BuyingObjective.LOWEST_PRICE:
                selected_item = min(eligible, key=lambda x: x.get("price", 999999))
                reason = f"Selected most cost-effective option (₹{selected_item.get('price'):,.2f}) satisfying structural budget limit."
            elif objective == BuyingObjective.MERCHANT_LOYALTY:
                # Prefer first allowed merchant
                approved = [c for c in eligible if c["is_approved_merchant"]]
                selected_item = approved[0] if approved else eligible[0]
                reason = f"Selected item prioritizing existing preferred vendor relationship with {selected_item['merchant_name']}."
            elif objective == BuyingObjective.CATEGORY_MATCH:
                # Prioritize category matching mandate intent
                intent_words = set(mandate.get("intent_text", "").lower().split())
                selected_item = max(
                    eligible,
                    key=lambda x: sum(1 for w in intent_words if w in x["name"].lower() or w in x["category"].lower())
                )
                reason = f"Selected item with highest lexical category match to stated intent."
            else:
                selected_item = eligible[0]
                reason = "Selected standard candidate product meeting structural spending limits."
        else:
            reason = f"Selected product '{selected_item['name']}' based on simulated optimization goal ({objective.value})."

        logs.append({
            "timestamp": now_ts(),
            "actor": "BUYING_AGENT",
            "event": "CANDIDATE_SELECTED",
            "detail": f"Selected '{selected_item['name']}' at ₹{selected_item['price']:,.2f} from {selected_item['merchant_name']}. Objective: {objective.value}."
        })

        proposal_id = f"prop-buy-{str(uuid.uuid4())[:8]}"

        logs.append({
            "timestamp": now_ts(),
            "actor": "TRANSACTION_PROPOSAL",
            "event": "PROPOSAL_CREATED",
            "detail": f"Generated transaction proposal #{proposal_id} for ₹{selected_item['price']:,.2f} at {selected_item['merchant_name']}. Submitting to IntentGuard."
        })

        factors = {
            "merchant_allowed": "YES" if selected_item.get("is_approved_merchant") else "NO",
            "within_budget": "YES" if selected_item.get("price", 0) <= budget_limit else "NO",
            "product_rating": f"{selected_item.get('rating', 4.5)} / 5.0",
            "discount": f"{selected_item.get('discount_percent', 0)}%",
            "optimization_objective": objective.value,
        }

        return BuyingProposalResponse(
            proposal_id=proposal_id,
            agent_type="buying_agent",
            mandate_id=mandate["id"],
            product_id=selected_item["id"],
            product_name=selected_item["name"],
            merchant_name=selected_item["merchant_name"],
            merchant_category=selected_item["merchant_category"],
            amount=float(selected_item["price"]),
            item_description=selected_item["description"],
            objective_used=objective.value,
            selection_reason=reason,
            observable_factors=factors,
            activity_log=logs,
        )
