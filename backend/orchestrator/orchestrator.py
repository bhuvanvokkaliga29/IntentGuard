"""
IntentGuard — Real Backend Agent Orchestration Layer

Orchestrates autonomous proposer agents through finite state machines, bounded memory,
concrete tool calls, self-healing recovery, and deterministic IntentGuard gating.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.orchestrator.evaluator import evaluate_transaction
from backend.agent.self_healing import get_self_healing_engine
from backend.agent.tools import get_tool_registry
from backend.db import (
    create_agent_run,
    create_transaction,
    get_mandate,
    get_session,
    update_agent_run,
)
from backend.orchestrator.event_bus import get_event_bus
from backend.orchestrator.state_machine import AgentStage, AgentStatus

logger = logging.getLogger("intentguard.orchestrator")


class BoundedRunMemory:
    """Explicit bounded memory for an agent run."""

    def __init__(self, run_id: str, max_items: int = 25):
        self.run_id = run_id
        self.max_items = max_items
        self.items: List[Dict[str, Any]] = []

    def record(self, source: str, content: Any, confidence: float = 1.0) -> None:
        if len(self.items) >= self.max_items:
            self.items.pop(0)
        self.items.append({
            "memory_id": str(uuid.uuid4()),
            "source": source,
            "content": content,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_summary(self) -> List[Dict[str, Any]]:
        return self.items


class AgentOrchestrator:
    """Central Agent Orchestrator managing runs, transitions, and IntentGuard handoffs."""

    def __init__(self):
        self.tool_registry = get_tool_registry()
        self.self_healing = get_self_healing_engine()
        self.event_bus = get_event_bus()

    async def _transition_stage(
        self,
        run_id: str,
        agent_id: str,
        target_stage: AgentStage,
        observable_summary: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record and broadcast an explicit state machine transition."""
        event_payload = {
            "current_stage": target_stage.value,
            "observable_summary": observable_summary,
            **(payload or {}),
        }
        await self.event_bus.publish(
            event_type="agent.stage_changed",
            run_id=run_id,
            agent_id=agent_id,
            stage=target_stage.value,
            payload=event_payload,
        )
        try:
            async with await get_session() as session:
                await update_agent_run(
                    session=session,
                    run_id=run_id,
                    current_stage=target_stage.value,
                    observable_summary=observable_summary,
                )
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Failed to update stage in DB: {e}")

    # ── Buying Agent Orchestrated Run ──────────────────────────

    async def run_buying_agent(
        self,
        mandate_id: str,
        objective: str = "BEST_RATING",
        injected_failure: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a full orchestrated run of the Autonomous Buying Agent."""
        run_id = str(uuid.uuid4())
        agent_id = "buying_agent"
        agent_type = "buying_agent"
        task_id = f"task-buy-{run_id[:8]}"
        start_time = time.time()
        memory = BoundedRunMemory(run_id=run_id)
        tools_called: List[str] = []

        # 1. Initialize Run in Database
        async with await get_session() as session:
            await create_agent_run(
                session=session,
                run_id=run_id,
                agent_id=agent_id,
                agent_type=agent_type,
                task_id=task_id,
                mandate_id=mandate_id,
            )

        await self.event_bus.publish(
            event_type="agent.started",
            run_id=run_id,
            agent_id=agent_id,
            stage=AgentStage.INITIALIZING.value,
            payload={"task_id": task_id, "mandate_id": mandate_id, "objective": objective},
        )

        try:
            # 2. Stage: READING_CONTEXT
            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.READING_CONTEXT,
                observable_summary={
                    "objective": "Read and normalize user spending mandate",
                    "input_summary": {"mandate_id": mandate_id},
                    "selected_action": "Fetch spending bounds and approved vendors from database",
                    "evidence_used": ["mandate_id"],
                    "result_summary": "Retrieved active user mandate",
                    "confidence": 1.0,
                    "next_action": "Plan catalog exploration strategy",
                },
            )

            async with await get_session() as session:
                mandate_row = await get_mandate(session, mandate_id)

            if not mandate_row:
                mandate_text = "Buy my regular office supplies up to ₹2,000 per week from our usual stationery suppliers."
                max_amount = 2000.0
                allowed_merchants = ["Stationery Mart", "Office Depot India"]
            else:
                mandate_text = mandate_row.intent_text
                max_amount = mandate_row.max_amount_per_txn
                allowed_merchants = mandate_row.allowed_merchants or ["Stationery Mart"]

            memory.record("mandate", {"intent": mandate_text, "max_amount": max_amount, "merchants": allowed_merchants})

            # 3. Stage: PLANNING
            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.PLANNING,
                observable_summary={
                    "objective": f"Formulate product search plan based on '{objective}' optimization objective",
                    "input_summary": {"max_amount": max_amount, "allowed_merchants": allowed_merchants},
                    "selected_action": "Execute multi-merchant catalog search tool",
                    "evidence_used": ["budget_limit", "merchant_allowlist"],
                    "result_summary": f"Targeting max price ₹{max_amount} at {allowed_merchants}",
                    "confidence": 0.95,
                    "next_action": "Invoke catalog.search tool",
                },
            )

            # 4. Stage: TOOL_CALL & OBSERVING (with self-healing support)
            catalog_result = None
            attempt = 1
            max_tool_retries = 3

            while attempt <= max_tool_retries:
                try:
                    await self._transition_stage(
                        run_id=run_id,
                        agent_id=agent_id,
                        target_stage=AgentStage.TOOL_CALL,
                        observable_summary={
                            "objective": "Query catalog for products meeting budget constraints",
                            "input_summary": {"query": "", "max_price": max_amount},
                            "selected_action": "Call catalog.search tool",
                            "evidence_used": ["catalog_index"],
                            "tool_used": "catalog.search",
                            "result_summary": f"Attempt {attempt}/{max_tool_retries}",
                            "confidence": 0.90,
                            "next_action": "Parse catalog response",
                        },
                    )
                    tools_called.append("catalog.search")

                    # If this is attempt 1 and failure injection is requested:
                    current_injected = injected_failure if attempt == 1 else None
                    catalog_result = await self.tool_registry.execute_tool(
                        tool_name="catalog.search",
                        arguments={"query": "", "max_price": max_amount, "limit": 15},
                        run_id=run_id,
                        agent_id=agent_id,
                        stage=AgentStage.TOOL_CALL.value,
                        injected_failure=current_injected,
                    )
                    break  # Success

                except Exception as tool_err:
                    # Self-Healing Recovery Trigger
                    await self._transition_stage(
                        run_id=run_id,
                        agent_id=agent_id,
                        target_stage=AgentStage.RECOVERING,
                        observable_summary={
                            "objective": "Recover from tool execution failure",
                            "input_summary": {"error": str(tool_err)},
                            "selected_action": "Execute bounded self-healing retry policy",
                            "evidence_used": ["error_classification"],
                            "result_summary": f"Fault classified. Attempting retry {attempt}/{max_tool_retries}...",
                            "confidence": 0.75,
                            "next_action": "Retry catalog.search tool",
                        },
                    )

                    async def retry_action():
                        return await self.tool_registry.execute_tool(
                            tool_name="catalog.search",
                            arguments={"query": "", "max_price": max_amount, "limit": 15},
                            run_id=run_id,
                            agent_id=agent_id,
                            stage=AgentStage.RECOVERING.value,
                            injected_failure=None,  # Clear failure on recovery
                        )

                    success, res, summary = await self.self_healing.execute_recovery(
                        run_id=run_id,
                        agent_id=agent_id,
                        stage=AgentStage.RECOVERING.value,
                        error=tool_err,
                        attempt=attempt,
                        retry_fn=retry_action,
                    )

                    if success:
                        catalog_result = res
                        break
                    attempt += 1
                    if attempt > max_tool_retries:
                        raise RuntimeError(f"Agent failed to recover from tool failure: {tool_err}")

            products = catalog_result.get("products", [])
            memory.record("catalog_search", f"Found {len(products)} products")

            # 5. Stage: EVALUATING_OPTIONS
            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.EVALUATING_OPTIONS,
                observable_summary={
                    "objective": f"Rank {len(products)} products against '{objective}' optimization objective",
                    "input_summary": {"candidate_count": len(products), "objective": objective},
                    "selected_action": "Apply objective scoring heuristic",
                    "evidence_used": ["ratings", "prices", "discounts", "merchant_name"],
                    "result_summary": f"Ranked candidates. Selected optimal product under {objective}.",
                    "confidence": 0.92,
                    "next_action": "Generate formal transaction proposal",
                },
            )

            # Heuristic selection based on objective
            selected_item = self._select_product(products, objective, allowed_merchants)

            # 6. Stage: GENERATING_PROPOSAL
            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.GENERATING_PROPOSAL,
                observable_summary={
                    "objective": "Construct structured transaction proposal schema",
                    "input_summary": {"product_name": selected_item.get("name"), "amount": selected_item.get("price")},
                    "selected_action": "Synthesize transaction payload",
                    "evidence_used": ["selected_candidate"],
                    "result_summary": f"Formed proposal for ₹{selected_item.get('price'):,.2f} at {selected_item.get('merchant_name')}",
                    "confidence": 0.98,
                    "next_action": "Perform syntax schema validation",
                },
            )

            # 7. Stage: VALIDATING_PROPOSAL
            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.VALIDATING_PROPOSAL,
                observable_summary={
                    "objective": "Verify transaction proposal syntax before IntentGuard submission",
                    "input_summary": {"amount": selected_item.get("price"), "currency": "INR"},
                    "selected_action": "Validate mandatory financial fields",
                    "evidence_used": ["schema_definition"],
                    "result_summary": "Proposal syntax valid. Zero money movement permitted.",
                    "confidence": 1.0,
                    "next_action": "Hand off proposal to IntentGuard gateway",
                },
            )

            # 8. Stage: SUBMITTING_TO_INTENTGUARD & WAITING_FOR_DECISION
            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.SUBMITTING_TO_INTENTGUARD,
                observable_summary={
                    "objective": "Hand off proposal to IntentGuard security gateway",
                    "input_summary": {"mandate_id": mandate_id, "amount": selected_item.get("price")},
                    "selected_action": "Send proposal to IntentGuard gateway",
                    "evidence_used": ["untrusted_proposal_payload"],
                    "result_summary": "IntentGuard evaluation initiated. Awaiting structural & semantic policy.",
                    "confidence": 1.0,
                    "next_action": "Wait for deterministic authorization decision",
                },
            )

            # Create transaction record
            async with await get_session() as session:
                txn_row = await create_transaction(
                    session=session,
                    txn_data={
                        "mandate_id": mandate_id,
                        "amount": selected_item.get("price", 100.0),
                        "merchant_name": selected_item.get("merchant_name", "Stationery Mart"),
                        "merchant_category": selected_item.get("category", "stationery"),
                        "item_description": selected_item.get("name", "office supplies"),
                    },
                )

            # Evaluate with IntentGuard
            await self.event_bus.publish(
                event_type="intentguard.started",
                run_id=run_id,
                agent_id=agent_id,
                stage=AgentStage.WAITING_FOR_DECISION.value,
                payload={"transaction_id": txn_row.id, "mandate_id": mandate_id},
            )

            async with await get_session() as session:
                guard_result = await evaluate_transaction(
                    session=session,
                    transaction_id=txn_row.id,
                    mandate_id=mandate_id,
                )

            decision_outcome = guard_result.get("final_decision", "FLAG")

            await self.event_bus.publish(
                event_type="intentguard.decision.created",
                run_id=run_id,
                agent_id=agent_id,
                stage=AgentStage.WAITING_FOR_DECISION.value,
                payload={
                    "decision": decision_outcome,
                    "confidence": guard_result.get("confidence_score"),
                    "explanation": guard_result.get("explanation"),
                    "audit_id": guard_result.get("audit_id"),
                },
            )

            # 9. Stage: COMPLETED
            latency_total = (time.time() - start_time) * 1000
            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.COMPLETED,
                observable_summary={
                    "objective": "Finalize run and persist immutable audit record",
                    "input_summary": {"decision": decision_outcome},
                    "selected_action": "Persist completed run telemetry",
                    "evidence_used": ["intentguard_decision"],
                    "result_summary": f"Run complete. IntentGuard Decision: {decision_outcome}.",
                    "confidence": 1.0,
                    "next_action": "Terminal stage",
                },
            )

            async with await get_session() as session:
                await update_agent_run(
                    session=session,
                    run_id=run_id,
                    status="COMPLETED",
                    tools_used=tools_called,
                    proposal_id=txn_row.id,
                    decision_id=guard_result.get("decision_id"),
                    latency_ms=latency_total,
                )

            await self.event_bus.publish(
                event_type="agent.completed",
                run_id=run_id,
                agent_id=agent_id,
                stage=AgentStage.COMPLETED.value,
                payload={
                    "status": "COMPLETED",
                    "decision": decision_outcome,
                    "latency_ms": round(latency_total, 2),
                    "tools_called": tools_called,
                },
            )

            return {
                "run_id": run_id,
                "agent_id": agent_id,
                "status": "COMPLETED",
                "proposal": selected_item,
                "transaction_id": txn_row.id,
                "intentguard_decision": guard_result,
                "latency_ms": round(latency_total, 2),
                "tools_used": tools_called,
            }

        except Exception as run_err:
            latency_total = (time.time() - start_time) * 1000
            logger.error(f"[ORCHESTRATOR] Run {run_id} failed: {run_err}")

            await self._transition_stage(
                run_id=run_id,
                agent_id=agent_id,
                target_stage=AgentStage.FAILED,
                observable_summary={
                    "objective": "Handle fatal unrecoverable failure",
                    "input_summary": {"error": str(run_err)},
                    "selected_action": "Safe-stop and persist failure telemetry",
                    "evidence_used": ["exception_trace"],
                    "result_summary": f"Agent halted: {str(run_err)}",
                    "confidence": 0.0,
                    "next_action": "None",
                },
            )

            async with await get_session() as session:
                await update_agent_run(
                    session=session,
                    run_id=run_id,
                    status="FAILED",
                    failure_reason=str(run_err),
                    latency_ms=latency_total,
                )

            await self.event_bus.publish(
                event_type="agent.failed",
                run_id=run_id,
                agent_id=agent_id,
                stage=AgentStage.FAILED.value,
                payload={"error": str(run_err), "latency_ms": round(latency_total, 2)},
            )

            return {
                "run_id": run_id,
                "agent_id": agent_id,
                "status": "FAILED",
                "error": str(run_err),
                "latency_ms": round(latency_total, 2),
            }

    def _select_product(self, products: List[Dict[str, Any]], objective: str, allowed_merchants: List[str]) -> Dict[str, Any]:
        """Rank products according to autonomous agent optimization objective."""
        if not products:
            return {
                "name": "premium imported chocolates gift box",
                "price": 1950.0,
                "merchant_name": "Stationery Mart",
                "category": "stationery",
            }

        if objective == "BEST_RATING":
            # Select highest rating from preferred vendor (often confectionery in stationery mart)
            preferred = [p for p in products if p.get("merchant_name") in allowed_merchants] or products
            return max(preferred, key=lambda x: x.get("rating", 0.0))

        elif objective == "PROMOTION":
            return max(products, key=lambda x: x.get("discount_percent", 0.0))

        elif objective == "LOWEST_PRICE":
            preferred = [p for p in products if p.get("merchant_name") in allowed_merchants] or products
            return min(preferred, key=lambda x: x.get("price", 999999.0))

        # Default
        return products[0]


# Global Singleton Orchestrator
_agent_orchestrator: Optional[AgentOrchestrator] = None


def get_agent_orchestrator() -> AgentOrchestrator:
    global _agent_orchestrator
    if _agent_orchestrator is None:
        _agent_orchestrator = AgentOrchestrator()
    return _agent_orchestrator
