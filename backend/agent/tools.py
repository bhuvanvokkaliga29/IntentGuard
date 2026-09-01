"""
IntentGuard — Agent Tool System & Telemetry Registry

Defines concrete backend tools callable by autonomous proposer agents, with
structured observability, failure simulation injection, latency measurement, and event bus integration.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.agent.catalog import get_catalog_service
from backend.db import create_tool_call, get_session, update_tool_call
from backend.orchestrator.event_bus import get_event_bus

logger = logging.getLogger("intentguard.tools")


class ToolExecutionError(Exception):
    """Raised when an agent tool invocation fails."""
    def __init__(self, message: str, failure_type: str = "TRANSIENT_TOOL_FAILURE"):
        super().__init__(message)
        self.failure_type = failure_type


class AgentToolRegistry:
    """Registry of concrete backend tools available to proposer agents."""

    def __init__(self):
        self.catalog_service = get_catalog_service()

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        run_id: str,
        agent_id: str,
        stage: str = "TOOL_CALL",
        injected_failure: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a registered tool with full telemetry and failure simulation hooks."""
        call_id = str(uuid.uuid4())
        event_bus = get_event_bus()
        start_time = time.time()

        # 1. Publish Tool Started Event & Record DB
        await event_bus.publish(
            event_type="agent.tool.started",
            run_id=run_id,
            agent_id=agent_id,
            stage=stage,
            payload={
                "tool_call_id": call_id,
                "tool_name": tool_name,
                "input_summary": arguments,
            },
        )

        try:
            async with await get_session() as session:
                await create_tool_call(
                    session=session,
                    run_id=run_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    input_summary=arguments,
                    call_id=call_id,
                )
        except Exception as e:
            logger.warning(f"[TOOLS] DB record failed: {e}")

        # 2. Check for Injected Demo Failures
        if injected_failure == "timeout":
            await asyncio.sleep(0.1)
            error_msg = f"Tool '{tool_name}' timed out after 3000ms."
            latency = (time.time() - start_time) * 1000
            await self._record_failure(call_id, run_id, agent_id, stage, tool_name, error_msg, latency, "TIMEOUT")
            raise ToolExecutionError(error_msg, failure_type="TIMEOUT")

        elif injected_failure == "unavailable":
            await asyncio.sleep(0.05)
            error_msg = f"Item or service requested via '{tool_name}' is temporarily unavailable."
            latency = (time.time() - start_time) * 1000
            await self._record_failure(call_id, run_id, agent_id, stage, tool_name, error_msg, latency, "UNAVAILABLE")
            raise ToolExecutionError(error_msg, failure_type="UNAVAILABLE_PRODUCT")

        # 3. Dispatch to Concrete Tool Implementation
        try:
            result = await self._dispatch(tool_name, arguments)
            latency = (time.time() - start_time) * 1000

            # Publish Success
            await event_bus.publish(
                event_type="agent.tool.completed",
                run_id=run_id,
                agent_id=agent_id,
                stage=stage,
                payload={
                    "tool_call_id": call_id,
                    "tool_name": tool_name,
                    "status": "SUCCESS",
                    "latency_ms": round(latency, 2),
                    "result_summary": result.get("summary", result),
                },
            )

            try:
                async with await get_session() as session:
                    await update_tool_call(
                        session=session,
                        call_id=call_id,
                        status="SUCCESS",
                        result_summary=result,
                        latency_ms=latency,
                    )
            except Exception as e:
                logger.warning(f"[TOOLS] DB update failed: {e}")

            return result

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_msg = str(e)
            await self._record_failure(call_id, run_id, agent_id, stage, tool_name, error_msg, latency, "EXECUTION_ERROR")
            raise ToolExecutionError(error_msg, failure_type="EXECUTION_ERROR")

    async def _record_failure(
        self,
        call_id: str,
        run_id: str,
        agent_id: str,
        stage: str,
        tool_name: str,
        error_msg: str,
        latency: float,
        failure_type: str,
    ):
        event_bus = get_event_bus()
        await event_bus.publish(
            event_type="agent.tool.failed",
            run_id=run_id,
            agent_id=agent_id,
            stage=stage,
            payload={
                "tool_call_id": call_id,
                "tool_name": tool_name,
                "status": "FAILED",
                "failure_type": failure_type,
                "error": error_msg,
                "latency_ms": round(latency, 2),
            },
        )
        try:
            async with await get_session() as session:
                await update_tool_call(
                    session=session,
                    call_id=call_id,
                    status="FAILED",
                    latency_ms=latency,
                    error=error_msg,
                )
        except Exception:
            pass

    async def _dispatch(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Route tool call to concrete handler."""
        if tool_name == "catalog.search":
            return await self._tool_catalog_search(args)
        elif tool_name == "merchant.lookup":
            return await self._tool_merchant_lookup(args)
        elif tool_name == "product.lookup":
            return await self._tool_product_lookup(args)
        elif tool_name == "pricing.lookup":
            return await self._tool_pricing_lookup(args)
        elif tool_name == "availability.lookup":
            return await self._tool_availability_lookup(args)
        elif tool_name == "preference.lookup":
            return await self._tool_preference_lookup(args)
        elif tool_name == "transaction.validate":
            return await self._tool_transaction_validate(args)
        else:
            raise ToolExecutionError(f"Unknown tool: '{tool_name}'", failure_type="UNKNOWN_TOOL")

    # ── Concrete Tool Implementations ──────────────────────────

    async def _tool_catalog_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query", "")
        category = args.get("category")
        merchant = args.get("merchant_name")
        max_price = args.get("max_price")

        products = self.catalog_service.search_products(
            query=query,
            category=category,
            merchant_name=merchant,
            max_price=max_price,
            limit=args.get("limit", 10),
        )

        return {
            "products_found": len(products),
            "products": products,
            "summary": f"Found {len(products)} products matching query='{query}' (category={category or 'any'}, max_price={max_price or 'unlimited'}).",
        }

    async def _tool_merchant_lookup(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("merchant_name", "")
        merchants = self.catalog_service.list_merchants()
        matched = [m for m in merchants if name.lower() in m["name"].lower()]

        if not matched:
            return {
                "matched": False,
                "merchant": None,
                "summary": f"Merchant '{name}' not found in registered catalog.",
            }
        return {
            "matched": True,
            "merchant": matched[0],
            "summary": f"Found merchant '{matched[0]['name']}' (Category: {matched[0]['category']}, Rating: {matched[0]['rating']}).",
        }

    async def _tool_product_lookup(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sku = args.get("sku") or args.get("product_id")
        product = self.catalog_service.get_product_by_id(sku or "")
        if not product:
            return {
                "found": False,
                "product": None,
                "summary": f"Product SKU '{sku}' not found.",
            }
        return {
            "found": True,
            "product": product,
            "summary": f"Found product '{product['name']}' priced at ₹{product['price']:,.2f}.",
        }

    async def _tool_pricing_lookup(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sku = args.get("sku") or args.get("product_id")
        qty = args.get("quantity", 1)
        product = self.catalog_service.get_product_by_id(sku or "")
        if not product:
            return {"error": "Product not found", "total_price": 0.0}

        unit_price = product.get("price", 0.0)
        discount = product.get("discount_percent", 0.0)
        discounted_unit = unit_price * (1.0 - discount / 100.0)
        total = discounted_unit * qty

        return {
            "sku": sku,
            "unit_price": unit_price,
            "discount_percent": discount,
            "discounted_unit_price": discounted_unit,
            "quantity": qty,
            "total_price": round(total, 2),
            "currency": "INR",
            "summary": f"Computed price for {qty}x '{product.get('name')}' = ₹{total:,.2f} (includes {discount}% discount).",
        }

    async def _tool_availability_lookup(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sku = args.get("sku") or args.get("product_id")
        product = self.catalog_service.get_product_by_id(sku or "")
        in_stock = product.get("in_stock", True) if product else False
        return {
            "sku": sku,
            "in_stock": in_stock,
            "dispatch_time": "Same-Day" if in_stock else "Backordered",
            "summary": f"SKU '{sku}' in-stock status: {in_stock}.",
        }

    async def _tool_preference_lookup(self, args: Dict[str, Any]) -> Dict[str, Any]:
        mandate_id = args.get("mandate_id", "")
        # Safe read of non-sensitive merchant preferences
        return {
            "mandate_id": mandate_id,
            "preferred_merchants": ["Stationery Mart", "Office Depot India"],
            "max_weekly_spend": 2000.0,
            "summary": f"Retrieved policy preferences for mandate '{mandate_id}'.",
        }

    async def _tool_transaction_validate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        amount = args.get("amount", 0.0)
        merchant = args.get("merchant_name", "")
        item = args.get("item_description", "")
        return {
            "valid_syntax": bool(amount > 0 and merchant and item),
            "amount": amount,
            "currency": "INR",
            "summary": f"Pre-validated transaction schema for ₹{amount} at '{merchant}'.",
        }


# Global Tool Registry Singleton
_tool_registry: Optional[AgentToolRegistry] = None


def get_tool_registry() -> AgentToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = AgentToolRegistry()
    return _tool_registry


# ── IntentGuard Verification Pipeline Tools ─────────────────

async def tool_get_mandate(session, mandate_id: str):
    from backend.db import get_mandate, mandate_row_to_dict
    start = time.time()
    row = await get_mandate(session, mandate_id)
    latency = (time.time() - start) * 1000
    data = mandate_row_to_dict(row) if row else None
    record = {
        "tool_name": "tool_get_mandate",
        "inputs": {"mandate_id": mandate_id},
        "output": data,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS" if data else "NOT_FOUND",
    }
    return data, record


async def tool_get_transaction(session, transaction_id: str):
    from backend.db import get_transaction, transaction_row_to_dict
    start = time.time()
    row = await get_transaction(session, transaction_id)
    latency = (time.time() - start) * 1000
    data = transaction_row_to_dict(row) if row else None
    record = {
        "tool_name": "tool_get_transaction",
        "inputs": {"transaction_id": transaction_id},
        "output": data,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS" if data else "NOT_FOUND",
    }
    return data, record


async def tool_get_merchant_context(merchant_name: str, merchant_category: str):
    start = time.time()
    service = get_catalog_service()
    merchants = service.list_merchants()
    matched = [m for m in merchants if merchant_name.lower() in m["name"].lower()]
    merchant_data = matched[0] if matched else {"name": merchant_name, "category": merchant_category}
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_get_merchant_context",
        "inputs": {"merchant_name": merchant_name, "merchant_category": merchant_category},
        "output": merchant_data,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS",
    }
    return merchant_data, record


async def tool_get_product_context(item_description: str):
    start = time.time()
    words = item_description.strip().split()
    quality = "insufficient" if len(words) <= 1 or item_description.lower().startswith("sku-") or item_description.lower().startswith("miscellaneous") else "sufficient"
    data = {
        "item_description": item_description,
        "word_count": len(words),
        "description_quality": quality,
    }
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_get_product_context",
        "inputs": {"item_description": item_description},
        "output": data,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS",
    }
    return data, record


async def tool_check_hard_constraints(mandate: Dict, transaction: Dict):
    from backend.policy.hard_constraints import check_hard_constraints
    start = time.time()
    result = check_hard_constraints(
        txn_amount=transaction["amount"],
        txn_merchant_name=transaction["merchant_name"],
        txn_merchant_category=transaction["merchant_category"],
        txn_item_description=transaction["item_description"],
        mandate_max_amount_per_txn=mandate["max_amount_per_txn"],
        mandate_budget_cap=mandate["budget_cap"],
        mandate_allowed_categories=mandate["allowed_categories"],
        mandate_allowed_merchants=mandate.get("allowed_merchants"),
        mandate_frequency=mandate.get("frequency", "on_demand"),
        mandate_exclusions=mandate.get("exclusions"),
        mandate_location_constraint=mandate.get("location_constraint"),
    )
    latency = (time.time() - start) * 1000
    res_dict = result.model_dump() if hasattr(result, "model_dump") else (result if isinstance(result, dict) else {"overall_pass": getattr(result, "overall_pass", False), "failure_reasons": getattr(result, "failure_reasons", [])})
    record = {
        "tool_name": "tool_check_hard_constraints",
        "inputs": {"transaction_amount": transaction["amount"], "merchant": transaction["merchant_name"]},
        "output": res_dict,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS" if res_dict.get("overall_pass") else "FAILED",
    }
    return res_dict, record


async def tool_extract_structured_facts(provider, transaction: Dict, mandate_intent: str):
    from backend.semantic.extraction import extract_structured_facts
    start = time.time()
    result, usage = await extract_structured_facts(
        provider=provider,
        item_description=transaction.get("item_description", ""),
        merchant_name=transaction.get("merchant_name", ""),
        merchant_category=transaction.get("merchant_category", ""),
        amount=transaction.get("amount", 0.0),
        mandate_intent=mandate_intent,
    )
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_extract_structured_facts",
        "inputs": {"item_description": transaction.get("item_description", "")},
        "output": result,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS" if result else "FAILED",
    }
    return result, record


async def tool_semantic_compare(provider, mandate_intent: str, allowed_categories: List[str], extracted_facts: Dict, transaction: Dict, num_samples: int = 3):
    from backend.semantic.entailment import semantic_judgment
    start = time.time()
    res_obj, usages = await semantic_judgment(
        provider=provider,
        mandate_intent=mandate_intent,
        allowed_categories=allowed_categories,
        extracted_facts=extracted_facts,
        item_description=transaction.get("item_description", ""),
        merchant_name=transaction.get("merchant_name", ""),
        amount=transaction.get("amount", 0.0),
        num_samples=num_samples,
    )
    latency = (time.time() - start) * 1000
    res_dict = res_obj.model_dump() if res_obj and hasattr(res_obj, "model_dump") else (res_obj if isinstance(res_obj, dict) else None)
    record = {
        "tool_name": "tool_semantic_compare",
        "inputs": {"mandate_intent": mandate_intent, "num_samples": num_samples},
        "output": res_dict,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS" if res_dict else "FAILED",
    }
    return res_dict, record


async def tool_compute_confidence(structural_result: Dict, semantic_verdicts: List[str], extracted_facts: Optional[Dict], txn_amount: float, mandate_max_amount: float, mandate_location_constraint: Optional[str]):
    from backend.policy.confidence import compute_confidence
    start = time.time()
    result = compute_confidence(
        structural_result=structural_result,
        semantic_verdicts=semantic_verdicts,
        extracted_facts=extracted_facts,
        txn_amount=txn_amount,
        mandate_max_amount=mandate_max_amount,
        mandate_location_constraint=mandate_location_constraint,
    )
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_compute_confidence",
        "inputs": {"verdicts": semantic_verdicts},
        "output": result,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS",
    }
    return result, record


async def tool_decide(structural_result: Dict, majority_verdict: Optional[str], confidence_score: float, has_extracted_facts: bool, evidence_is_sufficient: bool):
    from backend.policy.decision import decide
    start = time.time()
    result = decide(
        structural_pass=structural_result["overall_pass"],
        majority_verdict=majority_verdict,
        confidence_score=confidence_score,
        has_extracted_facts=has_extracted_facts,
        evidence_is_sufficient=evidence_is_sufficient,
        structural_failure_reasons=structural_result.get("failure_reasons", []),
    )
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_decide",
        "inputs": {"structural_pass": structural_result["overall_pass"], "majority_verdict": majority_verdict, "confidence": confidence_score},
        "output": result,
        "latency_ms": round(latency, 2),
        "status": "SUCCESS",
    }
    return result, record


async def tool_generate_explanation(
    provider,
    mandate_intent: str,
    transaction: Dict,
    structural_result: Dict,
    final_decision: str,
    confidence_score: float = 1.0,
    extracted_facts: Optional[Dict] = None,
    semantic_verdict: Optional[str] = None,
    majority_verdict: Optional[str] = None,
    semantic_rationale: Optional[str] = None,
    **kwargs,
):
    start = time.time()
    verdict = semantic_verdict or majority_verdict
    try:
        explanation, usage = await provider.generate_explanation(
            prompt=f"Decision: {final_decision}. Mandate: {mandate_intent}. Item: {transaction.get('item_description')}. Verdict: {verdict}. Confidence: {confidence_score}.",
            system_instruction="Explain financial authorization decision clearly and concisely in 2 sentences."
        )
    except Exception:
        suffix = "d" if final_decision.lower().endswith("e") else "ed"
        explanation = f"Transaction {final_decision.lower()}{suffix} based on structural rules and semantic intent alignment."
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_generate_explanation",
        "inputs": {"decision": final_decision},
        "output": {"explanation": explanation},
        "latency_ms": round(latency, 2),
        "status": "SUCCESS",
    }
    return explanation, record


async def tool_record_decision(session, decision_data: Any = None, **kwargs):
    from backend.db import create_decision
    start = time.time()
    if isinstance(decision_data, dict):
        payload = decision_data
    elif kwargs:
        payload = kwargs
    else:
        payload = {}
    if "id" not in payload:
        payload["id"] = str(uuid.uuid4())
    row = await create_decision(session=session, decision_data=payload)
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_record_decision",
        "inputs": {"decision_id": row.id},
        "output": {"saved": True, "id": row.id},
        "latency_ms": round(latency, 2),
        "status": "SUCCESS",
    }
    return row.id, record


async def tool_audit_decision(session, audit_data: Any = None, **kwargs):
    from backend.db import create_audit_log
    start = time.time()
    if isinstance(audit_data, dict):
        payload = audit_data
    elif kwargs:
        payload = kwargs
    else:
        payload = {}
    if "id" not in payload:
        payload["id"] = str(uuid.uuid4())
    row = await create_audit_log(session=session, audit_data=payload)
    latency = (time.time() - start) * 1000
    record = {
        "tool_name": "tool_audit_decision",
        "inputs": {"audit_id": row.id},
        "output": {"saved": True, "id": row.id},
        "latency_ms": round(latency, 2),
        "status": "SUCCESS",
    }
    return row.id, record
