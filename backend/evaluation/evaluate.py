"""
IntentGuard — Evaluation Harness

Runs the full dataset through three configurations and generates a comparison:
- Baseline A: structural rules only
- Baseline B: semantic layer only  
- Baseline C: combined IntentGuard (full pipeline)

Persists results as JSON for the /evaluation frontend page.
Does NOT hardcode evaluation numbers.
"""

import json
import logging
import time
from typing import Dict, List, Optional

from backend.evaluation.baselines import baseline_structural_only, baseline_semantic_only
from backend.evaluation.metrics import tier_to_expected_decision
from backend.evaluation.reports import generate_baseline_report, generate_comparison_report

logger = logging.getLogger("intentguard.evaluation")


async def run_evaluation(session, provider=None) -> Dict:
    """
    Run the full evaluation harness.
    
    Args:
        session: Database session
        provider: Optional LLM provider. If None, only Baseline A runs.
    
    Returns:
        Complete evaluation report dict.
    """
    from backend.db import list_transactions, transaction_row_to_dict, get_mandate, mandate_row_to_dict
    from backend.policy.hard_constraints import check_hard_constraints

    logger.info("[EVALUATION] Starting evaluation harness...")

    # Load all transactions with ground truth
    txn_rows = await list_transactions(session)
    transactions = [transaction_row_to_dict(r, include_ground_truth=True) for r in txn_rows]

    if not transactions:
        logger.warning("[EVALUATION] No transactions found. Generate dataset first.")
        return {"error": "No transactions found. Run /dataset/generate first."}

    # Filter to transactions with ground truth labels
    labeled_txns = [t for t in transactions if t.get("ground_truth_tier")]
    logger.info(f"[EVALUATION] {len(labeled_txns)} labeled transactions found.")

    # Prepare ground truth
    ground_truths = [
        tier_to_expected_decision(t["ground_truth_tier"])
        for t in labeled_txns
    ]

    # ── Baseline A: Structural Only ───────────────────────────
    logger.info("[EVALUATION] Running Baseline A: Structural rules only...")
    baseline_a_predictions = []
    baseline_a_latencies = []

    for txn in labeled_txns:
        start = time.time()
        mandate_row = await get_mandate(session, txn["mandate_id"])
        if mandate_row is None:
            baseline_a_predictions.append("ESCALATE")
            baseline_a_latencies.append(0)
            continue

        mandate = mandate_row_to_dict(mandate_row)

        result = check_hard_constraints(
            txn_amount=txn["amount"],
            txn_merchant_name=txn["merchant_name"],
            txn_merchant_category=txn["merchant_category"],
            txn_item_description=txn["item_description"],
            mandate_max_amount_per_txn=mandate["max_amount_per_txn"],
            mandate_budget_cap=mandate.get("budget_cap"),
            mandate_allowed_categories=mandate.get("allowed_categories", []),
            mandate_allowed_merchants=mandate.get("allowed_merchants"),
            mandate_exclusions=mandate.get("exclusions"),
            mandate_location_constraint=mandate.get("location_constraint"),
        )

        prediction = baseline_structural_only(result.overall_pass)
        baseline_a_predictions.append(prediction)
        baseline_a_latencies.append((time.time() - start) * 1000)

    report_a = generate_baseline_report(
        "Baseline A: Structural Only",
        baseline_a_predictions,
        ground_truths,
        baseline_a_latencies,
        llm_calls=0,
    )
    logger.info(f"[EVALUATION] Baseline A accuracy: {report_a['accuracy']:.2%}")

    # ── Baseline C: Combined IntentGuard ──────────────────────
    baseline_reports = [report_a]

    if provider is not None:
        logger.info("[EVALUATION] Running Baseline C: Combined IntentGuard...")
        from backend.orchestrator import evaluate_transaction

        baseline_c_predictions = []
        baseline_c_latencies = []
        baseline_b_predictions = []
        total_llm_calls = 0

        for i, txn in enumerate(labeled_txns):
            logger.info(f"[EVALUATION] Processing {i+1}/{len(labeled_txns)}: {txn['item_description'][:50]}...")

            try:
                # Run full pipeline
                result = await evaluate_transaction(
                    session=session,
                    transaction_id=txn["id"],
                    mandate_id=txn["mandate_id"],
                )

                prediction = result.get("final_decision", "ESCALATE")
                latency = result.get("latency_ms", 0)
                baseline_c_predictions.append(prediction)
                baseline_c_latencies.append(latency)

                # For Baseline B: use semantic verdict ignoring structural
                semantic = result.get("semantic_judgment")
                if semantic and semantic.get("majority_verdict"):
                    sem_pred = baseline_semantic_only(
                        semantic["majority_verdict"],
                        result.get("confidence", 0.5),
                    )
                    baseline_b_predictions.append(sem_pred)
                else:
                    baseline_b_predictions.append("FLAG")

                total_llm_calls += 4  # ~1 extraction + 3 semantic samples

            except Exception as e:
                logger.error(f"[EVALUATION] Error processing {txn['id']}: {e}")
                baseline_c_predictions.append("ESCALATE")
                baseline_c_latencies.append(0)
                baseline_b_predictions.append("FLAG")

        # Generate Baseline B report (semantic only)
        report_b = generate_baseline_report(
            "Baseline B: Semantic Only",
            baseline_b_predictions,
            ground_truths,
            baseline_c_latencies,  # Use same latencies as approximation
            llm_calls=total_llm_calls,
        )
        baseline_reports.append(report_b)
        logger.info(f"[EVALUATION] Baseline B accuracy: {report_b['accuracy']:.2%}")

        # Generate Baseline C report (combined)
        report_c = generate_baseline_report(
            "Baseline C: Combined IntentGuard",
            baseline_c_predictions,
            ground_truths,
            baseline_c_latencies,
            llm_calls=total_llm_calls,
        )
        baseline_reports.append(report_c)
        logger.info(f"[EVALUATION] Baseline C accuracy: {report_c['accuracy']:.2%}")

    # ── Generate Comparison Report ────────────────────────────
    comparison = generate_comparison_report(baseline_reports, len(labeled_txns))

    # Persist to database
    from backend.db import save_evaluation_report
    await save_evaluation_report(session, json.dumps(comparison, default=str))

    logger.info("[EVALUATION] Evaluation complete. Report saved.")
    return comparison


if __name__ == "__main__":
    import asyncio
    from backend.db import init_db, get_session

    async def main():
        await init_db()
        session = await get_session()
        async with session:
            # Run structural-only baseline (no LLM needed)
            report = await run_evaluation(session, provider=None)
            print(json.dumps(report, indent=2))

    asyncio.run(main())
