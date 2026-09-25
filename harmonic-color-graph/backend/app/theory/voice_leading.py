"""Deterministic four-part voicings and voice-leading measurements.

The bass respects a slash chord; the upper three parts are chord tones.  All
searches are bounded and use MIDI integers, so this module is safe in the API
hot path and has no music21 or pipeline dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations, product
from typing import Literal

from app.schemas.harmony import CanonicalChord
from app.theory.chord_normalizer import normalize_chord

VoicingStyle = Literal["all", "close", "open", "drop2"]
Strategy = Literal["smooth", "root_position", "spread"]
BASS_MIN, BASS_MAX = 40, 62  # E2–D4
UPPER_MIN, UPPER_MAX = 48, 79  # C3–G5


@dataclass(frozen=True)
class VoiceLeadingMetrics:
    total_motion: int
    max_voice_motion: int
    common_tones: int
    bass_motion: int
    parallel_perfects: int
    parsimonious: str | None
    motions: tuple[int, ...]


def _chord(value: CanonicalChord | str) -> CanonicalChord:
    if isinstance(value, CanonicalChord):
        return value
    result = normalize_chord(value)
    if not result.success or result.chord is None:
        raise ValueError(f"Unparseable chord: {value!r}")
    return result.chord


def _upper_pitch_classes(chord: CanonicalChord) -> list[tuple[int, int, int]]:
    pcs = tuple(dict.fromkeys(chord.pitch_classes))
    if len(pcs) < 2:
        raise ValueError("A chord needs at least two distinct pitch classes")
    if len(pcs) == 2:
        return [(pcs[0], pcs[1], pcs[0])]
    groups = list(combinations(pcs, 3))
    if len(pcs) >= 4:
        # Preserve the characteristic third and seventh in seventh chords.
        third, seventh = pcs[1], pcs[3]
        groups = [group for group in groups if third in group and seventh in group]
    return groups


def generate_voicings(chord: CanonicalChord | str, style: VoicingStyle = "all") -> list[list[int]]:
    """Generate bounded bass + three-upper-part voicings in the stated ranges."""
    if style not in ("all", "close", "open", "drop2"):
        raise ValueError(f"Unknown voicing style: {style}")
    parsed = _chord(chord)
    bass_pc = parsed.bass_pc if parsed.bass_pc is not None else parsed.root_pc
    if bass_pc is None:
        raise ValueError("Chord has no bass pitch class")
    basses = [n for n in range(BASS_MIN, BASS_MAX + 1) if n % 12 == bass_pc]
    found: dict[str, set[tuple[int, ...]]] = {"close": set(), "open": set(), "drop2": set()}
    for group in _upper_pitch_classes(parsed):
        options = [[n for n in range(UPPER_MIN, UPPER_MAX + 1) if n % 12 == pc] for pc in group]
        for pitches in product(*options):
            upper = tuple(sorted(pitches))
            if len(set(upper)) != 3:
                continue
            span = upper[-1] - upper[0]
            if span > 19:
                continue
            kind = "close" if span <= 12 else "open"
            for bass in basses:
                if bass >= upper[0]:
                    continue
                found[kind].add((bass, *upper))
                if kind == "close":
                    dropped = tuple(sorted((upper[0], upper[1] - 12, upper[2])))
                    if dropped[0] >= UPPER_MIN and bass < dropped[0]:
                        found["drop2"].add((bass, *dropped))
    selected = set().union(*found.values()) if style == "all" else found[style]
    # Typical register first, with a deterministic cap on the DP state space.
    ordered = sorted(
        selected,
        key=lambda v: (abs(v[0] - 48) + abs(sum(v[1:]) / 3 - 64), v),
    )
    return [list(v) for v in ordered[:64]]


def _best_assignment(source: tuple[int, ...], target: tuple[int, ...]) -> tuple[int, ...]:
    if len(source) != len(target) or not 2 <= len(source) <= 5:
        raise ValueError("Voicings must have equal size between 2 and 5")
    # Bass is its own voice; exhaustively assign the remaining 1–4 voices.
    return min(
        permutations(target[1:]),
        key=lambda upper: (
            sum(abs(a - b) for a, b in zip(source[1:], upper, strict=True)),
            max(abs(a - b) for a, b in zip(source[1:], upper, strict=True)),
            upper,
        ),
    )


def _parallel_perfects(source: tuple[int, ...], target: tuple[int, ...]) -> int:
    count = 0
    for i, j in combinations(range(len(source)), 2):
        old_interval = abs(source[j] - source[i]) % 12
        new_interval = abs(target[j] - target[i]) % 12
        di, dj = target[i] - source[i], target[j] - source[j]
        if old_interval in (0, 7) and new_interval == old_interval and di * dj > 0:
            count += 1
    return count


def _parsimonious(a: CanonicalChord, b: CanonicalChord) -> str | None:
    if len(set(a.pitch_classes)) != 3 or len(set(b.pitch_classes)) != 3:
        return None
    if {a.quality_class, b.quality_class} != {"maj", "min"}:
        return None
    if len(set(a.pitch_classes) & set(b.pitch_classes)) != 2:
        return None
    if a.root_pc is None or b.root_pc is None:
        return None
    delta = (b.root_pc - a.root_pc) % 12
    if delta == 0:
        return "P"
    if (a.quality_class == "maj" and delta == 4) or (a.quality_class == "min" and delta == 8):
        return "L"
    if (a.quality_class == "maj" and delta == 9) or (a.quality_class == "min" and delta == 3):
        return "R"
    return None


def transition_metrics(
    source: list[int] | tuple[int, ...],
    target: list[int] | tuple[int, ...],
    source_chord: CanonicalChord | str | None = None,
    target_chord: CanonicalChord | str | None = None,
) -> VoiceLeadingMetrics:
    """Measure minimum assigned upper motion, with bass voice held fixed."""
    first, second = tuple(source), tuple(target)
    if any(n < 0 or n > 127 for n in (*first, *second)):
        raise ValueError("MIDI notes must be in 0..127")
    assigned = (second[0], *_best_assignment(first, second))
    motions = tuple(b - a for a, b in zip(first, assigned, strict=True))
    common = len({n % 12 for n in first} & {n % 12 for n in second})
    transform = (
        _parsimonious(_chord(source_chord), _chord(target_chord))
        if source_chord is not None and target_chord is not None
        else None
    )
    return VoiceLeadingMetrics(
        total_motion=sum(map(abs, motions)),
        max_voice_motion=max(map(abs, motions)),
        common_tones=common,
        bass_motion=abs(motions[0]),
        parallel_perfects=_parallel_perfects(first, assigned),
        parsimonious=transform,
        motions=motions,
    )


def _root_voicing(chord: CanonicalChord) -> list[int]:
    choices = generate_voicings(chord, "close")
    if not choices:
        raise ValueError(f"No playable voicing for {chord.symbol}")
    return min(choices, key=lambda v: (abs(v[0] - 48), abs(sum(v[1:]) / 3 - 64), v))


def voice_lead(
    progression: list[CanonicalChord | str] | tuple[CanonicalChord | str, ...],
    strategy: Strategy = "smooth",
) -> list[list[int]]:
    """Return four MIDI notes per chord; smooth minimizes full-path motion."""
    if strategy not in ("smooth", "root_position", "spread"):
        raise ValueError(f"Unknown voice-leading strategy: {strategy}")
    chords = [_chord(chord) for chord in progression]
    if not chords:
        return []
    root_path = [_root_voicing(chord) for chord in chords]
    if strategy == "root_position":
        return root_path
    if strategy == "spread":
        return [
            min(
                generate_voicings(chord, "open")
                or generate_voicings(chord, "drop2")
                or [root_path[i]],
                key=lambda v: (abs(v[0] - 48), abs(sum(v[1:]) / 3 - 64), v),
            )
            for i, chord in enumerate(chords)
        ]

    # Root-position path is always in the search set, making its total-motion
    # cost an upper bound for the smooth strategy on any progression.
    options: list[list[list[int]]] = []
    for chord, root in zip(chords, root_path, strict=True):
        candidates = generate_voicings(chord)
        if root not in candidates:
            candidates.append(root)
        options.append(candidates)
    costs = [(0, 0, 0) for _ in options[0]]
    back: list[list[int]] = []
    for prev, current in zip(options, options[1:], strict=False):
        next_costs: list[tuple[int, int, int]] = []
        predecessors: list[int] = []
        for target in current:
            scored = []
            for i, source in enumerate(prev):
                metrics = transition_metrics(source, target)
                scored.append(
                    (
                        (
                            costs[i][0] + metrics.total_motion,
                            costs[i][1] + metrics.parallel_perfects,
                            max(costs[i][2], metrics.max_voice_motion),
                        ),
                        i,
                    )
                )
            cost, index = min(scored)
            next_costs.append(cost)
            predecessors.append(index)
        costs = next_costs
        back.append(predecessors)
    index = min(range(len(costs)), key=lambda i: (costs[i], i))
    path = [options[-1][index]]
    for step in range(len(back) - 1, -1, -1):
        index = back[step][index]
        path.append(options[step][index])
    return list(reversed(path))
