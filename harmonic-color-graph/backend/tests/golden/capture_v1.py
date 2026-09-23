"""Capture current (v1) analyze_progression_service outputs as a golden snapshot.

Run with: python -m tests.golden.capture_v1 (from backend/, with the package
installed - see scripts/check.*). Regenerating this file is a deliberate,
reviewed action (feature-specs/v2-implementation-plan.md, F03): it freezes
v1 behavior, bugs included, so later features can prove they changed it on
purpose rather than by accident. A golden file changes only with a commit
message explaining the musical reason (plan §0.4, stop condition 2).
"""

import json
from pathlib import Path

from app.services.analysis import analyze_progression_service

OUTPUT_PATH = Path(__file__).parent / "v1_analysis.json"

Case = dict[str, object]

CASES: list[Case] = [
    # -- roadmap-v2.md §2.2 defect reproductions (captured as-is; several are
    # -- known-wrong - see tests/unit/test_analysis_regressions.py) --
    {"id": "defect_dm_g", "chords": ["Dm", "G"], "key": None},
    {"id": "defect_d7_g_c", "chords": ["D7", "G", "C"], "key": "C major"},
    {"id": "defect_e7_am", "chords": ["E7", "Am"], "key": "C major"},
    {"id": "defect_fm_c_no_key", "chords": ["Fm", "C"], "key": None},
    {"id": "defect_bdim_c", "chords": ["Bdim", "C"], "key": "C major"},
    {"id": "defect_extensions_lost", "chords": ["Cmaj9", "Fadd9", "Gsus4", "C"], "key": None},
    {"id": "defect_am_dm_e7_am", "chords": ["Am", "Dm", "E7", "Am"], "key": None},
    {"id": "defect_ab_bb_c", "chords": ["Ab", "Bb", "C"], "key": "C major"},
    {"id": "defect_c_am_f_g_ambiguous", "chords": ["C", "Am", "F", "G"], "key": None},
    # -- context/code-standards.md minimum Phase 1 regression cases --
    {"id": "regression_c_g_am_f", "chords": ["C", "G", "Am", "F"], "key": "C major"},
    {"id": "regression_f_g_c", "chords": ["F", "G", "C"], "key": "C major"},
    {"id": "regression_dm_g_c", "chords": ["Dm", "G", "C"], "key": "C major"},
    {"id": "regression_fm_c_key_c_major", "chords": ["Fm", "C"], "key": "C major"},
    {"id": "regression_g_am_deceptive", "chords": ["G", "Am"], "key": "C major"},
    {"id": "regression_db7_c", "chords": ["Db7", "C"], "key": "C major"},
    # -- inversion (slash chord) case --
    {"id": "regression_inversion_c_over_e", "chords": ["C", "C/E", "F", "G"], "key": "C major"},
    # -- common progressions for broad coverage --
    {"id": "common_i_iv_v_i", "chords": ["C", "F", "G", "C"], "key": "C major"},
    {
        "id": "common_pop_loop_extended",
        "chords": ["C", "G", "Am", "Em", "F", "C", "F", "G"],
        "key": "C major",
    },
    {"id": "common_pop_punk", "chords": ["Am", "F", "C", "G"], "key": "C major"},
    {"id": "common_fifties_variant", "chords": ["C", "Am", "Dm", "G"], "key": "C major"},
    {"id": "common_i_iii_vi_iv", "chords": ["C", "Em", "Am", "F"], "key": "C major"},
    {"id": "common_i_v_vi_iv_d", "chords": ["D", "A", "Bm", "G"], "key": "D major"},
    {"id": "common_i_v_vi_iv_e", "chords": ["E", "B", "C#m", "A"], "key": "E major"},
    {"id": "common_i_v_vi_iv_g", "chords": ["G", "D", "Em", "C"], "key": "G major"},
    {"id": "common_i_iv_vi_v", "chords": ["C", "F", "Am", "G"], "key": "C major"},
    {"id": "common_andalusian_cadence", "chords": ["Am", "G", "F", "E"], "key": "A minor"},
    {"id": "common_minor_i_vi_vii", "chords": ["Am", "F", "G", "Am"], "key": "A minor"},
    {"id": "common_minor_circle", "chords": ["Am", "Dm", "G", "C"], "key": "A minor"},
    {"id": "common_minor_i_vi_iii_vii", "chords": ["Em", "C", "G", "D"], "key": "E minor"},
    {"id": "common_jazz_ii_v_i", "chords": ["Dm7", "G7", "Cmaj7"], "key": "C major"},
    {"id": "common_jazz_turnaround", "chords": ["Cmaj7", "A7", "Dm7", "G7"], "key": "C major"},
    {"id": "common_i_v7_i", "chords": ["C", "G7", "C"], "key": "C major"},
    {"id": "common_maj7_dominant", "chords": ["C", "Fmaj7", "G7", "C"], "key": "C major"},
    {"id": "common_i_v_vi_iv_bb", "chords": ["Bb", "F", "Gm", "Eb"], "key": "Bb major"},
    {"id": "common_secondary_dominant_iv", "chords": ["C", "C7", "F", "Fm", "C"], "key": "C major"},
    {"id": "common_v7_of_vi_no_key", "chords": ["C", "E7", "Am"], "key": None},
    {"id": "common_major_ii_borrowed", "chords": ["C", "D", "G"], "key": "C major"},
    {"id": "common_mixolydian_loop", "chords": ["C", "Bb", "F", "C"], "key": "C major"},
    {"id": "common_minor_bvii_bvi_v", "chords": ["Em", "D", "C", "B7"], "key": "E minor"},
    {"id": "common_i_vi_ii_v_major_two", "chords": ["C", "A", "D", "G"], "key": "C major"},
    {"id": "common_blues_turnaround", "chords": ["C7", "F7", "C7", "G7"], "key": "C major"},
]


def capture() -> list[Case]:
    results: list[Case] = []
    for case in CASES:
        response = analyze_progression_service(case["chords"], key=case["key"])
        results.append(
            {
                "id": case["id"],
                "chords": case["chords"],
                "key": case["key"],
                "response": response.model_dump(mode="json"),
            }
        )
    return results


def main() -> None:
    results = capture()
    OUTPUT_PATH.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} golden cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
