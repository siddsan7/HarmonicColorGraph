"""Letter-name spelling: line-of-fifths arithmetic, key-aware note names, and
chord-tone spelling derived from a chord's semitone interval pattern.

Every function here is pure pitch-class arithmetic plus letter-alphabet
bookkeeping; nothing depends on `CanonicalChord` so `theory/chord_normalizer.py`
can depend on this module without a cycle.
"""

from collections.abc import Sequence
from dataclasses import dataclass

LETTERS = "CDEFGAB"

NATURAL_PITCH_CLASS = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

# Full note-name -> pitch-class table (naturals plus single sharps/flats),
# the canonical source `theory/chord_normalizer.py` re-exports.
NOTE_TO_PITCH_CLASS = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "Fb": 4,
    "E#": 5,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
    "B#": 0,
}

# Base line-of-fifths index for each natural letter (F=-1 .. B=5); each "#"
# adds 7, each "b" subtracts 7 (a chromatic semitone is 7 fifths).
LOF_BASE = {
    "F": -1,
    "C": 0,
    "G": 1,
    "D": 2,
    "A": 3,
    "E": 4,
    "B": 5,
}

# Chord-degree letter offsets (0-6 letters above the root) keyed by the
# root-relative semitone interval, for tones that are not the chord's third
# or seventh (which depend on where they sit in the interval list, not just
# their raw value). Used for 9/11/13 extensions wherever they land.
_EXTENSION_LETTER_OFFSET = {1: 1, 2: 1, 3: 1, 5: 3, 6: 3, 8: 5, 9: 5}
_EXTENSION_LABEL = {1: "b9", 2: "9", 3: "#9", 5: "11", 6: "#11", 8: "b13", 9: "13"}

InversionLabel = str  # "root" | "first" | "second" | "third" | "other"


@dataclass(frozen=True)
class ChordQualityInfo:
    """Everything derivable from a chord's semitone interval list alone."""

    quality_class: str
    extensions: list[str]
    letter_offsets: list[int]


def spell(pc: int, letter: str) -> str:
    """Spell pitch class `pc` using `letter`, choosing the accidental that
    makes the letter's natural pitch class equal `pc` (mod 12), picking the
    smallest-magnitude accidental (ties resolve toward sharps).
    """
    letter = letter.upper()
    natural = NATURAL_PITCH_CLASS[letter]
    delta = (pc - natural) % 12
    if delta > 6:
        delta -= 12
    if delta == 0:
        return letter
    if delta > 0:
        return letter + ("#" * delta)
    return letter + ("b" * -delta)


def lof(note: str) -> int:
    """Line-of-fifths index: C=0, each fifth up (sharpward) is +1, each
    fifth down (flatward) is -1. `lof("G#") == 8`, `lof("Ab") == -4`.
    """
    letter = note[0].upper()
    accidentals = note[1:]
    count = accidentals.count("#") - accidentals.count("b")
    return LOF_BASE[letter] + 7 * count


def _parse_key(key: str) -> tuple[str, str, str]:
    """Return (tonic_letter, tonic_note, mode) for a "<Root> <major|minor>" key string."""
    parts = key.strip().split()
    root = parts[0][0].upper() + parts[0][1:]
    mode = parts[1].lower() if len(parts) > 1 else "major"
    return root[0], root, mode


_MAJOR_SCALE_STEPS = (0, 2, 4, 5, 7, 9, 11)
_NATURAL_MINOR_SCALE_STEPS = (0, 2, 3, 5, 7, 8, 10)


def diatonic_letters_and_pitch_classes(key: str) -> list[tuple[str, int]]:
    """The 7 (letter, pitch_class) scale degrees for a major or natural-minor key,
    one letter per staff position, starting from the tonic.
    """
    tonic_letter, tonic_note, mode = _parse_key(key)
    tonic_pc = _note_to_pc(tonic_note)
    steps = _MAJOR_SCALE_STEPS if mode == "major" else _NATURAL_MINOR_SCALE_STEPS
    start_index = LETTERS.index(tonic_letter)
    return [
        (LETTERS[(start_index + degree) % 7], (tonic_pc + step) % 12)
        for degree, step in enumerate(steps)
    ]


def spell_in_key(pc: int, key: str) -> str:
    """Spell pitch class `pc` in `key`.

    A pc that is one of the key's 7 diatonic scale degrees is spelled with
    that degree's own letter, even when it costs an "extra" accidental
    (F# major's 7th is E#, not the enharmonically-simpler F) - each of the
    7 letters is used exactly once per octave, the structural rule real key
    signatures follow.

    A chromatic (non-diatonic) pc instead gets whichever letter needs the
    fewest accidentals (Ab major's borrowed/altered tones spell as C or Eb,
    never B# or D#). A true tie on accidental count (e.g. pc 6 = F#/Gb)
    breaks toward the direction matching the key's own signature (sharp
    keys prefer sharps, flat keys prefer flats); a remaining tie (the
    raised leading tone) prefers sharpening the degree below over
    flattening the one above (G# in A minor, not Ab).
    """
    diatonic_by_pc = {
        degree_pc: letter for letter, degree_pc in diatonic_letters_and_pitch_classes(key)
    }
    if pc in diatonic_by_pc:
        return spell(pc, diatonic_by_pc[pc])

    _tonic_letter, tonic_note, mode = _parse_key(key)
    signature_lof = lof(tonic_note) if mode == "major" else lof(tonic_note) - 3
    prefer_sharps = signature_lof >= 0

    best_letter = "C"
    best_rank: tuple[int, int, int] | None = None
    for letter in LETTERS:
        natural = NATURAL_PITCH_CLASS[letter]
        delta = (pc - natural) % 12
        if delta > 6:
            delta -= 12
        magnitude = abs(delta)
        direction_penalty = 0 if delta == 0 or (delta > 0) == prefer_sharps else 1
        secondary = 0 if delta >= 0 else 1
        rank = (magnitude, direction_penalty, secondary)
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_letter = letter
    return spell(pc, best_letter)


def classify_chord_intervals(intervals: Sequence[int]) -> ChordQualityInfo:
    """Derive quality_class, extensions, and per-tone letter offsets purely
    from a chord's root-relative semitone interval list (QUALITY_INTERVALS
    order: root, third-slot, fifth-slot, seventh-slot, then extensions).
    """
    intervals = list(intervals)
    if intervals == [0, 7]:
        return ChordQualityInfo(quality_class="power", extensions=[], letter_offsets=[0, 4])

    third = intervals[1] if len(intervals) > 1 else None
    fifth = intervals[2] if len(intervals) > 2 else None
    seventh_slot = intervals[3] if len(intervals) > 3 else None

    third_letter_offset = 2
    seventh: int | None = None

    if third in (2, 5):
        quality_class = "sus"
        third_letter_offset = 1 if third == 2 else 3
        seventh = seventh_slot if seventh_slot in (10, 11) else None
    elif third == 3 and fifth == 6:
        seventh = seventh_slot if seventh_slot in (9, 10) else None
        quality_class = {9: "dim7", 10: "hdim7"}.get(seventh, "dim")
    elif third == 3:
        seventh = seventh_slot if seventh_slot in (10, 11) else None
        quality_class = {10: "min7", 11: "minmaj7"}.get(seventh, "min")
    elif third == 4 and fifth == 8:
        seventh = seventh_slot if seventh_slot in (10, 11) else None
        quality_class = {10: "dom7", 11: "maj7"}.get(seventh, "aug")
    elif third == 4:
        seventh = seventh_slot if seventh_slot in (10, 11) else None
        quality_class = {10: "dom7", 11: "maj7"}.get(seventh, "maj")
    else:
        seventh = seventh_slot if seventh_slot in (10, 11) else None
        quality_class = "maj"

    consumed_positions = {0}
    if len(intervals) > 1:
        consumed_positions.add(1)
    if len(intervals) > 2:
        consumed_positions.add(2)
    if seventh is not None:
        consumed_positions.add(3)

    extensions: list[str] = []
    letter_offsets = [0]
    if len(intervals) > 1:
        letter_offsets.append(third_letter_offset)
    if len(intervals) > 2:
        letter_offsets.append(4)
    for position in range(3, len(intervals)):
        interval = intervals[position]
        if position in consumed_positions:
            letter_offsets.append(6)
            continue
        label = _EXTENSION_LABEL.get(interval)
        if label:
            extensions.append(label)
        letter_offsets.append(_EXTENSION_LETTER_OFFSET.get(interval, 6))

    return ChordQualityInfo(
        quality_class=quality_class, extensions=extensions, letter_offsets=letter_offsets
    )


def spell_chord_tones(root: str, intervals: Sequence[int]) -> list[str]:
    """Spell every chord tone by stacking letters (thirds, with sus/power
    overrides) from the root letter, e.g. Ab major -> ["Ab", "C", "Eb"], never
    ["G#", "C", "D#"].
    """
    root_letter = root[0].upper()
    root_pc = _note_to_pc(root)
    info = classify_chord_intervals(intervals)
    root_index = LETTERS.index(root_letter)
    tones = []
    for interval, offset in zip(intervals, info.letter_offsets, strict=True):
        letter = LETTERS[(root_index + offset) % 7]
        pc = (root_pc + interval) % 12
        tones.append(spell(pc, letter))
    return tones


def compute_interval_vector(pitch_classes: Sequence[int]) -> list[int]:
    """Standard 6-entry interval-class vector <ic1..ic6> for a pitch-class set."""
    unique_pcs = sorted(set(pitch_classes))
    vector = [0, 0, 0, 0, 0, 0]
    for i in range(len(unique_pcs)):
        for j in range(i + 1, len(unique_pcs)):
            diff = abs(unique_pcs[i] - unique_pcs[j])
            interval_class = min(diff, 12 - diff)
            vector[interval_class - 1] += 1
    return vector


def compute_pc_set_mask(pitch_classes: Sequence[int]) -> int:
    """12-bit mask of which pitch classes are present."""
    mask = 0
    for pc in pitch_classes:
        mask |= 1 << (pc % 12)
    return mask


def detect_inversion(root_pc: int, bass_pc: int, pitch_classes: Sequence[int]) -> InversionLabel:
    """root/first/second/third by the bass's position in the stacked-third
    pitch-class list, or "other" when the bass isn't a chord tone in that stack.
    """
    if bass_pc == root_pc:
        return "root"
    labels = ["root", "first", "second", "third"]
    for index, pc in enumerate(pitch_classes):
        if pc == bass_pc and index < len(labels):
            return labels[index]
    return "other"


def _note_to_pc(note: str) -> int:
    return NOTE_TO_PITCH_CLASS[note]
