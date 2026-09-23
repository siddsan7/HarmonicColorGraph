"""Known-wrong v1 analysis cases, encoded as expected failures.

Each case reproduces a defect from docs/roadmap-v2.md §2.2 and states the
behavior a later feature (F11 key finder, F12 Roman v2, F13 relationships,
F10 chord features) must produce instead. `strict=True` means a fix that
makes one of these pass will turn the marker into a *failure* until it is
removed here - that is the point: it forces the fixing feature to touch
this file and consciously promote the case to a real regression test
(feature-specs/v2-implementation-plan.md, F03).

Do not weaken or delete a case to make it pass (plan §0.4, stop condition
2); remove the xfail marker only when the referenced feature actually
lands.
"""

import pytest

from app.services.analysis import analyze_progression_service
from app.theory.roman_analysis import analyze_progression


@pytest.mark.xfail(
    strict=True, reason="fixed in F11: 24-key finder must score keys beyond chord-root candidates"
)
def test_dm_g_includes_c_major_in_top_two():
    result = analyze_progression(["Dm", "G"], key=None)
    top_two_keys = [result.key] + [alt.key for alt in result.alternate_analyses[:1]]
    assert "C major" in top_two_keys


@pytest.mark.xfail(
    strict=True, reason="fixed in F12: applied dominants (V7/x) are not yet recognized"
)
def test_d7_g_c_is_secondary_dominant():
    response = analyze_progression_service(["D7", "G", "C"], key="C major")
    assert response.roman_chords == ["V7/V", "V", "I"]


@pytest.mark.xfail(
    strict=True, reason="fixed in F12: applied dominants (V7/x) are not yet recognized"
)
def test_e7_am_is_secondary_dominant_of_vi():
    response = analyze_progression_service(["E7", "Am"], key="C major")
    assert response.roman_chords == ["V7/vi", "vi"]


@pytest.mark.xfail(
    strict=True, reason="fixed in F11: key finder must prefer C major over the F-rooted candidate"
)
def test_fm_c_resolves_to_borrowed_iv_in_c_major():
    result = analyze_progression(["Fm", "C"], key=None)
    assert result.key == "C major"
    assert result.roman_chords == ["iv", "I"]


@pytest.mark.xfail(
    strict=True, reason="fixed in F12: diminished quality is not marked in the roman token"
)
def test_bdim_c_is_leading_tone_diminished():
    response = analyze_progression_service(["Bdim", "C"], key="C major")
    assert response.roman_chords == ["viio", "I"]


@pytest.mark.xfail(
    strict=True,
    reason="fixed in F13: authentic cadence rule only matches uppercase V->I, not minor-key V7->i",
)
def test_am_dm_e7_am_authentic_cadence_is_labeled():
    response = analyze_progression_service(["Am", "Dm", "E7", "Am"], key=None)
    final_transition = response.relationships[-1]
    assert "authentic cadence" in final_transition.relationship_labels


@pytest.mark.xfail(
    strict=True, reason="fixed in F13: no Aeolian/modal-mixture cadence rule exists yet"
)
def test_ab_bb_c_borrowed_chords_are_labeled():
    response = analyze_progression_service(["Ab", "Bb", "C"], key="C major")
    all_labels = [label for t in response.relationships for label in t.relationship_labels]
    assert all_labels, "bVI-bVII-I should carry at least one relationship label"


@pytest.mark.xfail(
    strict=True, reason="fixed in F11: AnalyzeProgressionResponse has no ambiguity flag yet"
)
def test_c_am_f_g_ambiguity_is_flagged():
    response = analyze_progression_service(["C", "Am", "F", "G"], key=None)
    assert response.ambiguous is True


@pytest.mark.xfail(
    strict=True, reason="fixed in F10/F12: chord extensions are dropped from the roman token"
)
def test_extensions_are_preserved_in_the_figure():
    response = analyze_progression_service(["Cmaj9", "Fadd9", "Gsus4", "C"], key=None)
    assert response.roman_chords == ["Imaj9", "IVadd9", "Vsus4", "I"]


@pytest.mark.xfail(
    strict=True, reason="fixed in F10/F12: inversions are dropped from the roman token"
)
def test_inversion_is_preserved_in_the_figure():
    response = analyze_progression_service(["C", "C/E", "F", "G"], key="C major")
    assert response.roman_chords == ["I", "I6", "IV", "V"]
