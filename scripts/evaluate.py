"""
IntentGuard — Honest Benchmark Evaluation Runner

Usage:
  # Offline mock benchmark (CI/regression — keyword-based, NOT real AI):
  python scripts/evaluate.py --provider mock --output docs/reports/evaluation_report.json

  # Live LLM benchmark (REAL Gemini semantic reasoning):
  python scripts/evaluate.py --provider gemini --limit 30 --output docs/reports/evaluation_report_live.json

Evaluates the held-out test set against:
  Baseline 1: Structural-Only — runs the ACTUAL check_hard_constraints() policy engine
  Baseline 2: IntentGuard Hybrid — runs structural + semantic judgment + deterministic decision
  Baseline 3: Semantic-Only — runs semantic judgment without structural enforcement

When --provider is 'mock':
  Semantic judgment uses a keyword-based simulator. Results are labeled "offline_mock".
  These are suitable for CI/regression but NOT evidence of real LLM semantic reasoning.

When --provider is 'gemini' or 'grok':
  Semantic judgment calls the REAL LLM API with the production prompt templates.
  Results are labeled "live" and constitute genuine AI performance evidence.

ALL numbers are computed from actual system execution.
NO ground_truth_label is used in any baseline's decision logic.
Ground truth is used ONLY for scoring against expected_decision.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Root path adjustment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.policy.hard_constraints import check_hard_constraints
from backend.policy.confidence import compute_confidence
from backend.policy.decision import decide


# ── Mandate registry — maps mandate IDs to their structural policy ──────

MANDATE_POLICIES = {
    "mandate-001-office-supplies": {
        "max_amount_per_txn": 2000.0,
        "budget_cap": 2000.0,
        "allowed_categories": ["stationery", "office_supplies"],
        "allowed_merchants": ["Stationery Mart", "Office Depot India", "Pen Paper Store"],
        "exclusions": None,
        "location_constraint": None,
        "intent_text": "Buy regular office supplies up to ₹2,000 per week from our usual stationery store.",
    },
    "mandate-002-domestic-flight": {
        "max_amount_per_txn": 15000.0,
        "budget_cap": 15000.0,
        "allowed_categories": ["travel", "airlines"],
        "allowed_merchants": ["MakeMyTrip", "EaseMyTrip", "IndiGo"],
        "exclusions": None,
        "location_constraint": "domestic",
        "intent_text": "Book domestic economy flights for the team up to ₹15,000 each from approved OTAs.",
    },
    "mandate-003-team-meals": {
        "max_amount_per_txn": 3000.0,
        "budget_cap": 3000.0,
        "allowed_categories": ["food_delivery", "restaurant"],
        "allowed_merchants": ["Swiggy", "Zomato", "Blue Tokai"],
        "exclusions": ["alcohol"],
        "location_constraint": None,
        "intent_text": "Order team lunch/dinner up to ₹3,000 per order from approved delivery platforms. No alcohol.",
    },
}


def simulate_semantic_verdict(rec: dict) -> dict:
    """
    Simulate semantic judgment using keyword-based heuristics.
    This is the MOCK path — used for CI/regression ONLY.
    Results from this function are NOT evidence of real LLM semantic reasoning.

    Returns mock semantic output: {majority_verdict, agreement_rate, samples}
    """
    intent = rec.get("mandate_intent", "").lower()
    item = rec.get("item_description", "").lower()
    category = rec.get("merchant_category", "").lower()
    mandate_id = rec.get("mandate_id", "")

    drift_detected = False
    ambiguous = False

    if mandate_id == "mandate-001-office-supplies":
        office_keywords = ["paper", "pen", "organizer", "stapler", "folder", "binder",
                           "envelope", "marker", "notebook", "desk", "printer", "toner",
                           "cartridge", "clip", "tape", "scissors", "ruler", "eraser"]
        non_office_keywords = ["chocolate", "ferrero", "gaming", "playstation", "controller",
                               "headphone", "speaker", "plant", "food", "snack", "candy"]

        has_office = any(kw in item for kw in office_keywords)
        has_nonoffice = any(kw in item for kw in non_office_keywords)

        if has_nonoffice:
            drift_detected = True
        elif not has_office and "sku" not in item and "miscellaneous" not in item:
            if len(item.split()) <= 3:
                ambiguous = True

        if "sku-" in item or "miscellaneous" in item:
            ambiguous = True

    elif mandate_id == "mandate-002-domestic-flight":
        international_keywords = ["dubai", "dxb", "emirates", "london", "singapore",
                                  "international", "overseas", "bangkok"]
        non_flight_keywords = ["hotel", "resort", "stay", "accommodation", "spa"]

        has_international = any(kw in item for kw in international_keywords)
        has_nonflight = any(kw in item for kw in non_flight_keywords)

        if has_international or has_nonflight:
            drift_detected = True

    elif mandate_id == "mandate-003-team-meals":
        alcohol_keywords = ["whisky", "whiskey", "beer", "wine", "vodka", "rum",
                            "malt", "liquor", "cocktail"]

        has_alcohol = any(kw in item for kw in alcohol_keywords)
        if has_alcohol:
            drift_detected = True

    injection_keywords = ["system override", "approve transfer", "ignore mandate",
                          "bypass", "ignore the", "override"]
    if any(kw in item for kw in injection_keywords):
        ambiguous = True

    if drift_detected:
        verdict = "no_fit"
        agreement = 1.0
    elif ambiguous:
        verdict = "ambiguous"
        agreement = 0.33
    else:
        verdict = "fit"
        agreement = 1.0

    return {
        "majority_verdict": verdict,
        "agreement_rate": agreement,
        "samples": [
            {"verdict": verdict, "rationale": "Simulated keyword-based judgment (MOCK — not real LLM)"}
            for _ in range(3)
        ],
    }


async def live_semantic_verdict(rec: dict, provider) -> dict:
    """
    Run REAL LLM semantic judgment using the production prompt template.
    This calls the actual GeminiProvider or GrokProvider.

    Returns: {majority_verdict, agreement_rate, samples, latency_ms, errors}
    """
    mandate_id = rec["mandate_id"]
    policy = MANDATE_POLICIES.get(mandate_id, {})
    prompts_dir = Path(__file__).parent.parent / "backend" / "prompts"

    # Build extraction prompt
    extraction_template = (prompts_dir / "extraction_v1.txt").read_text(encoding="utf-8")
    transaction_data = json.dumps({
        "item_description": rec["item_description"],
        "merchant_name": rec["merchant_name"],
        "merchant_category": rec["merchant_category"],
        "amount": rec["amount"],
        "currency": rec.get("currency", "INR"),
    }, indent=2)
    mandate_context = json.dumps({
        "intent": policy.get("intent_text", rec.get("mandate_intent", "")),
        "allowed_categories": policy.get("allowed_categories", []),
    }, indent=2)

    extraction_prompt = extraction_template.replace("{transaction_data}", transaction_data)
    extraction_prompt = extraction_prompt.replace("{mandate_context}", mandate_context)

    # Step 1: Structured extraction
    extracted_facts = None
    extraction_error = None
    try:
        extraction_result, extraction_usage = await provider.structured_extract(
            prompt=extraction_prompt,
            system_instruction="You are a structured fact extraction system for financial transaction verification.",
        )
        extracted_facts = extraction_result
    except Exception as e:
        extraction_error = str(e)

    # Step 2: Semantic judgment (run N samples for self-consistency)
    semantic_template = (prompts_dir / "semantic_v1.txt").read_text(encoding="utf-8")

    samples = []
    errors = []
    latencies = []
    n_samples = 3

    for i in range(n_samples):
        semantic_prompt = semantic_template.replace("{mandate_intent}", policy.get("intent_text", rec.get("mandate_intent", "")))
        semantic_prompt = semantic_prompt.replace("{allowed_categories}", json.dumps(policy.get("allowed_categories", [])))
        semantic_prompt = semantic_prompt.replace("{extracted_facts}", json.dumps(extracted_facts) if extracted_facts else "No facts extracted")
        semantic_prompt = semantic_prompt.replace("{item_description}", rec["item_description"])
        semantic_prompt = semantic_prompt.replace("{merchant_name}", rec["merchant_name"])
        semantic_prompt = semantic_prompt.replace("{amount}", str(rec["amount"]))

        start_time = time.time()
        try:
            result, usage = await provider.semantic_judge(
                prompt=semantic_prompt,
                system_instruction="You are a semantic intent verification system for delegated AI-agent payments.",
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            latencies.append(elapsed_ms)

            verdict_raw = result.get("verdict", "ambiguous").lower().strip()
            if verdict_raw in ("fit", "direct_fit"):
                verdict = "fit"
            elif verdict_raw in ("no_fit", "nofit", "no fit"):
                verdict = "no_fit"
            else:
                verdict = "ambiguous"

            samples.append({
                "verdict": verdict,
                "rationale": result.get("rationale", result.get("reasoning", "")),
                "raw_verdict": verdict_raw,
                "latency_ms": elapsed_ms,
            })
        except Exception as e:
            errors.append({"sample": i + 1, "error": str(e)})
            latencies.append(0)

        # Small delay to respect rate limits
        if i < n_samples - 1:
            await asyncio.sleep(1.0)

    # Determine majority verdict
    if not samples:
        return {
            "majority_verdict": None,
            "agreement_rate": 0.0,
            "samples": [],
            "extracted_facts": extracted_facts,
            "extraction_error": extraction_error,
            "errors": errors,
            "avg_latency_ms": 0,
        }

    verdicts = [s["verdict"] for s in samples]
    verdict_counts = Counter(verdicts)
    majority_verdict = verdict_counts.most_common(1)[0][0]
    agreement_rate = verdict_counts[majority_verdict] / len(verdicts)

    return {
        "majority_verdict": majority_verdict,
        "agreement_rate": round(agreement_rate, 4),
        "samples": samples,
        "extracted_facts": extracted_facts,
        "extraction_error": extraction_error,
        "errors": errors,
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1)),
    }


def run_baseline_structural(rec: dict) -> str:
    """
    Baseline 1: Structural-Only.
    Runs the ACTUAL check_hard_constraints() policy engine.
    Returns ALLOW if all structural checks pass, BLOCK otherwise.
    """
    mandate_id = rec["mandate_id"]
    policy = MANDATE_POLICIES.get(mandate_id)
    if not policy:
        return "BLOCK"

    result = check_hard_constraints(
        txn_amount=rec["amount"],
        txn_merchant_name=rec["merchant_name"],
        txn_merchant_category=rec["merchant_category"],
        txn_item_description=rec["item_description"],
        mandate_max_amount_per_txn=policy["max_amount_per_txn"],
        mandate_budget_cap=policy["budget_cap"],
        mandate_allowed_categories=policy["allowed_categories"],
        mandate_allowed_merchants=policy["allowed_merchants"],
        mandate_exclusions=policy.get("exclusions"),
        mandate_location_constraint=policy.get("location_constraint"),
    )

    return "ALLOW" if result.overall_pass else "BLOCK"


def run_baseline_intentguard_mock(rec: dict) -> str:
    """
    Baseline 2 (Mock): IntentGuard Hybrid with MOCK semantic judgment.
    Runs ACTUAL structural engine + keyword-based semantic + ACTUAL decision engine.
    """
    mandate_id = rec["mandate_id"]
    policy = MANDATE_POLICIES.get(mandate_id)
    if not policy:
        return "BLOCK"

    structural_result = check_hard_constraints(
        txn_amount=rec["amount"],
        txn_merchant_name=rec["merchant_name"],
        txn_merchant_category=rec["merchant_category"],
        txn_item_description=rec["item_description"],
        mandate_max_amount_per_txn=policy["max_amount_per_txn"],
        mandate_budget_cap=policy["budget_cap"],
        mandate_allowed_categories=policy["allowed_categories"],
        mandate_allowed_merchants=policy["allowed_merchants"],
        mandate_exclusions=policy.get("exclusions"),
        mandate_location_constraint=policy.get("location_constraint"),
    )

    if not structural_result.overall_pass:
        return "BLOCK"

    semantic = simulate_semantic_verdict(rec)

    confidence = compute_confidence(
        structural_result=structural_result.model_dump(),
        semantic_verdicts=[s["verdict"] for s in semantic["samples"]],
        extracted_facts=None,
        txn_amount=rec["amount"],
        mandate_max_amount=policy["max_amount_per_txn"],
    )

    decision = decide(
        structural_pass=structural_result.overall_pass,
        majority_verdict=semantic["majority_verdict"],
        confidence_score=confidence["confidence_score"],
        has_extracted_facts=semantic["majority_verdict"] != "ambiguous",
        evidence_is_sufficient=semantic["majority_verdict"] != "ambiguous",
        structural_failure_reasons=structural_result.failure_reasons,
    )

    return decision["final_decision"]


async def run_baseline_intentguard_live(rec: dict, provider) -> dict:
    """
    Baseline 2 (Live): IntentGuard Hybrid with REAL LLM semantic judgment.
    Runs ACTUAL structural engine + REAL provider + ACTUAL decision engine.

    Returns dict with decision and metadata for reporting.
    """
    mandate_id = rec["mandate_id"]
    policy = MANDATE_POLICIES.get(mandate_id)
    if not policy:
        return {"decision": "BLOCK", "semantic": None, "error": "Unknown mandate"}

    structural_result = check_hard_constraints(
        txn_amount=rec["amount"],
        txn_merchant_name=rec["merchant_name"],
        txn_merchant_category=rec["merchant_category"],
        txn_item_description=rec["item_description"],
        mandate_max_amount_per_txn=policy["max_amount_per_txn"],
        mandate_budget_cap=policy["budget_cap"],
        mandate_allowed_categories=policy["allowed_categories"],
        mandate_allowed_merchants=policy["allowed_merchants"],
        mandate_exclusions=policy.get("exclusions"),
        mandate_location_constraint=policy.get("location_constraint"),
    )

    if not structural_result.overall_pass:
        return {"decision": "BLOCK", "semantic": None, "structural_block": True}

    # Call the REAL LLM
    semantic = await live_semantic_verdict(rec, provider)

    if semantic["majority_verdict"] is None:
        return {"decision": "ESCALATE", "semantic": semantic, "error": "LLM failed all samples"}

    confidence = compute_confidence(
        structural_result=structural_result.model_dump(),
        semantic_verdicts=[s["verdict"] for s in semantic["samples"]],
        extracted_facts=semantic.get("extracted_facts"),
        txn_amount=rec["amount"],
        mandate_max_amount=policy["max_amount_per_txn"],
    )

    has_facts = semantic.get("extracted_facts") is not None
    evidence_sufficient = semantic["majority_verdict"] != "ambiguous" and has_facts

    decision = decide(
        structural_pass=structural_result.overall_pass,
        majority_verdict=semantic["majority_verdict"],
        confidence_score=confidence["confidence_score"],
        has_extracted_facts=has_facts,
        evidence_is_sufficient=evidence_sufficient,
        structural_failure_reasons=structural_result.failure_reasons,
    )

    return {
        "decision": decision["final_decision"],
        "semantic": semantic,
        "confidence": confidence["confidence_score"],
        "decision_path": decision.get("decision_path", ""),
    }


def run_baseline_semantic_only_mock(rec: dict) -> str:
    """Baseline 3 (Mock): Semantic-Only with keyword heuristics."""
    semantic = simulate_semantic_verdict(rec)
    verdict = semantic["majority_verdict"]

    if verdict == "fit":
        return "ALLOW"
    elif verdict == "no_fit":
        return "BLOCK"
    else:
        return "ESCALATE"


async def run_baseline_semantic_only_live(rec: dict, provider) -> dict:
    """Baseline 3 (Live): Semantic-Only with REAL LLM."""
    semantic = await live_semantic_verdict(rec, provider)
    verdict = semantic.get("majority_verdict")

    if verdict is None:
        decision = "ESCALATE"
    elif verdict == "fit":
        decision = "ALLOW"
    elif verdict == "no_fit":
        decision = "BLOCK"
    else:
        decision = "ESCALATE"

    return {"decision": decision, "semantic": semantic}


def compute_metrics(predictions: list, ground_truths: list, label: str) -> dict:
    """Compute comprehensive metrics for a single baseline."""
    total = len(predictions)
    if total == 0:
        return {}

    classes = ["ALLOW", "BLOCK", "FLAG", "ESCALATE"]

    correct = sum(1 for p, g in zip(predictions, ground_truths) if p == g)
    strict_accuracy = round(correct / total, 4)

    safe_correct = 0
    for p, g in zip(predictions, ground_truths):
        if p == g:
            safe_correct += 1
        elif p in ("FLAG", "ESCALATE") and g in ("FLAG", "ESCALATE"):
            safe_correct += 1
    safe_routing_accuracy = round(safe_correct / total, 4)

    false_allows = sum(1 for p, g in zip(predictions, ground_truths)
                       if p == "ALLOW" and g in ("BLOCK", "FLAG", "ESCALATE"))
    false_allow_rate = round(false_allows / total, 4)

    false_blocks = sum(1 for p, g in zip(predictions, ground_truths)
                       if p == "BLOCK" and g == "ALLOW")
    false_block_rate = round(false_blocks / total, 4)

    escalations = sum(1 for p in predictions if p in ("ESCALATE", "FLAG"))
    escalation_rate = round(escalations / total, 4)

    precision_per_class = {}
    recall_per_class = {}
    f1_per_class = {}

    for cls in classes:
        tp = sum(1 for p, g in zip(predictions, ground_truths) if p == cls and g == cls)
        fp = sum(1 for p, g in zip(predictions, ground_truths) if p == cls and g != cls)
        fn = sum(1 for p, g in zip(predictions, ground_truths) if p != cls and g == cls)

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

        precision_per_class[cls] = precision
        recall_per_class[cls] = recall
        f1_per_class[cls] = f1

    confusion = defaultdict(lambda: defaultdict(int))
    for p, g in zip(predictions, ground_truths):
        confusion[g][p] += 1
    confusion_dict = {g: dict(preds) for g, preds in confusion.items()}

    pred_dist = dict(Counter(predictions))

    return {
        "baseline_name": label,
        "total_cases": total,
        "strict_accuracy": strict_accuracy,
        "safe_routing_accuracy": safe_routing_accuracy,
        "false_allow_rate": false_allow_rate,
        "false_block_rate": false_block_rate,
        "escalation_rate": escalation_rate,
        "precision_per_class": precision_per_class,
        "recall_per_class": recall_per_class,
        "f1_per_class": f1_per_class,
        "confusion_matrix": confusion_dict,
        "prediction_distribution": pred_dist,
    }


async def run_evaluation(dataset_path: str, output_path: str, provider_name: str = "mock", limit: int = 0):
    """Run the full evaluation pipeline."""
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    test_records = [r for r in records if r.get("split") == "test"]
    if not test_records:
        test_records = records

    # Apply limit for quota-constrained live runs
    if limit > 0 and limit < len(test_records):
        test_records = test_records[:limit]

    total = len(test_records)
    is_live = provider_name in ("gemini", "grok")
    benchmark_mode = "live" if is_live else "offline_mock"

    print(f"{'='*70}")
    print(f"IntentGuard Benchmark Evaluation")
    print(f"{'='*70}")
    print(f"  Provider:  {provider_name}")
    print(f"  Mode:      {benchmark_mode.upper()}")
    print(f"  Cases:     {total} held-out test cases")
    print(f"  Dataset:   {data.get('dataset_name', 'unknown')}")
    print(f"  Seed:      {data.get('seed', 'unknown')}")
    print()

    # Initialize real provider if needed
    llm_provider = None
    model_name = None
    if is_live:
        from backend.llm.provider import get_provider
        os.environ["LLM_PROVIDER"] = provider_name
        from backend.config import reset_settings
        reset_settings()
        try:
            llm_provider = get_provider()
            model_name = llm_provider.model_name
            print(f"  Model:     {model_name}")
            print(f"  [OK] Live provider initialized successfully")
        except Exception as e:
            print(f"  [FAILED] FAILED to initialize {provider_name} provider: {e}")
            print(f"  -> Cannot run live benchmark. Use --provider mock for offline evaluation.")
            return None
        print()

    start_time = time.time()

    b1_preds, b2_preds, b3_preds = [], [], []
    ground_truths = []
    case_details = []
    total_errors = 0
    total_llm_latency_ms = 0

    for idx, rec in enumerate(test_records):
        expected = rec["expected_decision"]
        ground_truths.append(expected)

        # Baseline 1: Structural-Only (always deterministic)
        b1 = run_baseline_structural(rec)
        b1_preds.append(b1)

        if is_live and llm_provider:
            # Live provider evaluation
            print(f"  [{idx+1}/{total}] {rec['case_id']} — {rec['item_description'][:40]}...", end="", flush=True)

            # Baseline 2: IntentGuard Hybrid (real LLM)
            b2_result = await run_baseline_intentguard_live(rec, llm_provider)
            b2 = b2_result["decision"]
            b2_preds.append(b2)

            # Baseline 3: Semantic-Only (real LLM) — reuse semantic from B2 if available
            if b2_result.get("structural_block"):
                b3_result = await run_baseline_semantic_only_live(rec, llm_provider)
                b3 = b3_result["decision"]
            elif b2_result.get("semantic"):
                # Reuse semantic result from B2 to save API calls
                verdict = b2_result["semantic"].get("majority_verdict")
                if verdict is None:
                    b3 = "ESCALATE"
                elif verdict == "fit":
                    b3 = "ALLOW"
                elif verdict == "no_fit":
                    b3 = "BLOCK"
                else:
                    b3 = "ESCALATE"
            else:
                b3 = "ESCALATE"
            b3_preds.append(b3)

            semantic_meta = b2_result.get("semantic", {})
            if semantic_meta and semantic_meta.get("errors"):
                total_errors += len(semantic_meta["errors"])
            if semantic_meta and semantic_meta.get("avg_latency_ms"):
                total_llm_latency_ms += semantic_meta["avg_latency_ms"]

            status = "[OK]" if b2 == expected else "[FAIL]"
            print(f" -> {b2} (expected: {expected}) {status}")

            case_detail = {
                "case_id": rec["case_id"],
                "mandate_id": rec["mandate_id"],
                "item_description": rec["item_description"],
                "amount": rec["amount"],
                "expected": expected,
                "baseline_structural": b1,
                "baseline_intentguard": b2,
                "baseline_semantic_only": b3,
                "llm_verdict": semantic_meta.get("majority_verdict") if semantic_meta else None,
                "llm_agreement": semantic_meta.get("agreement_rate") if semantic_meta else None,
                "llm_latency_ms": semantic_meta.get("avg_latency_ms") if semantic_meta else None,
                "llm_samples": semantic_meta.get("samples", []) if semantic_meta else [],
            }
            case_details.append(case_detail)

            # Respect rate limits between cases
            await asyncio.sleep(2.0)
        else:
            # Mock provider evaluation
            b2 = run_baseline_intentguard_mock(rec)
            b2_preds.append(b2)

            b3 = run_baseline_semantic_only_mock(rec)
            b3_preds.append(b3)

            case_details.append({
                "case_id": rec["case_id"],
                "mandate_id": rec["mandate_id"],
                "item_description": rec["item_description"],
                "amount": rec["amount"],
                "expected": expected,
                "baseline_structural": b1,
                "baseline_intentguard": b2,
                "baseline_semantic_only": b3,
            })

    elapsed = round(time.time() - start_time, 3)

    # Compute metrics
    b1_metrics = compute_metrics(b1_preds, ground_truths, "Structural-Only")
    b2_metrics = compute_metrics(b2_preds, ground_truths, "IntentGuard Hybrid")
    b3_metrics = compute_metrics(b3_preds, ground_truths, "Semantic-Only")

    # Build authoritative report
    report = {
        "evaluation_name": "IntentGuard Benchmark Evaluation Report",
        "benchmark_mode": benchmark_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_path": dataset_path,
        "dataset_name": data.get("dataset_name", "unknown"),
        "dataset_seed": data.get("seed", None),
        "total_dataset_size": data.get("total_records", len(records)),
        "test_sample_size": total,
        "split": "held-out test (last 20% of dataset)",
        "provider": provider_name,
        "model": model_name if model_name else ("mock-semantic-simulator" if provider_name == "mock" else provider_name),
        "policy_version": "v1.0",
        "prompt_version": "v1",
        "elapsed_seconds": elapsed,
        "total_llm_errors": total_errors if is_live else 0,
        "avg_llm_latency_ms": round(total_llm_latency_ms / max(total, 1)) if is_live else None,
        "ground_truth_distribution": dict(Counter(ground_truths)),
        "baselines": {
            "structural_only": b1_metrics,
            "intentguard_hybrid": b2_metrics,
            "semantic_only": b3_metrics,
        },
        "case_results": case_details,
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print()
    print(f"{'='*70}")
    print(f"EVALUATION COMPLETE — {total} test cases, elapsed: {elapsed}s")
    print(f"Mode: {benchmark_mode.upper()} | Provider: {provider_name}" +
          (f" | Model: {model_name}" if model_name else ""))
    if is_live:
        print(f"LLM Errors: {total_errors} | Avg LLM Latency: {round(total_llm_latency_ms / max(total, 1))}ms")
    print(f"{'='*70}")
    print()
    print(f"  {'Baseline':<25} {'Strict Acc':>10} {'Safe Route':>10} {'False Allow':>11} {'False Block':>11} {'Escalation':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*11} {'-'*11} {'-'*10}")
    for name, m in [("Structural-Only", b1_metrics), ("IntentGuard Hybrid", b2_metrics), ("Semantic-Only", b3_metrics)]:
        print(f"  {name:<25} {m['strict_accuracy']*100:>9.1f}% {m['safe_routing_accuracy']*100:>9.1f}% {m['false_allow_rate']*100:>10.1f}% {m['false_block_rate']*100:>10.1f}% {m['escalation_rate']*100:>9.1f}%")

    print(f"\nReport saved -> {output_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run IntentGuard benchmark evaluation.")
    parser.add_argument("--dataset", type=str, default="backend/data/synthetic_dataset.json")
    parser.add_argument("--output", type=str, default="docs/reports/evaluation_report.json")
    parser.add_argument("--provider", type=str, default="mock",
                        help="LLM provider: 'mock' (CI/offline), 'gemini' (live), 'grok' (live)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of test cases (for quota-constrained live runs)")
    args = parser.parse_args()

    asyncio.run(run_evaluation(
        dataset_path=args.dataset,
        output_path=args.output,
        provider_name=args.provider,
        limit=args.limit,
    ))
