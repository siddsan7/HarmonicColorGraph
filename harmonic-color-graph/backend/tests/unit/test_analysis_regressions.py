"""The F03 defect reproductions, promoted to passing v2 regression checks."""

from app.theory.roman import analyze_v2


def test_dm_g_includes_c_major_in_top_two_and_is_ambiguous():
    result = analyze_v2(["Dm", "G"])
    assert "C major" in {item.key for item in result.key_distribution[:2]}
    assert result.ambiguous


def test_d7_g_c_is_secondary_dominant():
    result = analyze_v2(["D7", "G", "C"], key="C major")
    assert [token.figure for token in result.tokens] == ["V7/V", "V", "I"]
    assert "secondary dominant" in {relation.name for relation in result.relationships}


def test_e7_am_is_secondary_dominant_of_vi():
    result = analyze_v2(["E7", "Am"], key="C major")
    assert [token.figure for token in result.tokens] == ["V7/vi", "vi"]


def test_fm_c_resolves_to_borrowed_iv_in_c_major():
    result = analyze_v2(["Fm", "C"])
    assert result.song_key == "C major"
    assert [token.figure for token in result.tokens] == ["iv", "I"]
    assert result.tokens[0].is_borrowed


def test_bdim_c_is_leading_tone_diminished():
    result = analyze_v2(["Bdim", "C"], key="C major")
    assert [token.figure for token in result.tokens] == ["viio", "I"]


def test_am_dm_e7_am_authentic_cadence_is_labeled():
    result = analyze_v2(["Am", "Dm", "E7", "Am"], key="A minor")
    assert "authentic cadence" in {relation.name for relation in result.relationships}


def test_ab_bb_c_borrowed_chords_are_labeled():
    result = analyze_v2(["Ab", "Bb", "C"], key="C major")
    assert "Aeolian cadence" in {relation.name for relation in result.relationships}


def test_c_am_f_g_ambiguity_is_flagged():
    assert analyze_v2(["C", "Am", "F", "G"]).ambiguous


def test_extensions_are_preserved_in_the_figure():
    result = analyze_v2(["Cmaj9", "Fadd9", "Gsus4", "C"], key="C major")
    assert [token.figure for token in result.tokens] == ["Imaj9", "IVadd9", "Vsus4", "I"]


def test_inversion_is_preserved_in_the_figure():
    result = analyze_v2(["C", "C/E", "F", "G"], key="C major")
    assert [token.figure for token in result.tokens] == ["I", "I6", "IV", "V"]
