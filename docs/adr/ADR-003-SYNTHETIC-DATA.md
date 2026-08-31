# ADR-003: Use of Synthetic Datasets for Benchmark Evaluation

## Status
Accepted

## Context
Financial transaction datasets containing actual payment details present severe privacy, compliance, and PII risks. Furthermore, real production logs rarely contain adversarial agent optimization anomalies (e.g. prompt injection, luxury cross-category deals under office mandates).

## Decision
IntentGuard uses a **deterministic, seed-controlled synthetic dataset generator** (`scripts/generate_dataset.py`) for all benchmark evaluations, demo scenarios, and developer test suites.

## Consequences
- 100% reproducible benchmarks across runs with identical seeds.
- Zero customer PII or confidential merchant data stored.
- Explicit labeling as `SYNTHETIC BENCHMARK` / `PROTOTYPE` across all documentation and UI dashboards.
