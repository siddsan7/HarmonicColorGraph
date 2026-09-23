"""v1 code must keep reproducing the golden snapshot exactly.

This guards the legacy `/v1` routes (feature-specs/v2-implementation-plan.md,
F03): once v2 analysis lands, v1 stays callable and byte-for-byte identical
to what it always returned. If a change to app/theory or app/services makes
this fail, either the change unintentionally touched v1 behavior (fix the
change) or v1 was deliberately modified (regenerate the golden file with
`python -m tests.golden.capture_v1` from backend/, and explain the musical
reason in the commit message).
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.analysis import analyze_progression_service

GOLDEN_PATH = Path(__file__).parent.parent / "golden" / "v1_analysis.json"


def _load_golden_cases() -> list[dict[str, Any]]:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


GOLDEN_CASES = _load_golden_cases()


def test_golden_file_has_expected_case_count():
    assert len(GOLDEN_CASES) == 41


@pytest.mark.parametrize("case", GOLDEN_CASES, ids=[case["id"] for case in GOLDEN_CASES])
def test_v1_reproduces_golden_case(case: dict[str, Any]):
    response = analyze_progression_service(case["chords"], key=case["key"])
    assert response.model_dump(mode="json") == case["response"]
