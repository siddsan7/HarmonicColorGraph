"""Content-free local workflow profiling; these timings are not HTTP latency."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from app.recommend.scorer import WEIGHTS_FILE
from tests.eval.tail_acceptance import completion_tail_acceptance


class RequestDiagnostics:
    def __init__(self) -> None:
        self.started = time.perf_counter()
        self.nodes: dict[str, float] = {}
        self.node_ms: dict[str, float] = {}
        self.model_calls: list[dict[str, Any]] = []
        self.first_text_ms: float | None = None
        self.first_candidates_ms: float | None = None
        self.first_result_ms: float | None = None

    def attach(self, workflow: Any) -> None:
        for attr, stage in (("intent_model", "intent"), ("explanation_model", "explanation")):
            model = getattr(workflow, attr, None)
            if model is not None:
                setattr(workflow, attr, self._model(model, stage))

    def _model(self, model, stage):
        def call(prompt):
            started = time.perf_counter()
            outcome = "error"
            try:
                result = model(prompt)
                outcome = "returned"
                return result
            finally:
                self.model_calls.append(
                    {
                        "stage": stage,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "prompt_bytes": len(prompt.encode("utf-8")),
                        "outcome": outcome,
                    }
                )

        return call

    def event(self, event: str, payload: dict[str, Any]) -> None:
        now = time.perf_counter()
        if event == "step":
            node = payload["node"]
            if payload["status"] == "started":
                self.nodes[node] = now
            elif node in self.nodes:
                self.node_ms[node] = (now - self.nodes.pop(node)) * 1000
        elif event == "partial" and payload.get("text") and self.first_text_ms is None:
            self.first_text_ms = (now - self.started) * 1000
            if self.first_result_ms is None:
                self.first_result_ms = self.first_text_ms
        elif (
            event == "candidates" and payload.get("candidates") and self.first_candidates_ms is None
        ):
            self.first_candidates_ms = (now - self.started) * 1000
            if self.first_result_ms is None:
                self.first_result_ms = self.first_candidates_ms

    def finish(self) -> dict[str, Any]:
        return {
            "workflow_completion_ms": (time.perf_counter() - self.started) * 1000,
            "first_validated_text_ms": self.first_text_ms,
            "first_validated_candidates_ms": self.first_candidates_ms,
            "first_validated_result_ms": self.first_result_ms,
            "node_ms": self.node_ms,
            "model_calls": self.model_calls,
            "repair_calls": max(
                0, sum(row["stage"] == "explanation" for row in self.model_calls) - 1
            ),
        }


def route_diagnostics(
    rows: list[dict[str, Any]], *, evidence_type: str = "offline"
) -> dict[str, Any]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["expected_route"]].append(row)
    result = {}
    for route, sample in sorted(groups.items()):
        completed = [row for row in sample if "error" not in row]
        times = sorted(row["diagnostics"]["workflow_completion_ms"] for row in completed)
        text_times = sorted(
            row["diagnostics"]["first_validated_text_ms"]
            for row in completed
            if row["diagnostics"]["first_validated_text_ms"] is not None
        )
        result_times = sorted(
            row["diagnostics"]["first_validated_result_ms"]
            for row in completed
            if row["diagnostics"].get("first_validated_result_ms") is not None
        )
        cost = sum((Decimal(row["accounted_cost_usd"]) for row in sample), Decimal(0))
        result[route] = {
            "completion_tail_acceptance": completion_tail_acceptance(
                sample, evidence_type=evidence_type
            ),
            "attempts": len(sample),
            "completed": len(completed),
            "request_failures": len(sample) - len(completed),
            "fallbacks": sum(bool(row.get("fallback")) for row in completed),
            "fallback_rate": (
                sum(bool(row.get("fallback")) for row in completed) / len(completed)
                if completed
                else None
            ),
            "repair_calls": sum(row["diagnostics"]["repair_calls"] for row in sample),
            "accounted_cost_usd": str(cost),
            "cost_per_completed_request_usd": str(cost / len(completed)) if completed else None,
            "tokens_in": sum(
                usage["tokens_in"] for row in sample for usage in row["model_usage"].values()
            ),
            "tokens_out": sum(
                usage["tokens_out"] for row in sample for usage in row["model_usage"].values()
            ),
            "model_calls": sum(
                usage["calls"] for row in sample for usage in row["model_usage"].values()
            ),
            "p50_workflow_ms": median(times) if times else None,
            "p95_workflow_ms": times[math.ceil(0.95 * len(times)) - 1] if times else None,
            "p50_first_validated_text_ms": median(text_times) if text_times else None,
            "validated_result_count": len(result_times),
            "completed_without_validated_result": len(completed) - len(result_times),
            "p50_first_validated_result_ms": median(result_times) if result_times else None,
            "p95_first_validated_text_ms": (
                text_times[math.ceil(0.95 * len(text_times)) - 1] if text_times else None
            ),
        }
    return result


def reproducibility(cases: list[dict[str, Any]], *, live: bool, fixture: bool) -> dict[str, Any]:
    backend = Path(__file__).resolve().parents[2]

    def git(*args):
        try:
            return subprocess.run(
                ["git", "-C", str(backend), *args], capture_output=True, text=True, check=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    status = git("status", "--porcelain")
    return {
        "source_commit": git("rev-parse", "HEAD"),
        "source_branch": git("branch", "--show-current"),
        "python": sys.version.split()[0],
        "dirty": bool(status) if status is not None else None,
        "source_sha256": {
            name: hashlib.sha256((backend / name).read_bytes()).hexdigest()
            for name in (
                "app/ai/workflow.py",
                "app/ai/intent_fallback.py",
                "app/recommend/scorer.py",
                "app/recommend/features.py",
                "tests/eval/ai.py",
                "tests/eval/ai_diagnostics.py",
            )
        },
        "case_sha256": hashlib.sha256(
            json.dumps(cases, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "weights_sha256": hashlib.sha256(WEIGHTS_FILE.read_bytes()).hexdigest(),
        "models": {
            "intent": os.getenv("HCG_LLM_FAST_MODEL", "claude-haiku-4-5-20251001"),
            "explanation": os.getenv("HCG_LLM_MODEL", "claude-sonnet-5"),
        }
        if live
        else {},
        "corpus_version": "ai-eval-v1" if fixture else "unverified",
        "timing_boundary": "in-process workflow including tool scope; excludes HTTP/SSE transport",
        "first_useful_boundary": "validated explanation text; candidates arrive in final frame",
        "cache_state": "uncontrolled; process caches may warm across cases",
        "p95_method": "nearest rank; small samples do not establish a reliable tail",
    }
