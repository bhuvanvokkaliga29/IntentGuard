# Demo Architecture & Continuous Verification Flow

## 1. 5-Stage Demo Narrative for Judges

### Step 1: Real Agent Initiation & Tool Call
- Select Buying Agent under Mandate: *"Office supplies up to ₹2,000 per week"*.
- Observe live FSM timeline transition: `INITIALIZING` $\rightarrow$ `READING_CONTEXT` $\rightarrow$ `PLANNING` $\rightarrow$ `TOOL_CALL`.
- Agent executes `catalog.search` tool against synthetic merchant database.

### Step 2: Injected Fault & Autonomous Self-Healing
- Select **Tool Timeout** in Failure Injection.
- System detects timeout $\rightarrow$ classifies fault as `TIMEOUT` $\rightarrow$ initiates backoff retry $\rightarrow$ successfully recovers $\rightarrow$ resumes state machine.

### Step 3: Optimization Drift & Proposal Generation
- Buying Agent (optimizing for `BEST_RATING`) selects ₹1,950 Chocolates from Stationery Mart.
- Formulates proposal $\rightarrow$ validates syntax $\rightarrow$ hands off proposal to IntentGuard gateway.

### Step 4: IntentGuard Interception & Policy Gate
- Structural Check: **PASS** (Budget and Merchant OK)
- Fact Extraction: Confectionery / Food
- Semantic Entailment: **NO_FIT**
- Deterministic Decision: **FLAG / BLOCK**

### Step 5: Immutable Audit Ledger & Human Review
- Transaction routed to Human Review Queue.
- Full execution trace persisted to SQLite ledger.
