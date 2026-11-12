"""No network/model calls: pair reservation, uncertainty and stream parsing."""

from decimal import Decimal

import pytest

from tests.eval.paired_live import (
    Ledger,
    allowed_cap,
    audit_matches,
    complete_call_usage,
    events,
    stable_query_id,
)


def test_metered_validation_failure_is_accounted_but_missing_usage_is_not():
    diagnostic = {
        "unknown_usage_calls": 0,
        "calls": [
            {"outcome": "error", "usage_recorded_calls": 1, "unknown_usage_calls": 0},
            {"outcome": "returned", "usage_recorded_calls": 1, "unknown_usage_calls": 0},
        ],
    }
    assert complete_call_usage(diagnostic, {"main": {"calls": 2}})
    assert not complete_call_usage(diagnostic, {"main": {"calls": 1}})
    diagnostic["calls"][0]["usage_recorded_calls"] = 0
    assert not complete_call_usage(diagnostic, {"main": {"calls": 2}})
    diagnostic["calls"][0]["usage_recorded_calls"] = 1
    diagnostic["calls"][0]["unknown_usage_calls"] = 1
    assert not complete_call_usage(diagnostic, {"main": {"calls": 2}})


def test_stream_identity_stable_and_valid_uuid():
    value = "3ab8e21e-973e-4060-9f99-f8669344d4aa"
    assert stable_query_id(None, value) == value
    assert stable_query_id(value, value) == value
    with pytest.raises(ValueError, match="identity_mismatch"):
        stable_query_id(value, "00000000-0000-0000-0000-000000000000")
    with pytest.raises(ValueError):
        stable_query_id(None, "invalid")


def test_additional_budget_preserves_historical_spend():
    assert allowed_cap("2", "10.157483", "12.157483") == Decimal("2")
    assert allowed_cap("5", "10.157483", "12.157483") == Decimal("2")
    assert allowed_cap("2", "11.157483", "12.157483") == Decimal("1")


@pytest.mark.parametrize("prior,ceiling", [("10.157483", "10"), ("NaN", "12"), ("0", "Infinity")])
def test_exhausted_or_nonfinite_budget_rejected(prior, ceiling):
    with pytest.raises(ValueError):
        allowed_cap("2", prior, ceiling)


def test_pair_requires_full_reservation(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", Decimal("2"))
    with pytest.raises(ValueError, match="pair_budget"):
        ledger.reserve("case", Decimal("0.51"))
    assert not ledger.value["pairs"]


def test_known_pair_refunds_only_after_both_audits(tmp_path):
    ledger = Ledger(tmp_path / "ledger.json", Decimal("2"))
    pair = ledger.reserve("case", Decimal("0"))
    pair["attempts"] = [{"audited": True}, {"audited": False}]
    with pytest.raises(ValueError, match="Unknown"):
        ledger.settle(pair, Decimal("0.01"))
    assert ledger.value["committed_usd"] == "1.50"
    pair["attempts"][1]["audited"] = True
    ledger.settle(pair, Decimal("0.01"))
    assert ledger.value["committed_usd"] == "0.01"
    ledger.reserve("next", Decimal("0.01"))


def test_unknown_pair_never_replays(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = Ledger(path, Decimal("2"))
    ledger.reserve("case", Decimal("0"))
    with pytest.raises(ValueError, match="manual audit"):
        Ledger(path, Decimal("2"))
    with pytest.raises(ValueError, match="pair_budget"):
        ledger.reserve("next", Decimal("0"))


def test_unmatched_final_or_reserved_cost_never_refunds():
    final = {"errors": []}
    audit = {
        "final": final,
        "parsed_intent": {"task_type": "recommend"},
        "model_usage": {"model": {"calls": 1, "cost_usd": "0.01"}},
        "cost_usd": "0.01",
    }
    assert audit_matches(audit, final)
    assert not audit_matches(audit, {"errors": ["changed"]})
    assert not audit_matches({**audit, "cost_usd": "0.75"}, final)
    assert not audit_matches({**audit, "error_category": "timeout"}, final)
    assert not audit_matches({**audit, "model_usage": {}}, final)


def test_sse_parses_multiline_and_ignores_comment():
    assert list(
        events(
            [
                ": heartbeat",
                "event: final",
                'data: {"response":',
                'data: {"route": "recommend"}}',
                "",
            ]
        )
    ) == [("final", {"response": {"route": "recommend"}})]
