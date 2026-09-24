"""F30: `realize(core_token, key) -> RealizedChord`, the inverse of
`app.theory.roman.romanize_chord` restricted to the `.core` string it
produces (mode-aware Roman numeral + quality suffix, with an optional
`/applied_to` target -- never inversions or 9/11/13 extensions, since
`romanize_chord` never puts those in `.core`, only in `.figure`).

Spelling follows F10: the letter comes from the numeral's own scale-degree
position (via `app.theory.spelling.diatonic_letters_and_pitch_classes`),
never from a generic minimum-accidental heuristic, so a borrowed `bVI` in
Eb major spells as C-flat (the key's own 6th-degree letter, flattened),
not the enharmonically simpler B.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.harmony import CanonicalChord
from app.theory.chord_normalizer import normalize_chord
from app.theory.roman import MAJOR_DEGREES, MINOR_DEGREES, NUMERALS, parse_key
from app.theory.spelling import (
    LETTERS,
    NATURAL_PITCH_CLASS,
    diatonic_letters_and_pitch_classes,
    spell,
)

# Reverse of roman.py's degree -> semitone tables. MAJOR_DEGREES is a
# bijection (12 semitones, 12 distinct (degree, accidental) pairs);
# MINOR_DEGREES is not -- semitones 10 and 11 both mean "degree 7, no
# accidental" (natural minor's b7 and the raised leading tone are both
# just "vii" in this scheme, a genuine ambiguity already present in the
# forward analyzer, not something realize() can recover). Iterating
# ascending semitones with `setdefault` keeps the lower (natural-minor b7)
# semitone for that duplicate -- a deliberate, documented default rather
# than an accident of dict ordering.
_MAJOR_INTERVAL_FOR: dict[tuple[int, str], int] = {}
for _semitone, _pair in MAJOR_DEGREES.items():
    _MAJOR_INTERVAL_FOR.setdefault(_pair, _semitone)

_MINOR_INTERVAL_FOR: dict[tuple[int, str], int] = {}
for _semitone in sorted(MINOR_DEGREES):
    _MINOR_INTERVAL_FOR.setdefault(MINOR_DEGREES[_semitone], _semitone)

# Applied-chord markers (`romanize_chord`'s literal `base` values when
# `applied_to` is set): the chord's root and spelling letter are relative
# to its TARGET, not the tonic. `pc_offset` is in semitones, `letter_offset`
# in 7-letter-alphabet steps, both measured from the target's own
# root/letter -- see the module docstring's Eb example: V/V's root is a
# 5th (letter F) above the target V's own letter (B). `is_major_family`
# is forced by the marker (an applied dominant is always major/dom7-family
# regardless of what it resolves to), not derived from the marker text's
# case the way a plain numeral's is.
_APPLIED_MARKERS: dict[str, tuple[int, int, bool]] = {
    # marker: (pc_offset, letter_offset, is_major_family)
    "V": (7, 4, True),
    "vii": (11, 6, False),
    "subV": (1, 1, True),
}

# `_quality_suffix` in roman.py, inverted. Keyed by (suffix, is_major_family)
# since "" and "7" are each ambiguous between a major- and minor-family
# quality on their own (the numeral's letter case is what disambiguates
# them in the forward direction; for applied markers, `is_major_family` is
# forced -- see `_APPLIED_MARKERS`).
_QUALITY_FOR_SUFFIX: dict[tuple[str, bool], str] = {
    ("", True): "maj",
    ("", False): "min",
    ("7", True): "dom7",
    ("7", False): "min7",
    ("maj7", True): "maj7",
    ("maj7", False): "minmaj7",
    ("o", True): "dim",
    ("o", False): "dim",
    ("o7", True): "dim7",
    ("o7", False): "dim7",
    ("h7", True): "hdim7",
    ("h7", False): "hdim7",
    ("+", True): "aug",
    ("+", False): "aug",
    ("sus2", True): "sus2",
    ("sus2", False): "sus2",
    ("sus4", True): "sus4",
    ("sus4", False): "sus4",
    ("5", True): "power",
    ("5", False): "power",
}

# quality_class -> a symbol suffix `chord_normalizer.normalize_chord` can
# parse back (via its QUALITY_ALIASES), chosen so `classify_chord_intervals`
# round-trips to the same quality_class.
_SYMBOL_SUFFIX_FOR_QUALITY = {
    "maj": "",
    "min": "m",
    "dom7": "7",
    "min7": "m7",
    "maj7": "maj7",
    "minmaj7": "minmaj7",
    "dim": "dim",
    "dim7": "dim7",
    "hdim7": "m7b5",
    "aug": "aug",
    "sus2": "sus2",
    "sus4": "sus4",
    "power": "no3",
}

# Longest-first so the regex below never matches "I" as a prefix of "IV"
# etc (Python `re` alternation is first-match, not longest-match).
_NUMERAL_ALTERNATION = "|".join(
    sorted((*NUMERALS, *(n.lower() for n in NUMERALS)), key=len, reverse=True)
)
_NUMERAL_PATTERN = re.compile(rf"^(b|#)?({_NUMERAL_ALTERNATION})(.*)$")


@dataclass(frozen=True)
class RealizedChord:
    core_token: str
    key: str
    chord: CanonicalChord
    # Set only when the theoretically correct spelling needs 2+ sharps or
    # flats on one letter (e.g. a double flat): a plain-language
    # alternative for display, alongside (never instead of) the correct one.
    display_enharmonic: str | None


def realize(core_token: str, key: str) -> RealizedChord:
    mode_letter, separator, rest = core_token.partition(":")
    if separator != ":" or mode_letter not in ("M", "m"):
        raise ValueError(f"Not a core token (expected 'M:...' or 'm:...'): {core_token!r}")
    tonic_pc, tonic_mode, normalized_key = parse_key(key)
    diatonic = diatonic_letters_and_pitch_classes(normalized_key)

    base_str, has_target, target_str = rest.partition("/")
    if has_target:
        root_pc, letter, suffix, is_major_family = _resolve_applied(
            base_str, target_str, tonic_pc, tonic_mode, diatonic
        )
    else:
        degree, accidental, suffix, is_major_family = _split_numeral(base_str)
        root_pc = (tonic_pc + _interval_for(degree, accidental, tonic_mode)) % 12
        letter = diatonic[degree - 1][0]

    quality = _QUALITY_FOR_SUFFIX.get((suffix, is_major_family))
    if quality is None:
        raise ValueError(f"Unrecognized quality suffix {suffix!r} in {core_token!r}")
    return _build(core_token, normalized_key, root_pc, letter, quality)


def _resolve_applied(
    base_str: str,
    target_str: str,
    tonic_pc: int,
    tonic_mode: str,
    diatonic: list[tuple[str, int]],
) -> tuple[int, str, str, bool]:
    marker = next((m for m in _APPLIED_MARKERS if base_str.startswith(m)), None)
    if marker is None:
        raise ValueError(f"Unrecognized applied-chord marker in {base_str!r}")
    suffix = base_str[len(marker) :]
    pc_offset, letter_offset, is_major_family = _APPLIED_MARKERS[marker]

    target_degree, target_accidental, _target_suffix, _target_family = _split_numeral(target_str)
    target_pc = (tonic_pc + _interval_for(target_degree, target_accidental, tonic_mode)) % 12
    target_letter = diatonic[target_degree - 1][0]

    root_pc = (target_pc + pc_offset) % 12
    letter = LETTERS[(LETTERS.index(target_letter) + letter_offset) % 7]
    return root_pc, letter, suffix, is_major_family


def _split_numeral(numeral_str: str) -> tuple[int, str, str, bool]:
    match = _NUMERAL_PATTERN.match(numeral_str)
    if match is None:
        raise ValueError(f"Not a Roman numeral: {numeral_str!r}")
    accidental, numeral_text, suffix = match.groups()
    degree = NUMERALS.index(numeral_text.upper()) + 1
    is_major_family = numeral_text == numeral_text.upper()
    return degree, accidental or "", suffix, is_major_family


def _interval_for(degree: int, accidental: str, mode: str) -> int:
    table = _MAJOR_INTERVAL_FOR if mode == "major" else _MINOR_INTERVAL_FOR
    key = (degree, accidental)
    if key not in table:
        raise ValueError(f"No {mode} scale degree {accidental}{degree}")
    return table[key]


def _build(core_token: str, key: str, root_pc: int, letter: str, quality: str) -> RealizedChord:
    spelled_root = spell(root_pc, letter)
    # A double (or worse) accidental can't be represented at all --
    # `CanonicalChord`/`normalize_chord` only parse a single sharp or flat
    # per letter. When the theoretically correct spelling needs one (e.g.
    # a Neapolitan built on an already-flat scale degree), fall back to the
    # plainer, always-representable spelling (`_minimal_spelling` never
    # needs more than one accidental: every pitch class is within a
    # semitone of *some* natural letter, since no two adjacent naturals
    # are more than a tone apart) and surface the theoretically intended
    # name via `display_enharmonic` instead of the usual way around. Below
    # that threshold (0-1 accidentals), the correct spelling is always
    # constructible and stays primary, with no enharmonic offered -- e.g.
    # bVI in Eb major stays "Cb", not "B" (see the module docstring).
    if len(spelled_root) - 1 >= 2:
        primary_root, display = _minimal_spelling(root_pc), spelled_root
    else:
        primary_root, display = spelled_root, None

    symbol = primary_root + _SYMBOL_SUFFIX_FOR_QUALITY[quality]
    result = normalize_chord(symbol)
    if not result.success or result.chord is None:
        raise ValueError(f"Could not realize {core_token!r} in {key!r} (built {symbol!r})")
    return RealizedChord(
        core_token=core_token, key=key, chord=result.chord, display_enharmonic=display
    )


def _minimal_spelling(pc: int) -> str:
    best_letter, best_delta = "C", None
    for letter, natural_pc in NATURAL_PITCH_CLASS.items():
        delta = (pc - natural_pc) % 12
        if delta > 6:
            delta -= 12
        if best_delta is None or abs(delta) < abs(best_delta):
            best_letter, best_delta = letter, delta
    return spell(pc, best_letter)
