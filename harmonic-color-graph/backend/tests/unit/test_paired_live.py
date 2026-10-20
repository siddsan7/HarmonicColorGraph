"""No network/model calls: pair reservation, uncertainty and stream parsing."""

from decimal import Decimal

import pytest

from tests.eval.paired_live import Ledger, audit_matches, events


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
