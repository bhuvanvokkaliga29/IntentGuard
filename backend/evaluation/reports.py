"""
IntentGuard — Evaluation Report Generation

Generates JSON reports that the frontend reads directly.
No hardcoded evaluation numbers — everything is computed.
"""

import json
from typing import Dict, List

from backend.evaluation.metrics import (
    compute_confusion_matrix,
    compute_precision_recall_f1,
    compute_accuracy,
    compute_false_allow_rate,
    compute_false_block_rate,
    compute_escalation_accuracy,
)


def generate_baseline_report(
    baseline_name: str,
    predictions: List[str],
    ground_truths: List[str],
    latencies: List[float],
    llm_calls: int = 0,
    estimated_cost: float = 0.0,
) -> Dict:
    """
    Generate a complete evaluation report for a single baseline.
    """
    labels = ["ALLOW", "FLAG", "BLOCK", "ESCALATE"]

    precision, recall, f1 = compute_precision_recall_f1(
        predictions, ground_truths, labels
    )

    return {
        "baseline_name": baseline_name,
        "total_cases": len(predictions),
        "accuracy": compute_accuracy(predictions, ground_truths),
        "precision_per_class": precision,
        "recall_per_class": recall,
        "f1_per_class": f1,
        "confusion_matrix": compute_confusion_matrix(predictions, ground_truths, labels),
        "false_allow_rate": compute_false_allow_rate(predictions, ground_truths),
        "false_block_rate": compute_false_block_rate(predictions, ground_truths),
        "escalation_accuracy": compute_escalation_accuracy(predictions, ground_truths),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "total_llm_calls": llm_calls,
        "estimated_cost_usd": estimated_cost,
    }


def generate_comparison_report(
    baseline_reports: List[Dict],
    dataset_size: int,
) -> Dict:
    """
    Generate a comparison report across all baselines.
    """
    import uuid
    from datetime import datetime

    # Generate summary
    best_accuracy = max(r["accuracy"] for r in baseline_reports)
    best_baseline = next(r["baseline_name"] for r in baseline_reports if r["accuracy"] == best_accuracy)

    summary_parts = [
        f"Evaluated {dataset_size} transactions across {len(baseline_reports)} configurations.",
        f"Best overall accuracy: {best_baseline} ({best_accuracy:.1%}).",
    ]

    # Check if combined beats structural-only
    structural = next((r for r in baseline_reports if "structural" in r["baseline_name"].lower()), None)
    combined = next((r for r in baseline_reports if "combined" in r["baseline_name"].lower()), None)

    if structural and combined:
        improvement = combined["accuracy"] - structural["accuracy"]
        if improvement > 0:
            summary_parts.append(
                f"Combined system improves over structural-only by {improvement:.1%}."
            )

        # False allow comparison
        fa_improvement = structural["false_allow_rate"] - combined["false_allow_rate"]
        if fa_improvement > 0:
            summary_parts.append(
                f"False allow rate reduced by {fa_improvement:.1%} with semantic layer."
            )

    return {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "dataset_size": dataset_size,
        "baselines": baseline_reports,
        "summary": " ".join(summary_parts),
    }
