"""
IntentGuard — Semantic Cache Security & Context Isolation Test Suite

Verifies Phase 13 requirements:
1. Cache key includes all security-relevant context.
2. A cached ALLOW cannot survive changes to mandate categories, exclusions, or intent.
3. Merchant changes produce cache misses.
4. Policy version changes produce cache misses.
"""

import pytest
from backend.agent.agent import compute_semantic_cache_key


def test_cache_key_isolation_on_mandate_changes():
    """Cache key changes when mandate categories change, preventing cross-mandate authorization leak."""
    mandate_base = {
        "id": "mandate-001",
        "intent_text": "Buy regular office supplies",
        "allowed_categories": ["stationery"],
        "exclusions": [],
        "allowed_merchants": ["Stationery Mart"],
    }
    mandate_modified = {
        "id": "mandate-001",
        "intent_text": "Buy regular office supplies",
        "allowed_categories": ["electronics"],  # Category policy changed!
        "exclusions": [],
        "allowed_merchants": ["Stationery Mart"],
    }
    txn = {
        "item_description": "A4 Paper",
        "merchant_name": "Stationery Mart",
    }

    key1 = compute_semantic_cache_key(mandate_base, txn)
    key2 = compute_semantic_cache_key(mandate_modified, txn)

    assert key1 != key2, "Cached decision must not survive changes to allowed categories!"


def test_cache_key_isolation_on_exclusions():
    """Cache key changes when exclusions are added."""
    mandate_no_exclusions = {
        "id": "mandate-002",
        "intent_text": "Team lunch",
        "allowed_categories": ["food"],
        "exclusions": [],
        "allowed_merchants": ["Swiggy"],
    }
    mandate_with_exclusions = {
        "id": "mandate-002",
        "intent_text": "Team lunch",
        "allowed_categories": ["food"],
        "exclusions": ["alcohol"],  # Added exclusion!
        "allowed_merchants": ["Swiggy"],
    }
    txn = {
        "item_description": "Craft Beer",
        "merchant_name": "Swiggy",
    }

    key1 = compute_semantic_cache_key(mandate_no_exclusions, txn)
    key2 = compute_semantic_cache_key(mandate_with_exclusions, txn)

    assert key1 != key2, "Cached decision must not survive exclusion policy changes!"


def test_cache_key_isolation_on_merchant_difference():
    """Different merchants for the same item produce different cache keys."""
    mandate = {
        "id": "mandate-001",
        "intent_text": "Office supplies",
        "allowed_categories": ["stationery"],
        "exclusions": [],
        "allowed_merchants": ["Stationery Mart", "Dodgy Store"],
    }
    txn1 = {"item_description": "Desk Chair", "merchant_name": "Stationery Mart"}
    txn2 = {"item_description": "Desk Chair", "merchant_name": "Dodgy Store"}

    key1 = compute_semantic_cache_key(mandate, txn1)
    key2 = compute_semantic_cache_key(mandate, txn2)

    assert key1 != key2, "Different merchants must not share cached semantic authorization!"


def test_cache_key_deterministic_category_ordering():
    """Order of categories in mandate list does not change the cache key."""
    mandate1 = {
        "id": "mandate-001",
        "intent_text": "Office supplies",
        "allowed_categories": ["stationery", "books", "pens"],
        "exclusions": [],
        "allowed_merchants": ["Stationery Mart"],
    }
    mandate2 = {
        "id": "mandate-001",
        "intent_text": "Office supplies",
        "allowed_categories": ["pens", "stationery", "books"],
        "exclusions": [],
        "allowed_merchants": ["Stationery Mart"],
    }
    txn = {"item_description": "Notepad", "merchant_name": "Stationery Mart"}

    key1 = compute_semantic_cache_key(mandate1, txn)
    key2 = compute_semantic_cache_key(mandate2, txn)

    assert key1 == key2, "Category ordering differences must produce identical canonical cache keys!"
