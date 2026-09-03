"""
IntentGuard — Architectural Boundary & Import AST Enforcement Tests

Phase 1 Architectural Invariants:
1. Proposer agents must NEVER import payment execution or Razorpay modules.
2. Proposer agents must NEVER import or call the deterministic decision engine directly.
3. Self-healing modules must NEVER import payment execution or mandate-modifying routes.
4. Deterministic decision engine must NEVER import LLM providers (pure deterministic logic).
5. All proposals produced by autonomous agents must be untrusted Proposal objects, never authorizations.
"""

import ast
from pathlib import Path
import pytest
from backend.policy.decision import decide
from backend.models import FinalDecision


BACKEND_DIR = Path(__file__).resolve().parent.parent


def get_imported_module_names(file_path: Path) -> set:
    """Parse a python file with AST and return all top-level imported module names."""
    if not file_path.exists():
        return set()
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def test_proposer_agents_never_import_execution():
    """Proposer agents must NOT have access to Razorpay or payment execution modules."""
    proposer_files = [
        BACKEND_DIR / "agent" / "proposer.py",
        BACKEND_DIR / "agent" / "buying_agent.py",
        BACKEND_DIR / "agent" / "recommendation_agent.py",
        BACKEND_DIR / "agent" / "travel_agent.py",
    ]

    forbidden_tokens = ["execution", "razorpay", "backend.execution"]

    for file_path in proposer_files:
        if not file_path.exists():
            continue
        imported = get_imported_module_names(file_path)
        for mod in imported:
            for forbidden in forbidden_tokens:
                assert forbidden not in mod, (
                    f"ARCHITECTURAL VIOLATION in {file_path.name}: "
                    f"proposer agent imports forbidden execution module '{mod}'"
                )


def test_proposer_agents_never_import_decision_engine():
    """Proposer agents must NOT import or call the internal deterministic decision engine."""
    proposer_files = [
        BACKEND_DIR / "agent" / "proposer.py",
        BACKEND_DIR / "agent" / "buying_agent.py",
        BACKEND_DIR / "agent" / "recommendation_agent.py",
        BACKEND_DIR / "agent" / "travel_agent.py",
    ]

    for file_path in proposer_files:
        if not file_path.exists():
            continue
        imported = get_imported_module_names(file_path)
        for mod in imported:
            assert "backend.policy.decision" not in mod, (
                f"ARCHITECTURAL VIOLATION in {file_path.name}: "
                f"proposer agent directly imports decision engine '{mod}'"
            )


def test_self_healing_never_imports_execution():
    """Self-healing module must NOT import or call payment execution."""
    healing_file = BACKEND_DIR / "agent" / "self_healing.py"
    assert healing_file.exists()

    imported = get_imported_module_names(healing_file)
    for mod in imported:
        assert "execution" not in mod and "razorpay" not in mod, (
            f"ARCHITECTURAL VIOLATION in self_healing.py: "
            f"imports forbidden execution module '{mod}'"
        )


def test_decision_engine_is_pure_deterministic():
    """Deterministic decision engine must NEVER import LLM providers or network libraries."""
    decision_file = BACKEND_DIR / "policy" / "decision.py"
    assert decision_file.exists()

    imported = get_imported_module_names(decision_file)
    forbidden_in_decision = ["backend.llm", "google.genai", "openai", "requests", "httpx", "urllib"]

    for mod in imported:
        for forbidden in forbidden_in_decision:
            assert forbidden not in mod, (
                f"ARCHITECTURAL VIOLATION: Pure deterministic decision engine "
                f"imports non-deterministic/network module '{mod}'"
            )


def test_llm_cannot_override_structural_failure():
    """Even if semantic layer emits FIT with 100% confidence, structural failure forces BLOCK."""
    decision = decide(
        structural_pass=False,
        majority_verdict="fit",
        confidence_score=1.0,
        structural_failure_reasons=["Exceeded max amount per transaction"],
    )
    assert decision["final_decision"] == FinalDecision.BLOCK.value
    assert "hard constraint" in decision["reasoning"].lower()


def test_low_confidence_fit_escalates_not_allows():
    """A semantic 'fit' with low confidence must ESCALATE, never ALLOW."""
    decision = decide(
        structural_pass=True,
        majority_verdict="fit",
        confidence_score=0.35,  # Below threshold
    )
    assert decision["final_decision"] == FinalDecision.ESCALATE.value
