"""Live-evaluation accounting does not silently treat a fallback as a model run."""

from argparse import Namespace
from types import SimpleNamespace

import pytest

from tests.eval.ai_adversarial import _cost, _model_call


class FakeModel:
    def __init__(self, metadata):
        self.metadata = metadata

    def with_structured_output(self, _schema, *, include_raw):
        assert include_raw
        return self

    def invoke(self, _prompt):
        return {
            "raw": SimpleNamespace(usage_metadata=self.metadata),
            "parsed": {"task_type": "clarify"},
            "parsing_error": None,
        }


def test_model_wrapper_records_usage_and_cost():
    usage = {"fast": {"input": 0, "output": 0, "calls": 0}}
    assert _model_call(
        FakeModel({"input_tokens": 100, "output_tokens": 20}), object, usage, "fast"
    )("prompt") == {"task_type": "clarify"}
    assert usage["fast"] == {"input": 100, "output": 20, "calls": 1}
    assert _cost(usage, Namespace(fast_input_price=1.0, fast_output_price=5.0)) == 0.0002


def test_model_wrapper_rejects_missing_usage():
    usage = {"fast": {"input": 0, "output": 0, "calls": 0}}
    with pytest.raises(ValueError, match="token usage"):
        _model_call(FakeModel({}), object, usage, "fast")("prompt")
