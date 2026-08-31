"""
IntentGuard — Evaluation Metrics

Compute precision, recall, F1, confusion matrix, and custom metrics
for each decision class (ALLOW, FLAG, BLOCK, ESCALATE).
"""

from typing import Dict, List, Tuple
from collections import Counter


def compute_confusion_matrix(
    predictions: List[str],
    ground_truths: List[str],
    labels: List[str] = None,
) -> Dict[str, Dict[str, int]]:
    """
    Compute confusion matrix.
    
    Returns dict of {actual: {predicted: count}}.
    """
    if labels is None:
        labels = sorted(set(predictions + ground_truths))

    matrix = {actual: {pred: 0 for pred in labels} for actual in labels}
    for pred, truth in zip(predictions, ground_truths):
        if truth in matrix and pred in matrix[truth]:
            matrix[truth][pred] += 1

    return matrix


def compute_precision_recall_f1(
    predictions: List[str],
    ground_truths: List[str],
    labels: List[str] = None,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    """
    Compute per-class precision, recall, and F1.
    """
    if labels is None:
        labels = sorted(set(predictions + ground_truths))

    precision = {}
    recall = {}
    f1 = {}

    for label in labels:
        tp = sum(1 for p, g in zip(predictions, ground_truths) if p == label and g == label)
        fp = sum(1 for p, g in zip(predictions, ground_truths) if p == label and g != label)
        fn = sum(1 for p, g in zip(predictions, ground_truths) if p != label and g == label)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        precision[label] = round(prec, 4)
        recall[label] = round(rec, 4)
        f1[label] = round(f1_score, 4)

    return precision, recall, f1


def compute_accuracy(
    predictions: List[str],
    ground_truths: List[str],
) -> float:
    """Compute overall accuracy."""
    if not predictions:
        return 0.0
    correct = sum(1 for p, g in zip(predictions, ground_truths) if p == g)
    return round(correct / len(predictions), 4)


def compute_false_allow_rate(
    predictions: List[str],
    ground_truths: List[str],
) -> float:
    """
    False allow rate: cases that should have been BLOCK/FLAG/ESCALATE
    but were incorrectly ALLOWED.
    """
    should_not_allow = [
        (p, g) for p, g in zip(predictions, ground_truths)
        if g in ("BLOCK", "FLAG", "ESCALATE")
    ]
    if not should_not_allow:
        return 0.0
    false_allows = sum(1 for p, g in should_not_allow if p == "ALLOW")
    return round(false_allows / len(should_not_allow), 4)


def compute_false_block_rate(
    predictions: List[str],
    ground_truths: List[str],
) -> float:
    """
    False block rate: cases that should have been ALLOWED
    but were incorrectly BLOCKED.
    """
    should_allow = [
        (p, g) for p, g in zip(predictions, ground_truths)
        if g == "ALLOW"
    ]
    if not should_allow:
        return 0.0
    false_blocks = sum(1 for p, g in should_allow if p == "BLOCK")
    return round(false_blocks / len(should_allow), 4)


def compute_escalation_accuracy(
    predictions: List[str],
    ground_truths: List[str],
) -> float:
    """
    Escalation accuracy: how often ambiguous/unsafe_to_decide cases
    were correctly routed to FLAG or ESCALATE.
    """
    should_escalate = [
        (p, g) for p, g in zip(predictions, ground_truths)
        if g in ("FLAG", "ESCALATE")
    ]
    if not should_escalate:
        return 0.0
    correct_escalations = sum(
        1 for p, g in should_escalate
        if p in ("FLAG", "ESCALATE")
    )
    return round(correct_escalations / len(should_escalate), 4)


# ── Ground Truth Mapping ─────────────────────────────────────

def tier_to_expected_decision(tier: str) -> str:
    """
    Map ground truth tier to expected decision.
    
    clearly_in_scope → ALLOW
    clearly_out_of_scope → BLOCK
    ambiguous → FLAG
    unsafe_to_decide → ESCALATE
    """
    mapping = {
        "clearly_in_scope": "ALLOW",
        "clearly_out_of_scope": "BLOCK",
        "ambiguous": "FLAG",
        "unsafe_to_decide": "ESCALATE",
    }
    return mapping.get(tier, "ESCALATE")
