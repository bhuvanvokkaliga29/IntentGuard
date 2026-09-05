"""
IntentGuard — Bounded Semantic LRU Cache Test Suite

Verifies:
1. Cache hit and miss mechanics
2. Deterministic LRU eviction at configurable max size
3. Stale mandate and policy mutation isolation
4. Invalidation by key and by mandate_id
5. Concurrent multithreaded access safety
6. Corruption recovery (malformed entries cleanly discarded)
7. Operational metrics accuracy (hits, misses, evictions, hit_rate)
"""

import threading
import pytest
from backend.semantic.cache import BoundedSemanticCache, get_semantic_cache, reset_semantic_cache
from backend.agent.agent import compute_semantic_cache_key


def test_cache_hit_and_miss_and_metrics():
    """Verify hit, miss, and metrics calculation."""
    cache = BoundedSemanticCache(max_size=10)
    assert len(cache) == 0

    # Cache miss
    miss = cache.get("nonexistent_key")
    assert miss is None
    m = cache.get_metrics()
    assert m["hits"] == 0
    assert m["misses"] == 1
    assert m["hit_rate"] == 0.0

    # Insert entry
    entry = {
        "extracted_facts": {"category": "office_supplies", "item_type": "pen"},
        "semantic_verdicts": ["fit", "fit", "fit"],
        "semantic_judgment_result": {"majority_verdict": "fit", "agreement_rate": 1.0},
    }
    cache.put("key_1", entry, mandate_id="mandate_1")
    assert len(cache) == 1

    # Cache hit
    hit = cache.get("key_1")
    assert hit is not None
    assert hit["extracted_facts"]["item_type"] == "pen"

    m = cache.get_metrics()
    assert m["hits"] == 1
    assert m["misses"] == 1
    assert m["hit_rate"] == 0.5


def test_deterministic_lru_eviction():
    """Verify that when cache exceeds max_size, oldest accessed items are evicted."""
    cache = BoundedSemanticCache(max_size=3)

    for i in range(1, 4):
        cache.put(
            f"key_{i}",
            {
                "extracted_facts": {"item": f"item_{i}"},
                "semantic_verdicts": ["fit"],
            },
            mandate_id=f"mandate_{i}",
        )
    assert len(cache) == 3

    # Access key_1 to make it most recently used (order now: key_2, key_3, key_1)
    _ = cache.get("key_1")

    # Add key_4 -> should evict key_2
    cache.put(
        "key_4",
        {
            "extracted_facts": {"item": "item_4"},
            "semantic_verdicts": ["fit"],
        },
        mandate_id="mandate_4",
    )

    assert len(cache) == 3
    assert cache.get("key_2") is None  # Evicted!
    assert cache.get("key_1") is not None  # Kept!
    assert cache.get("key_3") is not None  # Kept!
    assert cache.get("key_4") is not None  # Kept!

    m = cache.get_metrics()
    assert m["evictions"] == 1


def test_invalidate_by_key_and_mandate():
    """Verify invalidation mechanics for revocation/mutation."""
    cache = BoundedSemanticCache(max_size=10)

    cache.put("k1", {"extracted_facts": {}, "semantic_verdicts": []}, mandate_id="mandate_alpha")
    cache.put("k2", {"extracted_facts": {}, "semantic_verdicts": []}, mandate_id="mandate_alpha")
    cache.put("k3", {"extracted_facts": {}, "semantic_verdicts": []}, mandate_id="mandate_beta")

    assert len(cache) == 3

    # Invalidate mandate_alpha (should remove k1 and k2)
    evicted_count = cache.invalidate_mandate("mandate_alpha")
    assert evicted_count == 2
    assert len(cache) == 1
    assert cache.get("k1") is None
    assert cache.get("k2") is None
    assert cache.get("k3") is not None

    # Invalidate k3 by single key
    assert cache.invalidate("k3") is True
    assert len(cache) == 0


def test_corruption_recovery():
    """Verify malformed/corrupted cached entries are discarded and treated as misses."""
    cache = BoundedSemanticCache(max_size=5)

    # Insert malformed entry directly (simulating corrupted state)
    with cache._lock:
        cache._cache["corrupt_key"] = {"broken": "data"}  # missing extracted_facts and semantic_verdicts

    result = cache.get("corrupt_key")
    assert result is None  # Gracefully treated as miss
    assert "corrupt_key" not in cache  # Evicted corrupted record


def test_concurrent_multithreaded_access():
    """Verify thread-safe reading and writing without race conditions."""
    cache = BoundedSemanticCache(max_size=50)
    errors = []

    def writer_task(worker_id: int):
        try:
            for i in range(50):
                cache.put(
                    f"worker_{worker_id}_{i}",
                    {
                        "extracted_facts": {"worker": worker_id, "step": i},
                        "semantic_verdicts": ["fit"],
                    },
                    mandate_id=f"mandate_{worker_id}",
                )
        except Exception as e:
            errors.append(e)

    def reader_task(worker_id: int):
        try:
            for i in range(50):
                _ = cache.get(f"worker_{worker_id}_{i}")
        except Exception as e:
            errors.append(e)

    threads = []
    for w in range(5):
        t1 = threading.Thread(target=writer_task, args=(w,))
        t2 = threading.Thread(target=reader_task, args=(w,))
        threads.extend([t1, t2])

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    assert len(cache) <= 50  # Bound strictly respected under high concurrency


def test_stale_mandate_context_isolation():
    """
    Verify that policy context changes (exclusions, allowed merchants,
    allowed categories, prompt version) generate distinct cache keys.
    """
    mandate_base = {
        "id": "m1",
        "intent_text": "Buy stationary",
        "allowed_categories": ["office_supplies"],
        "exclusions": [],
        "allowed_merchants": ["Office Depot"],
    }
    txn = {"item_description": "pen", "merchant_name": "Office Depot"}

    key_base = compute_semantic_cache_key(mandate_base, txn, "v1")

    # Change exclusion
    m_excl = dict(mandate_base, exclusions=["luxury_pens"])
    key_excl = compute_semantic_cache_key(m_excl, txn, "v1")
    assert key_base != key_excl

    # Change merchant
    m_merch = dict(mandate_base, allowed_merchants=["Office Depot", "Staples"])
    key_merch = compute_semantic_cache_key(m_merch, txn, "v1")
    assert key_base != key_merch

    # Change policy version
    key_v2 = compute_semantic_cache_key(mandate_base, txn, "v2")
    assert key_base != key_v2
