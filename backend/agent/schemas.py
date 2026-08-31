"""
IntentGuard — Agent Tool Schemas

JSON input/output schemas for all agent tools.
Each tool has: name, description, input schema, output schema.
"""

TOOL_REGISTRY = {
    "get_mandate": {
        "name": "get_mandate",
        "description": "Retrieve the spending mandate by ID from the database.",
        "input_schema": {"mandate_id": "string"},
        "output_schema": {"mandate": "Mandate object"},
    },
    "get_transaction": {
        "name": "get_transaction",
        "description": "Retrieve the transaction by ID from the database.",
        "input_schema": {"transaction_id": "string"},
        "output_schema": {"transaction": "Transaction object (without ground truth)"},
    },
    "get_merchant_context": {
        "name": "get_merchant_context",
        "description": "Retrieve contextual information about the merchant.",
        "input_schema": {"merchant_name": "string", "merchant_category": "string"},
        "output_schema": {"merchant_info": "dict with known merchant details"},
    },
    "get_product_context": {
        "name": "get_product_context",
        "description": "Retrieve contextual information about the product/item.",
        "input_schema": {"item_description": "string"},
        "output_schema": {"product_info": "dict with product category hints"},
    },
    "check_hard_constraints": {
        "name": "check_hard_constraints",
        "description": "Run deterministic hard constraint checks against the mandate.",
        "input_schema": {"mandate": "Mandate", "transaction": "Transaction"},
        "output_schema": {"structural_result": "StructuralResult with per-check breakdown"},
    },
    "extract_structured_facts": {
        "name": "extract_structured_facts",
        "description": "Extract structured facts from transaction using LLM (Call 1).",
        "input_schema": {"transaction": "Transaction", "mandate_intent": "string"},
        "output_schema": {"extracted_facts": "ExtractedFacts dict"},
    },
    "semantic_compare": {
        "name": "semantic_compare",
        "description": "Run entailment-style semantic judgment with self-consistency (LLM Call 2).",
        "input_schema": {
            "mandate_intent": "string",
            "allowed_categories": "list[string]",
            "extracted_facts": "dict",
            "transaction": "Transaction",
        },
        "output_schema": {"semantic_judgment": "SemanticJudgmentResult"},
    },
    "compute_confidence": {
        "name": "compute_confidence",
        "description": "Compute deterministic confidence score from evidence.",
        "input_schema": {
            "structural_result": "StructuralResult",
            "semantic_verdicts": "list[string]",
            "extracted_facts": "dict",
            "txn_amount": "float",
            "mandate_max_amount": "float",
        },
        "output_schema": {"confidence": "dict with score and breakdown"},
    },
    "request_user_confirmation": {
        "name": "request_user_confirmation",
        "description": "Request human review for ambiguous or escalated cases.",
        "input_schema": {"decision_id": "string", "reason": "string"},
        "output_schema": {"escalation_logged": "bool"},
    },
    "record_decision": {
        "name": "record_decision",
        "description": "Record the final decision to the database.",
        "input_schema": {"decision": "Decision"},
        "output_schema": {"decision_id": "string"},
    },
    "audit_decision": {
        "name": "audit_decision",
        "description": "Write the complete audit trail for the decision.",
        "input_schema": {"audit_log": "AuditLog"},
        "output_schema": {"audit_id": "string"},
    },
}
