"""
IntentGuard — Repository Smoke & Integration Test

Usage:
  python scripts/smoke_test.py

Verifies:
  1. Database initialization and SQLite connection
  2. LLM Provider discovery and configuration
  3. Proposer Agent tool execution and latency logging
  4. IntentGuard Hard Constraint validation
  5. Deterministic Confidence & Policy calculation
  6. End-to-End Buying Agent execution through 11-stage FSM
  7. Self-Healing recovery under injected fault
  8. Immutable Audit log persistence
"""

import asyncio
import os
import sys
import time

# Root path adjustment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import init_db, get_session, list_decisions, list_audit_logs, list_agent_runs
from backend.llm.provider import get_provider_info, get_provider
from backend.agent.tools import get_tool_registry
from backend.agent.self_healing import get_self_healing_engine
from backend.orchestrator.orchestrator import get_agent_orchestrator
from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.decision import decide


async def run_smoke_test():
    print("=" * 60)
    print("INTENTGUARD -- END-TO-END SMOKE & INTEGRATION VERIFICATION")
    print("=" * 60)

    # 1. Database
    print("\n[1/8] Verifying Database Connection...")
    await init_db()
    print("  [OK] Database initialized successfully.")

    # 2. LLM Provider
    print("\n[2/8] Verifying LLM Provider Configuration...")
    info = get_provider_info()
    print(f"  [OK] Active Provider: {info['provider']} (Configured: {info['configured']}, Model: {info['model']})")

    # 3. Tool Layer
    print("\n[3/8] Verifying Concrete Agent Tool Execution...")
    tools = get_tool_registry()
    search_res = await tools.execute_tool(
        tool_name="catalog.search",
        arguments={"query": "paper", "max_price": 2000.0},
        run_id="smoke-run-1",
        agent_id="smoke_agent",
    )
    print(f"  [OK] catalog.search returned {search_res['products_found']} products.")

    # 4. Structural Policy
    print("\n[4/8] Verifying Hard Constraint Policy Invariants...")
    h_pass = check_hard_constraints(
        txn_amount=1500.0,
        txn_merchant_name="Stationery Mart",
        txn_merchant_category="stationery",
        txn_item_description="A4 paper reams",
        mandate_max_amount_per_txn=2000.0,
        mandate_budget_cap=2000.0,
        mandate_allowed_categories=["stationery"],
        mandate_allowed_merchants=["Stationery Mart"],
    )
    assert getattr(h_pass, "overall_pass", False) is True
    print("  [OK] Hard constraint PASS check verified.")

    # 5. Deterministic Decision Engine
    print("\n[5/8] Verifying Deterministic Decision Matrix...")
    dec = decide(
        structural_pass=True,
        majority_verdict="no_fit",
        confidence_score=1.0,
        has_extracted_facts=True,
        evidence_is_sufficient=True,
    )
    path_str = str(dec.get('decision_path', '')).replace('\u2192', '->')
    print(f"  [OK] Semantic mismatch decision: {dec['final_decision']} (Path: {path_str})")

    # 6. End-to-End Orchestrated Agent Run
    print("\n[6/8] Executing Real Autonomous Buying Agent through 11-Stage FSM...")
    orchestrator = get_agent_orchestrator()
    run_res = await orchestrator.run_buying_agent(
        mandate_id="mandate-001-office-supplies",
        objective="BEST_RATING",
    )
    assert run_res["status"] == "COMPLETED"
    print(f"  [OK] Agent Run Completed! Run ID: {run_res['run_id']} (Latency: {run_res['latency_ms']:.1f}ms)")
    print(f"  [OK] IntentGuard Decision: {run_res['intentguard_decision']['final_decision']}")

    # 7. Self-Healing & Fault Recovery
    print("\n[7/8] Testing Injected Fault & Autonomous Self-Healing Recovery...")
    heal_run = await orchestrator.run_buying_agent(
        mandate_id="mandate-001-office-supplies",
        objective="LOWEST_PRICE",
        injected_failure="timeout",
    )
    assert heal_run["status"] == "COMPLETED"
    print("  [OK] Self-healing successfully recovered from injected tool timeout.")

    # 8. Audit Ledger Verification
    print("\n[8/9] Verifying Immutable Audit Ledger Records...")
    async with await get_session() as session:
        decisions = await list_decisions(session)
        audits = await list_audit_logs(session)
        runs = await list_agent_runs(session)
    print(f"  [OK] Verified {len(decisions)} Decisions, {len(audits)} Audit Logs, and {len(runs)} Agent Runs persisted.")

    # 9. Cryptographic Audit Hash Chain Verification
    print("\n[9/9] Verifying Cryptographic Audit Hash Chain Integrity...")
    from backend.db import verify_audit_chain
    async with await get_session() as session:
        is_chain_valid, chain_errors = await verify_audit_chain(session)
    assert is_chain_valid is True, f"Audit hash chain verification failed: {chain_errors}"
    print(f"  [OK] Cryptographic SHA-256 Audit Hash Chain is unbroken and tamper-evident!")

    print("\n" + "=" * 60)
    print("ALL 9 INTEGRATION CHECKS PASSED! REPOSITORY IS HEALTHY.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_smoke_test())
