"""Batch judge: cost cap, request shape, and count-only scoring (no network)."""

import json
from argparse import Namespace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from tests.eval.batch_judge import collect, cost_bound, request_params, submit

SAMPLE = {
    "id": "case-1",
    "input": "Explain C G Am F",
    "claims": [
        {"text": "G is the dominant.", "fact_ids": ["f1"]},
        {"text": "Am is the relative minor.", "fact_ids": ["f2"]},
    ],
    "evidence": json.dumps({"analyze_progression": {"fact_ids": ["f1", "f2"]}}),
    "evidence_truncated": False,
    "arm": "new",
    "repeat": 0,
}


def _samples(tmp_path, count=2):
    path = tmp_path / "samples.jsonl"
    path.write_text("\n".join(json.dumps(SAMPLE) for _ in range(count)) + "\n", encoding="utf-8")
    return path


def _message(text, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
    )


class FakeBatches:
    def __init__(self, results):
        self.created = None
        self._results = results

    def create(self, requests):
        self.created = requests
        return SimpleNamespace(id="batch_1")

    def retrieve(self, batch_id):
        return SimpleNamespace(processing_status="ended")

    def results(self, batch_id):
        return iter(self._results)


def _client(results=()):
    return SimpleNamespace(messages=SimpleNamespace(batches=FakeBatches(list(results))))


def test_request_uses_structured_output_without_forced_tools_or_sampling():
    params = request_params(SAMPLE, "claude-opus-5-5", "high")
    assert params["output_config"]["effort"] == "high"
    assert params["output_config"]["format"]["type"] == "json_schema"
    for rejected in ("tool_choice", "temperature", "thinking", "fallbacks", "stream"):
        assert rejected not in params
    assert "0. G is the dominant. (cites: f1)" in params["messages"][0]["content"]


def test_submit_refuses_when_bound_exceeds_cap(tmp_path):
    args = Namespace(
        samples=_samples(tmp_path),
        output_dir=tmp_path / "out",
        max_cost_usd=Decimal("0.001"),
        model="claude-opus-5-5",
        effort="high",
    )
    client = _client()
    with pytest.raises(ValueError, match="exceeds cap"):
        submit(args, client)
    assert client.messages.batches.created is None


def test_submit_then_collect_reports_counts_only(tmp_path):
    out = tmp_path / "out"
    args = Namespace(
        samples=_samples(tmp_path),
        output_dir=out,
        max_cost_usd=Decimal("5"),
        model="claude-opus-5-5",
        effort="high",
    )
    submit(args, _client())
    state = json.loads((out / "batch_state.json").read_text(encoding="utf-8"))
    assert state["batch_id"] == "batch_1" and len(state["samples"]) == 2
    with pytest.raises(ValueError, match="already submitted"):
        submit(args, _client())
    verdicts = {
        "verdicts": [
            {"claim_index": 0, "verdict": "supported", "reason": "f1 names G as V"},
            {"claim_index": 1, "verdict": "unsupported", "reason": "no relative minor fact"},
        ]
    }
    results = [
        SimpleNamespace(
            custom_id="s00000",
            result=SimpleNamespace(type="succeeded", message=_message(json.dumps(verdicts))),
        ),
        SimpleNamespace(
            custom_id="s00001",
            result=SimpleNamespace(type="succeeded", message=_message("", "refusal")),
        ),
    ]
    report = collect(Namespace(output_dir=out, wait_minutes=0), _client(results))
    arm = report["arms"]["new"]
    assert arm["claims_judged"] == 2
    assert arm["counts"]["judge_refusal"] == 2
    assert arm["supported_rate"] == 0.5
    # Batch pricing: half of $4/$20 per million tokens, for two metered requests.
    assert Decimal(report["metered_cost_usd"]) == Decimal("0.008")
    saved = (out / "judge.json").read_text(encoding="utf-8")
    assert "relative minor" not in saved and "dominant" not in saved
    details = (out / "judge_details.jsonl").read_text(encoding="utf-8")
    assert "no relative minor fact" in details


def test_cost_bound_grows_with_samples():
    assert cost_bound([SAMPLE, SAMPLE], "claude-opus-5-5") > cost_bound([SAMPLE], "claude-opus-5-5")
