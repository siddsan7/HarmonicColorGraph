"""Candidate availability and validated prose are distinct timing boundaries."""

from tests.eval.ai_diagnostics import RequestDiagnostics, reproducibility, route_diagnostics


def test_reproducibility_describes_new_boundary_and_hashes_behavior_helpers():
    metadata = reproducibility([], live=False, fixture=True)
    assert "candidate preview after rank" in metadata["first_useful_boundary"]
    assert "excludes HTTP/SSE" in metadata["first_useful_boundary"]
    assert {
        "app/ai/explanation_constraints.py",
        "tests/eval/tail_acceptance.py",
        "tests/eval/ai_cost_diagnostics.py",
    } <= metadata["source_sha256"].keys()


def test_preview_is_useful_before_explanation_without_relabeling_text(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("tests.eval.ai_diagnostics.time.perf_counter", lambda: now[0])
    diagnostics = RequestDiagnostics()
    now[0] = 0.5
    diagnostics.event("step", {"node": "rank", "status": "completed"})
    diagnostics.event("candidates", {"candidates": []})
    assert diagnostics.finish()["first_validated_result_ms"] is None
    now[0] = 1.0
    diagnostics.event("candidates", {"candidates": [{"chords": ["C"]}]})
    now[0] = 5.0
    diagnostics.event("partial", {"text": "A validated explanation."})
    timing = diagnostics.finish()
    assert timing["first_validated_candidates_ms"] == 1000
    assert timing["first_validated_result_ms"] == 1000
    assert timing["first_validated_text_ms"] == 5000
    row = {
        "expected_route": "recommend",
        "diagnostics": timing,
        "accounted_cost_usd": "0",
        "model_usage": {},
    }
    summary = route_diagnostics([row])["recommend"]
    assert summary["p50_first_validated_result_ms"] == 1000
    assert summary["p50_first_validated_text_ms"] == 5000
    assert summary["validated_result_count"] == 1


def test_prose_only_first_result_and_legacy_missing_timing(monkeypatch):
    now = [0.0]
    monkeypatch.setattr("tests.eval.ai_diagnostics.time.perf_counter", lambda: now[0])
    diagnostics = RequestDiagnostics()
    now[0] = 2.0
    diagnostics.event("partial", {"text": "Validated."})
    assert diagnostics.finish()["first_validated_result_ms"] == 2000
    legacy = {
        "expected_route": "explain",
        "accounted_cost_usd": "0",
        "model_usage": {},
        "diagnostics": {
            "workflow_completion_ms": 3000,
            "first_validated_text_ms": 2000,
            "repair_calls": 0,
        },
    }
    summary = route_diagnostics([legacy])["explain"]
    assert summary["p50_first_validated_result_ms"] is None
    assert summary["completed_without_validated_result"] == 1
