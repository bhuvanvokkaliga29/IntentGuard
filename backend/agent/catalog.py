"""
IntentGuard — Synthetic Catalog Service

Provides query, search, and retrieval capabilities for proposer agents
over merchants and products.
"""

from typing import List, Dict, Optional
from backend.data.catalog_data import MERCHANTS, PRODUCTS


class CatalogService:
    def __init__(self, merchants: Optional[List[Dict]] = None, products: Optional[List[Dict]] = None):
        self._merchants = {m["id"]: m for m in (merchants or MERCHANTS)}
        self._products = {p["id"]: p for p in (products or PRODUCTS)}

    def get_merchant(self, merchant_id: str) -> Optional[Dict]:
        return self._merchants.get(merchant_id)

    def get_product(self, product_id: str) -> Optional[Dict]:
        return self._products.get(product_id)

    def list_merchants(self) -> List[Dict]:
        return list(self._merchants.values())

    def list_products(self) -> List[Dict]:
        return list(self._products.values())

    def search_candidates(
        self,
        allowed_merchants: Optional[List[str]] = None,
        max_budget: Optional[float] = None,
        category_keyword: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search products matching loose structural constraints.
        Enriches product records with merchant metadata.
        """
        candidates = []
        for p in self._products.values():
            merchant = self._merchants.get(p["merchant_id"])
            if not merchant:
                continue

            # Check merchant filter if supplied
            if allowed_merchants is not None:
                merchant_name = merchant["name"].lower()
                allowed_lower = [m.lower() for m in allowed_merchants]
                # If merchant not in allowed list, agent might still view it if it ignores merchant restrictions
                # But we annotate the match
                is_merchant_allowed = any(a in merchant_name or merchant_name in a for a in allowed_lower)
            else:
                is_merchant_allowed = True

            # Price check
            is_within_budget = True
            if max_budget is not None and p["price"] > max_budget:
                is_within_budget = False

            candidates.append({
                **p,
                "merchant_name": merchant["name"],
                "merchant_category": merchant["category"],
                "merchant_rating": merchant["rating"],
                "is_approved_merchant": is_merchant_allowed,
                "is_within_budget": is_within_budget,
            })
        return candidates

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        return self._products.get(product_id)

    def search_products(
        self,
        query: str = "",
        category: Optional[str] = None,
        merchant_name: Optional[str] = None,
        max_price: Optional[float] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Search products with query string and optional filters."""
        results = []
        q = query.lower()
        for p in self._products.values():
            merchant = self._merchants.get(p["merchant_id"])
            if not merchant:
                continue

            # Query filter
            if q and q not in p["name"].lower() and q not in p.get("description", "").lower():
                continue

            # Category filter
            if category and category.lower() not in p.get("category", "").lower() and category.lower() not in merchant.get("category", "").lower():
                continue

            # Merchant filter
            if merchant_name and merchant_name.lower() not in merchant["name"].lower():
                continue

            # Max price filter
            if max_price is not None and p["price"] > max_price:
                continue

            results.append({
                **p,
                "merchant_name": merchant["name"],
                "merchant_category": merchant["category"],
                "merchant_rating": merchant["rating"],
            })
            if len(results) >= limit:
                break
        return results


_default_catalog = CatalogService()


def get_catalog() -> CatalogService:
    return _default_catalog


def get_catalog_service() -> CatalogService:
    return _default_catalog
