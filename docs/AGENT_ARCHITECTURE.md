# Autonomous Proposer Agents Architecture

## 1. Architectural Philosophy: Bounded Proposers, Not Executors

In agentic financial systems, the central security question is:
> **"Can an autonomous agent remain within a user's numerical and structural limits while still violating what the user actually meant?"**

To answer this question, IntentGuard establishes a strict architectural boundary:
- Autonomous agents operate exclusively as **Transaction-Proposing Agents**.
- Proposer agents have **zero authority** to execute money movement.
- IntentGuard acts as the **central gateway and semantic authorization layer**.

```
USER
  ↓
USER MANDATE (Natural language intent + structural bounds)
  ↓
AUTONOMOUS AGENT ECOSYSTEM
  ├── Buying Agent (Procurement optimizer)
  ├── Recommendation Agent (Promotional / deals recommender)
  └── Voice / NL Interface (Conversational mandate parser)
  ↓
TRANSACTION PROPOSAL (Structured draft action)
  ↓
============================================================
              INTENTGUARD GATEWAY (Gatekeeper)
============================================================
  ├── Structural Policy Engine (Deterministic constraints)
  ├── Fact Extraction Pipeline (Untrusted description parsing)
  ├── Semantic Verification (Multi-sample self-consistency)
  ├── Confidence Engine (Evidence & agreement calculation)
  └── Deterministic Decision Policy (ALLOW / FLAG / BLOCK / ESCALATE)
  ↓
FINANCIAL EXECUTION GATE (Only ALLOW moves funds; others routed to Human Review)
```

---

## 2. Implemented Proposer Agents

### Agent 1 — Autonomous Buying Agent (`BuyingAgent`)
- **Purpose**: Simulates an autonomous purchasing system acting on synthetic merchant catalogs under a user mandate.
- **Configurable Optimization Objectives**:
  - `LOWEST_PRICE`: Greedily selects the cheapest candidate meeting budget limits.
  - `BEST_RATING`: Selects the highest customer-rated product (which may be a luxury chocolate box sold at a stationery store).
  - `PROMOTION`: Prioritizes maximum percentage discount deals.
  - `CONVENIENCE`: Selects the first fast-dispatching item.
  - `MERCHANT_LOYALTY`: Strictly procures from primary approved vendors.
  - `CATEGORY_MATCH`: Lexically aligns item name with intent keywords.
- **Observable Factors Emitted**: Merchant rating, pricing breakdown, discount rate, vendor match, objective rationale.

### Agent 2 — AI Recommendation Agent (`RecommendationAgent`)
- **Purpose**: Simulates recommendation systems influencing autonomous transactions.
- **Biases Modeled**:
  - `PROMOTIONAL_UPSELL`: Pushes 30% discounted luxury spa packages under a household grocery mandate.
  - `CROSS_CATEGORY`: Promotes high-engagement non-essential items from approved merchants.
- **Behavioral Demonstration**: Proves that commercial optimization does not equal user intent alignment.

### Agent 3 — Voice / Natural Language Interface (`VoiceMandateAgent`)
- **Purpose**: Allows users to specify spending intent via conversational spoken language or text transcripts.
- **Normalization**: Extracts `intent_text`, `max_amount_per_txn`, `budget_cap`, `allowed_categories`, `allowed_merchants`, `frequency`, `exclusions`, and `purpose_context`.

---

## 3. Strict Proposer Agent Constraints

1. **No Direct Financial API Access**: Proposer agents have no access to Razorpay or banking credentials.
2. **Ground Truth Isolation**: Proposer agents never see evaluation benchmark labels or semantic compatibility matrices.
3. **Immutability of Mandates**: Once signed, user mandates cannot be mutated or overridden by proposer agents.
