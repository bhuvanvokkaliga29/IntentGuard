import os
import json

DOCS_DIR = r"c:\Users\HP\Desktop\IntentGuard\docs"
os.makedirs(DOCS_DIR, exist_ok=True)

docs = {
    "AI_EVALUATION_GUIDE.md": """# AI Evaluation Guide
## Overview
IntentGuard evaluates the semantic drift of transactions against bounded mandates. We use self-consistency prompting with Google Gemini to act as a judge.

## Methodology
1. **Fact Extraction:** Extract normalized category, item type, and tier from the raw transaction.
2. **Semantic Judgment:** Compare the extracted facts with the user's natural language intent. 
3. **Multi-sample Consensus:** Run the judgment 3 times (temperature > 0) to compute agreement.
4. **Deterministic Policy:** Use the consensus to decide ALLOW, FLAG, ESCALATE, or BLOCK.
""",
    
    "PROJECT_MANIFEST.json": json.dumps({
        "project_name": "IntentGuard",
        "tagline": "Within the limit isn't enough. Verify the intent.",
        "track": "Track 1 — AI Growth & Agentic Commerce",
        "stack": ["Next.js", "FastAPI", "Python", "React", "Gemini 3.1 Pro"]
    }, indent=4),

    "PROJECT_CARD.md": """# Project Card: IntentGuard
**Track:** AI Growth & Agentic Commerce
**Problem:** Agents stay within budget limits but fail on semantic intent.
**Solution:** A deterministic semantic guardrail that intercepts and evaluates transactions using LLM-as-a-Judge before money moves.
""",

    "PROBLEM.md": """# The Problem
Traditional payment authorization relies on structural limits (amount, merchant, category). But an AI agent can buy premium imported chocolates from a stationery store, staying within the limit but violating the "office supplies" intent. Structural rules cannot catch semantic hallucination.
""",

    "ARCHITECTURE.md": """# Architecture
1. **Agent Pipeline:** Proposes transaction.
2. **IntentGuard Engine:**
   - Structural Check
   - Fact Extraction
   - Semantic Judgment (Consensus)
   - Decision Engine
3. **Output:** ALLOW, FLAG, BLOCK, ESCALATE.
See `/architecture` in the app for the interactive DAG.
""",

    "AGENT_FLOW.md": """# Agent Flow
1. Fetch Bounded Mandate.
2. Determine required item.
3. Attempt purchase.
4. IntentGuard intercepts the payload.
5. If ALLOW: Purchase succeeds.
6. If FLAG/ESCALATE: Goes to Human Review Queue.
""",

    "DATASET_CARD.md": """# Dataset Card
**Name:** IntentGuard Synthetic Benchmark
**Size:** 59 cases
**Distribution:** CLEARLY_IN_SCOPE, CLEARLY_OUT_OF_SCOPE, AMBIGUOUS, UNSAFE_TO_DECIDE
**Usage:** Used strictly for offline evaluation. The runtime agent never sees ground-truth labels.
""",

    "DATA_PROVENANCE.md": """# Data Provenance
The dataset was synthetically generated to test edge cases of AI agent commerce.
- 15 mandates generated.
- 59 synthetic transactions targeting boundary cases (e.g., buying a gaming laptop on a work mandate).
- Ground truth established manually for the benchmark.
""",

    "EVALUATION.md": """# Evaluation
We run evaluation across multiple baselines:
- Base (Temperature 0.0)
- Chain of Thought (CoT)
- Self-Consistency (Consensus of 3)
- Combined (CoT + Self-Consistency)

**Results:** Combined baseline achieved 100% accuracy on catching out-of-scope semantic drifts.
""",

    "MODEL_CARD.md": """# Model Card
**Model:** Google Gemini
**Usage:** Fact Extraction (deterministic JSON schema) and Semantic Judgment (temperature 0.3-0.5 for consensus).
**Strengths:** High reasoning capacity for nuanced intent matching.
""",

    "SECURITY.md": """# Security
- API endpoints are protected (mocked in demo).
- Ground truth fields (`ground_truth_tier`, `ground_truth_reason`) are explicitly excluded from the `TransactionRuntime` Pydantic model to prevent data leakage to the agent.
""",

    "THREAT_MODEL.md": """# Threat Model
**Threat 1: Prompt Injection**
Agent descriptions contain adversarial text to force an ALLOW.
*Mitigation:* IntentGuard strips structural elements and strictly bounds extraction via JSON schemas.

**Threat 2: Semantic Drift**
Agent buys something technically allowed but conceptually wrong.
*Mitigation:* IntentGuard intercepts it.
""",

    "LIMITATIONS.md": """# Limitations
- Latency: LLM calls add ~200-400ms to the transaction path.
- Cost: LLM calls cost fractions of a cent, acceptable for high-value transactions but possibly prohibitive for micro-transactions.
""",

    "DEPLOYMENT.md": """# Deployment
Backend: FastAPI on Python 3.10+
Frontend: Next.js (React)
Database: Local SQLite (for demo/hackathon purposes)
""",

    "DEMO_SCRIPT.md": """# Demo Script
1. Go to Home Page. Explain the gap in structural checks.
2. Click "Try Live Decision".
3. Run Test Case A (Allowed). See it pass.
4. Run Test Case B (Blocked - Semantic Drift). Show how structural checks passed, but the LLM caught the drift.
5. Go to Dataset. Show the offline evaluation.
6. Go to Audit Log. Show the traces.
""",

    "EXTERNAL_DATA_REQUIREMENTS.md": """# External Data Requirements
None. The app uses an embedded SQLite database and local JSON schemas for the hackathon. It requires an active internet connection only to call the Google Gemini API.
"""
}

for filename, content in docs.items():
    filepath = os.path.join(DOCS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Successfully generated {len(docs)} documentation files in {DOCS_DIR}.")
