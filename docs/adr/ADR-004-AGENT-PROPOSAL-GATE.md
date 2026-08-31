# ADR-004: Proposal-Only Gateway Architecture for Proposer Agents

## Status
Accepted

## Context
Granting autonomous agents direct API access to bank accounts or payment gateways allows misaligned or prompt-injected agents to execute catastrophic unauthorized transfers.

## Decision
Autonomous agents (Buying Agents, Recommendation Agents, Voice Agents) operate in a **Proposal-Only Sandbox**. They formulate transaction proposals (`TransactionProposal`) and submit them to the IntentGuard Gateway. Agents possess zero financial credentials and have no direct path to execution.

## Consequences
- Every transaction proposal must pass through the IntentGuard control plane before execution can occur.
- Compromised or hallucinating agents are intercepted at the proposal gateway without any money movement.
