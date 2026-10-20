"""Budget-reserved controlled-runner live HTTP comparison; never a production claim.

Run this file directly. Serve imports the specified checkout before application code.
No provider/transport retries, paid warmups or benchmark modifications are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import statistics
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

BOUND = Decimal("0.75")
PAIR = BOUND * 2
BASELINE = "8ed6dfb5e63a7c5e417e3ffedd17d532e4548dec"
CANDIDATE = "e668de33d217417f4ef7dff53c576aa46b8f44b8"
MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-5"]


def allowed_cap(cap: str, prior_spend: str, total_ceiling: str) -> Decimal:
    values = [Decimal(value) for value in (cap, prior_spend, total_ceiling)]
    if any(not value.is_finite() for value in values):
        raise ValueError("Invalid nonfinite budget")
    requested, prior, ceiling = values
    if requested <= 0 or prior < 0 or ceiling <= prior:
        raise ValueError("Invalid exhausted budget")
    return min(requested, Decimal("2"), ceiling - prior)


def persist(path: Path, value: dict[str, Any]) -> None:
    """Atomic, flushed state on local disk; an existing ledger is never resumed."""
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class Ledger:
    def __init__(self, path: Path, cap: Decimal):
        if path.exists():
            raise ValueError("Existing ledger requires manual audit; do not replay requests")
        self.path, self.cap = path, cap
        self.value: dict[str, Any] = {"pairs": [], "committed_usd": "0"}
        persist(path, self.value)

    def reserve(self, case_id: str, observed_spend: Decimal) -> dict[str, Any]:
        committed = Decimal(self.value["committed_usd"])
        if max(committed, observed_spend) + PAIR > self.cap:
            raise ValueError("pair_budget_shortfall")
        row: dict[str, Any] = {"case_id": case_id, "reserved_usd": str(PAIR), "attempts": []}
        self.value["pairs"].append(row)
        self.value["committed_usd"] = str(committed + PAIR)
        persist(self.path, self.value)
        return row

    def settle(self, pair: dict[str, Any], cost: Decimal) -> None:
        if len(pair["attempts"]) != 2 or not all(a.get("audited") for a in pair["attempts"]):
            raise ValueError("Unknown pair outcome retains full reservation")
        if not Decimal("0") <= cost <= PAIR:
            raise ValueError("Invalid audited pair cost")
        self.value["committed_usd"] = str(Decimal(self.value["committed_usd"]) - PAIR + cost)
        pair["settled_usd"] = str(cost)
        persist(self.path, self.value)


def source_identity(backend: Path) -> dict[str, str]:
    result = subprocess.run(
        ["git", "-C", str(backend), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = subprocess.run(
        ["git", "-C", str(backend), "diff", "--exit-code", "HEAD", "--", "app"],
        capture_output=True,
    )
    if tracked.returncode:
        raise ValueError("Application checkout is dirty")
    digest = hashlib.sha256()
    for path in sorted((backend / "app").rglob("*.py")):
        digest.update(path.relative_to(backend).as_posix().encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return {"sha": result.stdout.strip(), "app_sha256": digest.hexdigest()}


def serve(args: argparse.Namespace) -> None:
    backend = args.backend.resolve()
    identity = source_identity(backend)
    sys.path.insert(0, str(backend))
    import uvicorn

    from app.ai.usage import configured_rates, request_cost_bound
    from app.api import ai_v2
    from app.core.config import get_settings
    from app.main import app

    # Workflow callables are observed without changing inputs, outputs or retries.
    original = ai_v2._default_workflow

    def factory(session: Any, meter: Any) -> Any:
        workflow = original(session, meter)
        records: list[dict[str, Any]] = []
        for attribute, stage in (("intent_model", "intent"), ("explanation_model", "explanation")):
            delegate = getattr(workflow, attribute)
            if delegate is None:
                continue

            def wrapped(prompt: str, delegate: Any = delegate, stage: str = stage) -> Any:
                record = {"stage": stage, "outcome": "started"}
                records.append(record)
                try:
                    value = delegate(prompt)
                    record["outcome"] = "returned"
                    return value
                except Exception:
                    record["outcome"] = "error"
                    raise

            setattr(workflow, attribute, wrapped)
        original_stream = workflow.stream

        def stream(query: str) -> Any:
            try:
                yield from original_stream(query)
            finally:
                with args.diagnostics.open("a", encoding="utf-8") as file:
                    file.write(
                        json.dumps(
                            {
                                "query_sha256": hashlib.sha256(query.encode()).hexdigest(),
                                "calls": records,
                                "unknown_usage_calls": meter.unknown_usage_calls,
                            }
                        )
                        + "\n"
                    )
                    file.flush()
                    os.fsync(file.fileno())

        workflow.stream = stream
        return workflow

    ai_v2._default_workflow = factory

    @app.get("/__paired_identity", include_in_schema=False)
    def paired_identity() -> dict[str, Any]:
        settings = get_settings()
        return {
            **identity,
            "corpus": settings.hcg_corpus_version,
            "daily_cap": str(settings.hcg_daily_ai_budget_usd),
            "request_bound": str(request_cost_bound()),
            "models": [
                os.getenv("HCG_LLM_FAST_MODEL", MODELS[0]),
                os.getenv("HCG_LLM_MODEL", MODELS[1]),
            ],
            "rates": [
                [str(x) for x in configured_rates(MODELS[0], "HCG_LLM_FAST")],
                [str(x) for x in configured_rates(MODELS[1], "HCG_LLM")],
            ],
        }

    uvicorn.run(app, host="127.0.0.1", port=args.port, access_log=False)


def events(lines: Any) -> Any:
    kind, data = "", []
    for line in lines:
        if line.startswith("event:"):
            kind = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].strip())
        elif not line and data:
            yield kind, json.loads("\n".join(data))
            kind, data = "", []


def audit_matches(audit: dict[str, Any], final: dict[str, Any]) -> bool:
    usages = audit.get("model_usage") or {}
    cost = Decimal(str(audit.get("cost_usd", "0")))
    known = sum(Decimal(str(row.get("cost_usd", "0"))) for row in usages.values())
    return bool(
        audit.get("final") == final
        and audit.get("parsed_intent")
        and not audit.get("error_category")
        and usages
        and cost < BOUND
        and cost == known
        and all(row.get("calls", 0) > 0 for row in usages.values())
        and not any("model_failed" in code for code in final.get("errors", []))
    )


def stable_query_id(previous: str | None, current: str) -> str:
    parsed = str(uuid.UUID(current))
    if previous is not None and previous != parsed:
        raise ValueError("sse_request_identity_mismatch")
    return parsed


def run(args: argparse.Namespace) -> None:
    import httpx
    from sqlalchemy import create_engine, text

    # Import grader only from the frozen candidate; benchmark and grader remain unchanged.
    sys.path.insert(0, str(args.candidate_backend.resolve()))
    from app.ai.state import AssistantResponse, ParsedIntent
    from tests.eval.ai import _measure, load_cases, summarize

    args.output.mkdir(parents=True, exist_ok=True)
    engine = create_engine(os.environ["HCG_PAIRED_EVAL_DATABASE_URL"])
    cutoff = datetime.fromisoformat(args.cutoff).astimezone(UTC)
    expected_ip_hash = hmac.new(
        os.environ["HCG_IP_HASH_SECRET"].encode(), b"127.0.0.1", hashlib.sha256
    ).hexdigest()
    cap = allowed_cap(args.cap, args.prior_spend, args.total_ceiling)
    ledger = Ledger(args.output / "ledger.json", cap)
    cases = [case for case in load_cases() if case["intent"]["route"] == "recommend"][:10]
    identities = {
        "baseline": source_identity(args.baseline_backend.resolve()),
        "candidate": source_identity(args.candidate_backend.resolve()),
    }
    if identities["baseline"]["sha"] != BASELINE or identities["candidate"]["sha"] != CANDIDATE:
        raise ValueError("Frozen commit mismatch")
    bases = {"baseline": args.baseline_url, "candidate": args.candidate_url}
    results: dict[str, list[dict[str, Any]]] = {name: [] for name in bases}

    def db_spend() -> tuple[Decimal, Decimal]:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT coalesce(sum(cost_usd) FILTER (WHERE created_at >= :cutoff),0), "
                    "coalesce(sum(cost_usd) FILTER "
                    "(WHERE created_at >= date_trunc('day',now())),0) "
                    "FROM hcg.ai_query_logs"
                ),
                {"cutoff": cutoff},
            ).one()
        return Decimal(str(row[0])), Decimal(str(row[1]))

    with httpx.Client(timeout=90, follow_redirects=False, trust_env=False) as client:

        def preflight() -> Decimal:
            for name, url in bases.items():
                if not url.startswith("http://127.0.0.1:"):
                    raise ValueError("Only runner-local endpoints accepted")
                health = client.get(url + "/health").json()
                actual = client.get(url + "/__paired_identity").json()
                expected = {
                    **identities[name],
                    "corpus": args.corpus,
                    "daily_cap": "2",
                    "request_bound": "0.75",
                    "models": MODELS,
                    "rates": [["1", "5"], ["2", "10"]],
                }
                # Decimal serialization may preserve equivalent zeroes.
                for field in ("daily_cap", "request_bound"):
                    actual[field] = str(Decimal(actual[field]).normalize())
                if actual != expected or health.get("corpus_version") != args.corpus:
                    raise ValueError("Endpoint identity/configuration mismatch")
            spent, today = db_spend()
            if today + PAIR > Decimal("2"):
                raise ValueError("shared_daily_pair_budget_shortfall")
            return spent

        stop = "maximum_pairs"
        try:
            for index, case in enumerate(cases):
                pair = ledger.reserve(case["id"], preflight())
                order = ("baseline", "candidate") if index % 2 == 0 else ("candidate", "baseline")
                for name in order:
                    attempt: dict[str, Any] = {
                        "arm": name,
                        "started_at": datetime.now(UTC).isoformat(),
                        "query_sha256": hashlib.sha256(case["input"].encode()).hexdigest(),
                    }
                    pair["attempts"].append(attempt)
                    persist(ledger.path, ledger.value)
                    started = time.perf_counter()
                    timing: dict[str, float] = {}
                    final = None
                    with client.stream(
                        "POST", bases[name] + "/v2/ai/query", json={"query": case["input"]}
                    ) as response:
                        if response.status_code != 200:
                            raise ValueError("http_non_success_outcome_requires_audit")
                        for kind, payload in events(response.iter_lines()):
                            query_id = payload.get("query_id")
                            if query_id:
                                attempt["query_id"] = stable_query_id(
                                    attempt.get("query_id"), query_id
                                )
                                persist(ledger.path, ledger.value)
                            elapsed = (time.perf_counter() - started) * 1000
                            if kind == "candidates":
                                timing.setdefault("first_candidate_ms", elapsed)
                            if kind in ("token", "text", "partial"):
                                timing.setdefault("first_text_ms", elapsed)
                            if kind == "error":
                                raise ValueError("sse_error_unknown_cost")
                            if kind == "final":
                                final = payload["response"]
                                timing["completion_ms"] = elapsed
                    if final is None or "query_id" not in attempt:
                        raise ValueError("missing_final_unknown_cost")
                    with engine.connect() as connection:
                        audit = dict(
                            connection.execute(
                                text(
                                    "SELECT final,parsed_intent,error_category,"
                                    "model_usage,cost_usd,"
                                    "tools,tokens_in,tokens_out FROM hcg.ai_query_logs "
                                    "WHERE query_id=CAST(:id AS uuid) AND created_at>=:cutoff "
                                    "AND ip_hash=:ip_hash AND user_query=:query"
                                ),
                                {
                                    "id": attempt["query_id"],
                                    "cutoff": cutoff,
                                    "ip_hash": expected_ip_hash,
                                    "query": case["input"],
                                },
                            )
                            .mappings()
                            .one()
                        )
                    if not audit_matches(audit, final):
                        raise ValueError("audit_final_or_usage_mismatch")
                    diagnostic_path = getattr(args, name + "_diagnostics")
                    diagnostics = [
                        json.loads(line) for line in diagnostic_path.read_text().splitlines()
                    ]
                    matches = [
                        row for row in diagnostics if row["query_sha256"] == attempt["query_sha256"]
                    ]
                    if len(matches) != 1 or matches[0]["unknown_usage_calls"]:
                        raise ValueError("missing_or_unknown_usage_diagnostics")
                    diagnostic = matches[0]
                    if any(call["outcome"] != "returned" for call in diagnostic["calls"]):
                        raise ValueError("callable_failed_uncertain_billing")
                    parsed = ParsedIntent.model_validate(audit["parsed_intent"])
                    measured = _measure(
                        case, AssistantResponse.model_validate(final), parsed, audit["tools"]
                    )
                    measured.update(
                        case_id=case["id"],
                        **timing,
                        cost_usd=str(audit["cost_usd"]),
                        tokens_in=audit["tokens_in"],
                        tokens_out=audit["tokens_out"],
                        model_usage=audit["model_usage"],
                        query_id=attempt["query_id"],
                    )
                    measured["model_call_attempts"] = len(diagnostic["calls"])
                    measured["repair_attempts"] = max(
                        0, sum(call["stage"] == "explanation" for call in diagnostic["calls"]) - 1
                    )
                    if final.get("candidates") and "first_candidate_ms" not in measured:
                        measured["first_candidate_ms"] = timing["completion_ms"]
                    measured["first_useful_ms"] = measured.get("first_candidate_ms")
                    attempt.update(audited=True, cost_usd=str(audit["cost_usd"]))
                    results[name].append(measured)
                    persist(ledger.path, ledger.value)
                ledger.settle(
                    pair, sum((Decimal(a["cost_usd"]) for a in pair["attempts"]), Decimal("0"))
                )
        except Exception as exc:
            # Never serialize provider/SQL/network exceptions, which may contain credentials.
            safe_codes = {
                "pair_budget_shortfall",
                "shared_daily_pair_budget_shortfall",
                "http_non_success_outcome_requires_audit",
                "sse_error_unknown_cost",
                "missing_final_unknown_cost",
                "audit_final_or_usage_mismatch",
                "missing_or_unknown_usage_diagnostics",
                "callable_failed_uncertain_billing",
                "sse_request_identity_mismatch",
            }
            stop = str(exc) if str(exc) in safe_codes else type(exc).__name__
        finally:
            summaries = {}
            paired_ids = {
                pair["case_id"] for pair in ledger.value["pairs"] if "settled_usd" in pair
            }
            for name, all_rows in results.items():
                rows = [row for row in all_rows if row["case_id"] in paired_ids]
                cost = sum((Decimal(row["cost_usd"]) for row in rows), Decimal("0"))
                summaries[name] = {
                    "quality": summarize(rows, len(rows), cost) if rows else None,
                    "completed": len(rows),
                    "fallback_rate": sum(row["fallback"] for row in rows) / len(rows)
                    if rows
                    else None,
                    "model_call_attempts": sum(row["model_call_attempts"] for row in rows),
                    "repair_attempts": sum(row["repair_attempts"] for row in rows),
                    "tokens_in": sum(row["tokens_in"] for row in rows),
                    "tokens_out": sum(row["tokens_out"] for row in rows),
                    "cost_usd": str(cost),
                    "completion_p50_ms": statistics.median(row["completion_ms"] for row in rows)
                    if rows
                    else None,
                    "first_useful_p50_ms": statistics.median(
                        row["first_useful_ms"]
                        for row in rows
                        if row.get("first_useful_ms") is not None
                    )
                    if any(row.get("first_useful_ms") is not None for row in rows)
                    else None,
                }
            persist(
                args.output / "report.json",
                {
                    "mode": "controlled_runner_live_http",
                    "identities": identities,
                    "corpus": args.corpus,
                    "protocol": {
                        "cap_usd": str(cap),
                        "prior_spend_usd": args.prior_spend,
                        "total_ceiling_usd": args.total_ceiling,
                        "cutoff": args.cutoff,
                        "pair_reservation_usd": str(PAIR),
                        "case_ids": [case["id"] for case in cases],
                        "order": "AB/BA alternating",
                        "maximum_pairs": 10,
                        "paid_warmup": False,
                        "first_useful_boundary": (
                            "first validated candidate event, or final with candidates"
                        ),
                        "transport_retries": 0,
                    },
                    "stop": stop,
                    "summaries": summaries,
                    "rows": results,
                    "limitations": [
                        "Maximum ten pairs; p95 not certified",
                        "No musician judgment",
                        "Not Vercel production",
                        "Diagnostics reconcile actual callable attempts and unknown usage",
                    ],
                },
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    server = commands.add_parser("serve")
    server.add_argument("--backend", type=Path, required=True)
    server.add_argument("--diagnostics", type=Path, required=True)
    server.add_argument("--port", type=int, required=True)
    evaluator = commands.add_parser("run")
    for name in (
        "baseline-backend",
        "candidate-backend",
        "baseline-diagnostics",
        "candidate-diagnostics",
        "output",
    ):
        evaluator.add_argument("--" + name, type=Path, required=True)
    for name in (
        "baseline-url",
        "candidate-url",
        "cutoff",
        "corpus",
        "prior-spend",
        "total-ceiling",
    ):
        evaluator.add_argument("--" + name, required=True)
    evaluator.add_argument("--cap", default="2")
    args = parser.parse_args()
    (serve if args.command == "serve" else run)(args)


if __name__ == "__main__":
    main()
