# ADR-001: Separation of LLM Reasoning from Financial Authorization Authority

## Status
Accepted

## Context
Autonomous agents are increasingly being tasked with financial procurement. While Large Language Models (LLMs) excel at semantic comprehension and natural language intent interpretation, they suffer from inherent nondeterminism, hallucination, prompt injection vulnerability, and lack mathematical invariance guarantees.

## Decision
The LLM is strictly restricted to providing **untrusted semantic evidence**. It is structurally prohibited from executing financial transactions, modifying budget caps, mutating user mandates, or directly returning binary payment authorizations. 

## Consequences
- The LLM output is parsed into structured Pydantic schemas and treated as advisory signal.
- Final financial authorization (`ALLOW`, `FLAG`, `BLOCK`, `ESCALATE`) is computed exclusively by deterministic Python policy code.
- If the LLM produces malformed output or experiences an outage, the system fails closed or escalates to human review.
