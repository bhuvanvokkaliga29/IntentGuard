"""
IntentGuard — Prometheus Metrics & Observability Collector

Tracks real-time telemetry, latency histograms, decision counters, and self-healing recovery metrics.
Exposes standard Prometheus-compatible metrics text at GET /metrics.
"""

import time
from collections import defaultdict
from typing import Dict, List


class MetricsCollector:
    """In-memory Prometheus metrics registry and aggregator."""

    def __init__(self):
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.request_latencies: Dict[str, List[float]] = defaultdict(list)
        self.decisions_total: Dict[str, int] = defaultdict(int)
        self.llm_calls_total: Dict[str, int] = defaultdict(int)
        self.llm_latency_total: Dict[str, float] = defaultdict(float)
        self.self_healing_attempts: Dict[str, int] = defaultdict(int)
        self.active_connections: int = 0

    def record_request(self, endpoint: str, method: str, status_code: int, duration_sec: float) -> None:
        key = f'{method}:{endpoint}:{status_code}'
        self.request_counts[key] += 1
        self.request_latencies[f'{method}:{endpoint}'].append(duration_sec)
        # Keep last 1000 latency samples
        if len(self.request_latencies[f'{method}:{endpoint}']) > 1000:
            self.request_latencies[f'{method}:{endpoint}'] = self.request_latencies[f'{method}:{endpoint}'][-1000:]

    def record_decision(self, verdict: str) -> None:
        self.decisions_total[verdict.upper()] += 1

    def record_llm_call(self, provider: str, model: str, duration_sec: float) -> None:
        key = f'{provider}:{model}'
        self.llm_calls_total[key] += 1
        self.llm_latency_total[key] += duration_sec

    def record_self_healing(self, failure_type: str, resolved: bool) -> None:
        status = "resolved" if resolved else "failed"
        self.self_healing_attempts[f'{failure_type}:{status}'] += 1

    def generate_prometheus_output(self) -> str:
        """Generate Prometheus exposition text format."""
        lines = [
            "# HELP intentguard_http_requests_total Total number of HTTP requests processed.",
            "# TYPE intentguard_http_requests_total counter",
        ]
        for key, count in self.request_counts.items():
            parts = key.split(":")
            method, endpoint, status = parts[0], parts[1], parts[2]
            lines.append(f'intentguard_http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}')

        lines.extend([
            "",
            "# HELP intentguard_decisions_total Total financial authorization decisions by verdict.",
            "# TYPE intentguard_decisions_total counter",
        ])
        for verdict, count in self.decisions_total.items():
            lines.append(f'intentguard_decisions_total{{verdict="{verdict}"}} {count}')

        lines.extend([
            "",
            "# HELP intentguard_llm_calls_total Total semantic LLM calls executed.",
            "# TYPE intentguard_llm_calls_total counter",
        ])
        for key, count in self.llm_calls_total.items():
            provider, model = key.split(":")
            lines.append(f'intentguard_llm_calls_total{{provider="{provider}",model="{model}"}} {count}')

        lines.extend([
            "",
            "# HELP intentguard_self_healing_attempts_total Total bounded self-healing attempts.",
            "# TYPE intentguard_self_healing_attempts_total counter",
        ])
        for key, count in self.self_healing_attempts.items():
            parts = key.split(":")
            ftype, status = parts[0], parts[1]
            lines.append(f'intentguard_self_healing_attempts_total{{failure_type="{ftype}",status="{status}"}} {count}')

        lines.append("")
        return "\n".join(lines)


# Singleton metrics collector instance
metrics = MetricsCollector()
