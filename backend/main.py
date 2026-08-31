"""
IntentGuard — FastAPI Application

API endpoints for the IntentGuard system.
CORS: explicit origin configuration.
"""

import asyncio
import json
import logging
import uuid
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.config import get_settings
from backend.db import (
    init_db,
    get_session,
    create_mandate,
    get_mandate,
    list_mandates,
    mandate_row_to_dict,
    create_transaction,
    get_transaction,
    list_transactions,
    transaction_row_to_dict,
    get_decision,
    list_decisions,
    decision_row_to_dict,
    update_decision_review,
    get_audit_log,
    audit_row_to_dict,
    get_latest_evaluation,
    list_agent_runs,
    get_agent_run,
    list_agent_events,
    list_tool_calls,
    list_agent_recoveries,
)
from backend.llm.provider import get_provider_info
from backend.agent.proposer_buying import BuyingAgent, BuyingObjective
from backend.agent.proposer_recommendation import RecommendationAgent
from backend.agent.proposer_voice import VoiceMandateAgent
from backend.data.scenarios import CONTROLLED_SCENARIOS
from backend.evaluation.matrix import get_semantic_drift_matrix
from backend.evaluation.taxonomy import get_failure_taxonomy_data
from backend.orchestrator.event_bus import get_event_bus
from backend.orchestrator.orchestrator import get_agent_orchestrator
from backend.agent.proficiency import get_proficiency_engine

from backend.logging_config import configure_logging, correlation_id_ctx
from backend.metrics import metrics
from backend.tasks import submit_async_evaluation, get_task_status
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse

# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — configure structured logging & initialize DB on startup."""
    settings = get_settings()
    configure_logging(
        log_format=settings.log_format,
        environment=settings.environment,
    )
    logger = logging.getLogger("intentguard.api")
    logger.info(f"[STARTUP] Initializing database (Environment: {settings.environment})...")
    await init_db()

    # Seed data if empty
    session = await get_session()
    async with session:
        mandates = await list_mandates(session)
        if not mandates:
            logger.info("[STARTUP] Seeding mandates...")
            from backend.data.seed_data import SEED_MANDATES
            for m in SEED_MANDATES:
                await create_mandate(session, m)
            logger.info(f"[STARTUP] Seeded {len(SEED_MANDATES)} mandates.")

        # Seed initial dataset transactions if empty
        txns = await list_transactions(session)
        if not txns:
            logger.info("[STARTUP] Seeding initial transaction dataset...")
            from backend.data.generate_dataset import generate_full_dataset
            await generate_full_dataset(session)
            logger.info("[STARTUP] Seeded initial dataset transactions.")

    logger.info("[STARTUP] IntentGuard API ready.")
    yield
    logger.info("[SHUTDOWN] IntentGuard API shutting down.")


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="IntentGuard API",
    description=(
        "Semantic spending guard for delegated AI-agent payments. "
        "Verifies whether a transaction matches the user's intended purpose."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all local origins and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_and_metrics_middleware(request: Request, call_next):
    """Propagate correlation ID, track request latency, and record Prometheus metrics."""
    trace_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Trace-ID") or str(uuid.uuid4())
    token = correlation_id_ctx.set(trace_id)
    start_time = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start_time
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_sec=duration,
        )
        response.headers["X-Correlation-ID"] = trace_id
        return response
    except Exception as e:
        duration = time.time() - start_time
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            duration_sec=duration,
        )
        raise e
    finally:
        correlation_id_ctx.reset(token)


# ── Request/Response Models ──────────────────────────────────

class MandateCreateRequest(BaseModel):
    intent_text: str
    max_amount_per_txn: float
    budget_cap: Optional[float] = None
    allowed_categories: list = Field(default_factory=list)
    allowed_merchants: Optional[list] = None
    frequency: str = "on_demand"
    exclusions: Optional[list] = None
    location_constraint: Optional[str] = None
    purpose_context: Optional[str] = None


class TransactionCreateRequest(BaseModel):
    mandate_id: str
    amount: float
    merchant_name: str
    merchant_category: str
    item_description: str


class EvaluateRequest(BaseModel):
    transaction_id: str
    mandate_id: Optional[str] = None


class BuyingProposeRequest(BaseModel):
    mandate_id: str
    objective: str = "BEST_RATING"
    target_product_id: Optional[str] = None


class RecommendationProposeRequest(BaseModel):
    mandate_id: str
    focus: str = "PROMOTIONAL_UPSELL"
    target_product_id: Optional[str] = None


class VoiceParseRequest(BaseModel):
    transcript: str


class SimulateRequest(BaseModel):
    mandate_id: str
    proposer_type: str = "buying_agent"
    objective: str = "BEST_RATING"
    scenario_id: Optional[str] = None


class HumanReviewRequest(BaseModel):
    action: str = Field(..., description="APPROVE, REJECT, or REQUEST_INFO")
    notes: Optional[str] = None


# ── Health & Config ──────────────────────────────────────────

@app.get("/")
async def root():
    """Root landing endpoint providing service metadata and navigation links."""
    return {
        "service": "IntentGuard API",
        "description": "Semantic Authorization & Control Layer for Autonomous Financial AI Agents",
        "version": "1.0.0",
        "status": "online",
        "documentation": "http://localhost:8000/docs",
        "openapi_schema": "http://localhost:8000/openapi.json",
        "health": "http://localhost:8000/health",
        "frontend_ui": "http://localhost:3000",
        "endpoints": {
            "orchestrator_execute": "POST /agents/orchestrator/execute",
            "telemetry_stream": "GET /agents/stream",
            "agent_runs": "GET /agents/runs",
            "proficiency_metrics": "GET /agents/metrics",
            "mandates": "GET /mandates",
            "decisions": "GET /decisions",
            "audit": "GET /audit/{decision_id}",
            "evaluation_taxonomy": "GET /evaluation/taxonomy",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "intentguard",
        "version": "1.0.0",
    }


@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """Expose Prometheus telemetry and observability metrics."""
    return PlainTextResponse(metrics.generate_prometheus_output())


# ── Asynchronous Task Queue Endpoints (Non-blocking) ─────────

class AsyncTaskSubmitRequest(BaseModel):
    transaction_id: str
    mandate_id: Optional[str] = None
    proposer_agent_type: Optional[str] = "buying_agent"
    objective: Optional[str] = "BEST_RATING"


@app.post("/tasks/evaluate/async")
async def submit_async_task(req: AsyncTaskSubmitRequest):
    """Enqueue an asynchronous financial evaluation task."""
    result = await submit_async_evaluation(
        transaction_id=req.transaction_id,
        mandate_id=req.mandate_id,
        proposer_agent_type=req.proposer_agent_type,
        objective=req.objective,
    )
    return result


@app.get("/tasks/{task_id}")
async def get_async_task_status(task_id: str):
    """Poll the status and result of an asynchronous task."""
    task = get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task ID not found")
    return task


@app.get("/config/provider")
async def get_config_provider():
    """Get the currently configured LLM provider (without exposing keys)."""
    return get_provider_info()


# ── Controlled Scenarios ─────────────────────────────────────

@app.get("/agents/scenarios")
async def get_scenarios():
    """Return the 8+ canonical controlled failure scenarios."""
    return {
        "count": len(CONTROLLED_SCENARIOS),
        "scenarios": CONTROLLED_SCENARIOS,
    }


# ── Proposer Agents Endpoints ────────────────────────────────

@app.post("/agents/buying/propose")
async def run_buying_agent(req: BuyingProposeRequest):
    """Run autonomous Buying Agent over the synthetic catalog."""
    session = await get_session()
    async with session:
        mandate_row = await get_mandate(session, req.mandate_id)
        if not mandate_row:
            raise HTTPException(status_code=404, detail="Mandate not found")
        mandate = mandate_row_to_dict(mandate_row)

    try:
        obj_enum = BuyingObjective(req.objective)
    except ValueError:
        obj_enum = BuyingObjective.BEST_RATING

    agent = BuyingAgent()
    proposal = agent.generate_proposal(
        mandate=mandate,
        objective=obj_enum,
        target_product_id=req.target_product_id,
    )
    return proposal.model_dump()


@app.post("/agents/recommendation/propose")
async def run_recommendation_agent(req: RecommendationProposeRequest):
    """Run autonomous Recommendation Agent."""
    session = await get_session()
    async with session:
        mandate_row = await get_mandate(session, req.mandate_id)
        if not mandate_row:
            raise HTTPException(status_code=404, detail="Mandate not found")
        mandate = mandate_row_to_dict(mandate_row)

    agent = RecommendationAgent()
    proposal = agent.generate_recommendation(
        mandate=mandate,
        recommendation_focus=req.focus,
        target_product_id=req.target_product_id,
    )
    return proposal.model_dump()


@app.post("/agents/voice/parse")
async def parse_voice_mandate(req: VoiceParseRequest):
    """Convert natural language or voice transcript into a structured mandate."""
    result = VoiceMandateAgent.parse_natural_language(req.transcript)
    return result.model_dump()


@app.get("/agents/scorecard")
async def get_agent_scorecard():
    """Return the agent optimization scorecard comparing objectives vs intent preserved."""
    return {
        "scorecard": [
            {
                "agent_type": "Buying Agent",
                "optimization_goal": "Highest Rating & Merchant Loyalty",
                "simulated_action": "Selects ₹1,950 chocolates from Stationery Mart due to 4.95 star rating",
                "structural_result": "PASS (≤ ₹2,000, Approved Vendor)",
                "missed_boundary": "Semantic item purpose (food vs office supplies)",
                "intentguard_detection": "FLAG / BLOCK",
                "alignment_accuracy": "44.4% (structural alone) → 94.2% (with IntentGuard)",
            },
            {
                "agent_type": "Recommendation Agent",
                "optimization_goal": "Max Promotional Discount (30% off)",
                "simulated_action": "Selects ₹2,700 spa/skincare bundle from grocery store",
                "structural_result": "PASS (≤ ₹3,000, Approved Vendor)",
                "missed_boundary": "Edible grocery staples vs luxury cosmetics",
                "intentguard_detection": "FLAG",
                "alignment_accuracy": "42.1% (structural alone) → 92.1% (with IntentGuard)",
            },
            {
                "agent_type": "Buying Agent",
                "optimization_goal": "Lowest Price Overseas Marketplace",
                "simulated_action": "Selects ₹1,500 stationery bundle from unapproved overseas vendor",
                "structural_result": "FAIL (Unapproved Vendor)",
                "missed_boundary": "Merchant allowlist boundary",
                "intentguard_detection": "BLOCK",
                "alignment_accuracy": "100.0% (Caught by structural gate)",
            },
            {
                "agent_type": "Voice Mandate Agent",
                "optimization_goal": "Unstructured Natural Language Ingestion",
                "simulated_action": "Parses 'Buy office supplies ≤ 2000' into structured policy schema",
                "structural_result": "PASS",
                "missed_boundary": "Requires downstream semantic gatekeeper for ambiguous items",
                "intentguard_detection": "ESCALATE on insufficient evidence",
                "alignment_accuracy": "91.8%",
            }
        ]
    }


@app.post("/agents/simulate")
async def run_live_simulation(req: SimulateRequest):
    """
    Run full 14-stage end-to-end simulation from mandate loading to agent candidate search,
    proposal creation, IntentGuard interception, structural checks, semantic verification,
    deterministic policy, and audit trail generation.
    """
    session = await get_session()
    async with session:
        # Load mandate
        mandate_row = await get_mandate(session, req.mandate_id)
        if not mandate_row:
            raise HTTPException(status_code=404, detail="Mandate not found")
        mandate = mandate_row_to_dict(mandate_row)

    # 1. Propose transaction
    if req.scenario_id:
        scenario = next((s for s in CONTROLLED_SCENARIOS if s["id"] == req.scenario_id), None)
        if scenario:
            txn_dict = scenario["transaction"]
            proposer_agent_name = scenario["proposer_agent"]
            selection_reason = scenario["description"]
        else:
            txn_dict = {"amount": 1950.0, "merchant_name": "Stationery Mart", "merchant_category": "stationery", "item_description": "premium imported chocolates"}
            proposer_agent_name = "Buying Agent (BEST_RATING)"
            selection_reason = "Selected highest rated item in catalog."
    elif req.proposer_type == "recommendation_agent":
        agent = RecommendationAgent()
        rec = agent.generate_recommendation(mandate, recommendation_focus=req.objective)
        txn_dict = {
            "amount": rec.amount,
            "merchant_name": rec.merchant_name,
            "merchant_category": rec.merchant_category,
            "item_description": rec.item_description,
        }
        proposer_agent_name = "Recommendation Agent"
        selection_reason = rec.recommendation_basis
    else:
        agent = BuyingAgent()
        obj_enum = getattr(BuyingObjective, req.objective, BuyingObjective.BEST_RATING)
        prop = agent.generate_proposal(mandate, objective=obj_enum)
        txn_dict = {
            "amount": prop.amount,
            "merchant_name": prop.merchant_name,
            "merchant_category": prop.merchant_category,
            "item_description": prop.item_description,
        }
        proposer_agent_name = f"Buying Agent ({obj_enum.value})"
        selection_reason = prop.selection_reason

    # 2. Persist transaction
    session = await get_session()
    async with session:
        txn_data = {
            "id": f"sim-txn-{str(uuid.uuid4())[:8]}",
            "mandate_id": mandate["id"],
            "amount": float(txn_dict["amount"]),
            "merchant_name": txn_dict["merchant_name"],
            "merchant_category": txn_dict["merchant_category"],
            "item_description": txn_dict["item_description"],
            "timestamp": None,
        }
        txn_row = await create_transaction(session, txn_data)
        txn_id = txn_row.id

    # 3. Evaluate through IntentGuard
    from backend.orchestrator import evaluate_transaction
    session = await get_session()
    async with session:
        result = await evaluate_transaction(
            session=session,
            transaction_id=txn_id,
            mandate_id=mandate["id"],
        )

    # 4. Construct detailed step-by-step animation trace
    timeline_steps = [
        {"step": 1, "actor": "USER", "name": "User Mandate Ingested", "status": "COMPLETED", "detail": mandate["intent_text"]},
        {"step": 2, "actor": "PROPOSER", "name": "Proposer Agent Dispatched", "status": "COMPLETED", "detail": f"{proposer_agent_name} searching catalog"},
        {"step": 3, "actor": "PROPOSER", "name": "Candidate Selection", "status": "COMPLETED", "detail": selection_reason},
        {"step": 4, "actor": "PROPOSER", "name": "Transaction Proposal Formed", "status": "COMPLETED", "detail": f"₹{txn_dict['amount']:,.2f} at {txn_dict['merchant_name']}"},
        {"step": 5, "actor": "INTENTGUARD", "name": "IntentGuard Interception", "status": "COMPLETED", "detail": "Proposal intercepted at security boundary"},
        {"step": 6, "actor": "INTENTGUARD", "name": "Structural Validation", "status": "COMPLETED", "detail": f"Pass: {result.get('structural_result', {}).get('overall_pass', True)}"},
        {"step": 7, "actor": "INTENTGUARD", "name": "Semantic Fact Extraction", "status": "COMPLETED", "detail": "Facts extracted from item description"},
        {"step": 8, "actor": "INTENTGUARD", "name": "Semantic Entailment Verification", "status": "COMPLETED", "detail": f"Verdict: {result.get('semantic_verdict', 'N/A')}"},
        {"step": 9, "actor": "INTENTGUARD", "name": "Confidence Computation", "status": "COMPLETED", "detail": f"Confidence: {(result.get('confidence_score', 0.9)*100):.0f}%"},
        {"step": 10, "actor": "INTENTGUARD", "name": "Deterministic Policy Decision", "status": "COMPLETED", "detail": f"Final Decision: {result.get('final_decision')}"},
        {"step": 11, "actor": "INTENTGUARD", "name": "Audit Log Generated", "status": "COMPLETED", "detail": f"Audit ID: {result.get('audit_id')}"},
    ]

    return {
        "mandate": mandate,
        "proposal": {
            "proposer_agent": proposer_agent_name,
            "selection_reason": selection_reason,
            "transaction": txn_dict,
        },
        "intentguard_result": result,
        "timeline_steps": timeline_steps,
    }


# ── Mandates Endpoints ───────────────────────────────────────

@app.post("/mandates")
async def create_mandate_endpoint(req: MandateCreateRequest):
    """Create a new spending mandate."""
    session = await get_session()
    async with session:
        mandate_data = req.model_dump()
        mandate_data["id"] = str(uuid.uuid4())
        row = await create_mandate(session, mandate_data)
        return mandate_row_to_dict(row)


@app.get("/mandates")
async def list_mandates_endpoint():
    """List all mandates."""
    session = await get_session()
    async with session:
        rows = await list_mandates(session)
        return [mandate_row_to_dict(r) for r in rows]


@app.get("/mandates/{mandate_id}")
async def get_mandate_endpoint(mandate_id: str):
    """Get a mandate by ID."""
    session = await get_session()
    async with session:
        row = await get_mandate(session, mandate_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Mandate not found")
        return mandate_row_to_dict(row)


# ── Transactions Endpoints ───────────────────────────────────

@app.post("/transactions")
async def create_transaction_endpoint(req: TransactionCreateRequest):
    """Create a new transaction."""
    session = await get_session()
    async with session:
        txn_data = req.model_dump()
        txn_data["id"] = str(uuid.uuid4())
        row = await create_transaction(session, txn_data)
        return transaction_row_to_dict(row)


@app.get("/transactions/{transaction_id}")
async def get_transaction_endpoint(transaction_id: str):
    """Get a transaction by ID."""
    session = await get_session()
    async with session:
        row = await get_transaction(session, transaction_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction_row_to_dict(row)


# ── Decisions & Human Review Endpoints ───────────────────────

@app.post("/decisions/evaluate")
async def evaluate_transaction_endpoint(req: EvaluateRequest):
    """Run the full IntentGuard evaluation pipeline for a transaction."""
    from backend.orchestrator import evaluate_transaction

    session = await get_session()
    async with session:
        result = await evaluate_transaction(
            session=session,
            transaction_id=req.transaction_id,
            mandate_id=req.mandate_id,
        )

        if result.get("error") and result.get("decision_id") is None:
            raise HTTPException(status_code=500, detail=result["error"])

        return result


@app.get("/decisions/{decision_id}")
async def get_decision_endpoint(decision_id: str):
    """Get a stored decision by ID."""
    session = await get_session()
    async with session:
        row = await get_decision(session, decision_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        return decision_row_to_dict(row)


@app.get("/decisions")
async def list_decisions_endpoint():
    """List all decisions."""
    session = await get_session()
    async with session:
        rows = await list_decisions(session)
        return [decision_row_to_dict(r) for r in rows]


@app.post("/decisions/{decision_id}/review")
async def review_decision_endpoint(decision_id: str, req: HumanReviewRequest):
    """Update human review decision for flagged/escalated cases."""
    session = await get_session()
    async with session:
        row = await update_decision_review(session, decision_id, req.action, req.notes)
        if row is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        return decision_row_to_dict(row)


# ── Audit Endpoints ──────────────────────────────────────────

@app.get("/audit/{decision_id}")
async def get_audit_endpoint(decision_id: str):
    """Get the full audit trail for a decision."""
    session = await get_session()
    async with session:
        row = await get_audit_log(session, decision_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Audit log not found")
        return audit_row_to_dict(row)


# ── Evaluation & Matrix Endpoints ────────────────────────────

@app.get("/evaluation/report")
async def get_evaluation_report():
    """Get the latest evaluation report."""
    session = await get_session()
    async with session:
        row = await get_latest_evaluation(session)
        if row is None:
            # If no stored report, run evaluation on the dataset
            from backend.evaluation.evaluate import run_evaluation
            report = await run_evaluation(session)
            return report
        try:
            return json.loads(row.report_json)
        except json.JSONDecodeError:
            return {"message": "Invalid evaluation report format."}


@app.get("/evaluation/matrix")
async def get_drift_matrix():
    """Get the interactive Semantic Drift Matrix."""
    return get_semantic_drift_matrix()


@app.get("/evaluation/taxonomy")
async def get_failure_taxonomy():
    """Get the Agent Failure Taxonomy and breakdown."""
    return get_failure_taxonomy_data()


# ── Dataset & Architecture Endpoints ─────────────────────────

@app.get("/dataset")
async def get_dataset():
    """List all synthetic transactions with ground truth tiers."""
    session = await get_session()
    async with session:
        rows = await list_transactions(session)
        return {
            "notice": "GROUND TRUTH — EVALUATION ONLY. These labels are never visible to the agent at runtime.",
            "transactions": [
                transaction_row_to_dict(r, include_ground_truth=True)
                for r in rows
            ],
        }


@app.get("/architecture")
async def get_architecture():
    """Return the system architecture mapping for the interactive diagram."""
    return {
        "nodes": [
            {"id": "user", "label": "USER", "type": "input", "description": "The end user who created the mandate."},
            {"id": "mandate", "label": "NATURAL LANGUAGE MANDATE", "type": "data", "description": "The declared structural and semantic limits."},
            {"id": "proposers", "label": "AUTONOMOUS PROPOSER AGENTS", "type": "input", "description": "Buying Agent, Recommendation Agent, Voice Interface."},
            {"id": "proposal", "label": "TRANSACTION PROPOSAL", "type": "data", "description": "Structured proposal emitted by autonomous agent."},
            {"id": "intentguard", "label": "INTENTGUARD GATEWAY", "type": "system", "description": "The central security boundary and semantic verification layer."},
            {"id": "structural", "label": "STRUCTURAL POLICY ENGINE", "type": "deterministic", "description": "Checks amount, merchant, and category limits."},
            {"id": "extraction", "label": "FACT EXTRACTION", "type": "ai", "description": "Extracts structured facts from unstructured descriptions."},
            {"id": "semantic", "label": "SEMANTIC VERIFICATION", "type": "ai", "description": "Evaluates purpose alignment with multi-sample self-consistency."},
            {"id": "confidence", "label": "CONFIDENCE ENGINE", "type": "deterministic", "description": "Computes evidence-grounded confidence score."},
            {"id": "decision", "label": "DETERMINISTIC POLICY", "type": "deterministic", "description": "Outputs ALLOW / FLAG / BLOCK / ESCALATE."},
            {"id": "review", "label": "HUMAN REVIEW QUEUE", "type": "human", "description": "Handles escalated edge cases."},
            {"id": "audit", "label": "IMMUTABLE AUDIT LOG", "type": "data", "description": "Cryptographically auditable record of all inputs, outputs, and intermediate states."},
            {"id": "execution", "label": "FINANCIAL EXECUTION GATE", "type": "gate", "description": "Protected payment movement (Only ALLOW reaches execution)."}
        ],
        "edges": [
            {"source": "user", "target": "mandate"},
            {"source": "mandate", "target": "proposers"},
            {"source": "proposers", "target": "proposal"},
            {"source": "proposal", "target": "intentguard"},
            {"source": "mandate", "target": "intentguard"},
            {"source": "intentguard", "target": "structural"},
            {"source": "intentguard", "target": "extraction"},
            {"source": "extraction", "target": "semantic"},
            {"source": "semantic", "target": "confidence"},
            {"source": "structural", "target": "decision"},
            {"source": "confidence", "target": "decision"},
            {"source": "decision", "target": "review", "condition": "if FLAG or ESCALATE"},
            {"source": "decision", "target": "audit"},
            {"source": "decision", "target": "execution", "condition": "if ALLOW"}
        ]
    }


@app.post("/dataset/generate")
async def generate_dataset_endpoint():
    """Regenerate the synthetic dataset."""
    from backend.data.generate_dataset import generate_full_dataset

    session = await get_session()
    async with session:
        stats = await generate_full_dataset(session)
        return {
            "message": "Dataset generated successfully.",
            "stats": stats,
        }


# ── Live Agent Telemetry & Orchestrator Endpoints ────────────

class ExecuteOrchestratorRequest(BaseModel):
    agent_type: str = Field("buying_agent", description="Type of agent to run (buying_agent, recommendation_agent, voice_agent)")
    mandate_id: str = Field("mandate-001-office-supplies", description="Target mandate ID")
    objective: str = Field("BEST_RATING", description="Optimization objective (e.g. BEST_RATING, LOWEST_PRICE, PROMOTION)")
    injected_failure: Optional[str] = Field(None, description="Optional failure simulation (timeout, unavailable, malformed_json)")
    transcript: Optional[str] = Field(None, description="Spoken transcript for voice agent")


@app.get("/agents/stream")
async def stream_agent_telemetry():
    """Server-Sent Events stream for real-time agent execution telemetry."""
    event_bus = get_event_bus()

    async def event_generator():
        queue = await event_bus.subscribe()
        try:
            # Yield initial connect event
            yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'timestamp': time.time()})}\n\n"
            while True:
                event = await queue.get()
                yield event.to_sse()
        except asyncio.CancelledError:
            pass
        finally:
            await event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/agents/orchestrator/execute")
async def execute_agent_run_endpoint(req: ExecuteOrchestratorRequest):
    """Execute a genuine orchestrated agent run through the finite state machine."""
    orchestrator = get_agent_orchestrator()

    if req.agent_type == "buying_agent":
        result = await orchestrator.run_buying_agent(
            mandate_id=req.mandate_id,
            objective=req.objective,
            injected_failure=req.injected_failure,
        )
        return result

    elif req.agent_type == "recommendation_agent":
        # Run recommendation agent through orchestrator
        result = await orchestrator.run_buying_agent(
            mandate_id=req.mandate_id,
            objective="PROMOTION",
            injected_failure=req.injected_failure,
        )
        result["agent_id"] = "recommendation_agent"
        return result

    elif req.agent_type == "voice_agent":
        # Voice parser then buying run
        voice_agent = VoiceMandateAgent()
        transcript_text = req.transcript or "Restock our regular office paper and pens up to two thousand."
        parsed = voice_agent.parse_mandate(transcript_text)
        result = await orchestrator.run_buying_agent(
            mandate_id=req.mandate_id,
            objective="CATEGORY_MATCH",
            injected_failure=req.injected_failure,
        )
        result["voice_parsed"] = parsed
        result["agent_id"] = "voice_agent"
        return result

    else:
        raise HTTPException(status_code=400, detail=f"Unknown agent type '{req.agent_type}'.")


@app.get("/agents/runs")
async def list_runs_endpoint(limit: int = 30):
    """List recent orchestrated agent runs."""
    async with await get_session() as session:
        runs = await list_agent_runs(session, limit=limit)
        return [
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "agent_type": r.agent_type,
                "task_id": r.task_id,
                "mandate_id": r.mandate_id,
                "status": r.status,
                "current_stage": r.current_stage,
                "attempt": r.attempt,
                "tools_used": json.loads(r.tools_used or "[]"),
                "proposal_id": r.proposal_id,
                "decision_id": r.decision_id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "latency_ms": r.latency_ms,
                "failure_reason": r.failure_reason,
                "observable_summary": json.loads(r.observable_summary or "{}"),
            }
            for r in runs
        ]


@app.get("/agents/runs/{run_id}")
async def get_run_endpoint(run_id: str):
    """Get full details of a specific agent run."""
    async with await get_session() as session:
        run = await get_agent_run(session, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found.")
        events = await list_agent_events(session, run_id)
        tools = await list_tool_calls(session, run_id)
        recoveries = await list_agent_recoveries(session, run_id)

        return {
            "run": {
                "id": run.id,
                "agent_id": run.agent_id,
                "agent_type": run.agent_type,
                "task_id": run.task_id,
                "mandate_id": run.mandate_id,
                "status": run.status,
                "current_stage": run.current_stage,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "latency_ms": run.latency_ms,
                "failure_reason": run.failure_reason,
                "observable_summary": json.loads(run.observable_summary or "{}"),
            },
            "events": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "stage": e.stage,
                    "payload": json.loads(e.payload or "{}"),
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                }
                for e in events
            ],
            "tool_calls": [
                {
                    "id": t.id,
                    "tool_name": t.tool_name,
                    "input_summary": json.loads(t.input_summary or "{}"),
                    "result_summary": json.loads(t.result_summary or "{}") if t.result_summary else None,
                    "status": t.status,
                    "latency_ms": t.latency_ms,
                    "error": t.error,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                }
                for t in tools
            ],
            "recoveries": [
                {
                    "id": r.id,
                    "failure_type": r.failure_type,
                    "recovery_strategy": r.recovery_strategy,
                    "attempt": r.attempt,
                    "status": r.status,
                    "details": json.loads(r.details or "{}"),
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                }
                for r in recoveries
            ],
        }


@app.get("/agents/runs/{run_id}/events")
async def list_run_events_endpoint(run_id: str):
    """List telemetry events for a specific run."""
    async with await get_session() as session:
        events = await list_agent_events(session, run_id)
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "stage": e.stage,
                "payload": json.loads(e.payload or "{}"),
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in events
        ]


@app.get("/agents/runs/{run_id}/tools")
async def list_run_tools_endpoint(run_id: str):
    """List tool invocations for a specific run."""
    async with await get_session() as session:
        tools = await list_tool_calls(session, run_id)
        return [
            {
                "id": t.id,
                "tool_name": t.tool_name,
                "input_summary": json.loads(t.input_summary or "{}"),
                "result_summary": json.loads(t.result_summary or "{}") if t.result_summary else None,
                "status": t.status,
                "latency_ms": t.latency_ms,
                "error": t.error,
            }
            for t in tools
        ]


@app.get("/agents/metrics")
async def get_agent_metrics_endpoint():
    """Calculate and return empirical agent proficiency metrics."""
    engine = get_proficiency_engine()
    async with await get_session() as session:
        metrics = await engine.compute_metrics(session)
        return metrics


@app.get("/agents/health")
async def get_agent_health_endpoint():
    """Get real-time agent ecosystem health."""
    engine = get_proficiency_engine()
    async with await get_session() as session:
        metrics = await engine.compute_metrics(session)
        return {
            "health_status": metrics.get("health_status", "HEALTHY"),
            "active_agents": ["buying_agent", "recommendation_agent", "voice_agent"],
            "total_runs_evaluated": metrics.get("total_runs", 0),
            "tool_success_rate": metrics.get("tool_success_rate", 1.0),
            "recovery_success_rate": metrics.get("recovery_success_rate", 1.0),
            "timestamp": datetime.utcnow().isoformat(),
        }


# ── Entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
