"""Registry of evidence-bearing harmonic relationships over RomanToken sequences."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.schemas.analysis_v2 import RelationshipFact, RomanToken

Detector = Callable[[Sequence[RomanToken], bool], bool]


@dataclass(frozen=True)
class RelationshipRule:
    id: str
    name: str
    category: str
    arity: int
    modes: tuple[str, ...]
    detector: Detector
    fact_template: str
    technical_template: str


def _base(token: RomanToken) -> str:
    figure = token.figure.split("/", 1)[0]
    for suffix in (
        "maj13",
        "maj11",
        "maj9",
        "maj7",
        "add13",
        "add11",
        "add9",
        "sus4",
        "sus2",
        "h7",
        "o7",
        "65",
        "64",
        "43",
        "42",
        "13",
        "11",
        "9",
        "7",
        "6",
        "o",
        "+",
    ):
        if figure.endswith(suffix):
            return figure[: -len(suffix)]
    return figure


def _root_motion(window: Sequence[RomanToken]) -> int:
    return (window[1].root_pc - window[0].root_pc) % 12


def _shared(window: Sequence[RomanToken]) -> int:
    return len(set(window[0].pitch_classes) & set(window[1].pitch_classes))


def _rule(
    id: str,
    name: str,
    category: str,
    arity: int,
    detector: Detector,
    short: str,
    technical: str,
    modes: tuple[str, ...] = ("major", "minor"),
) -> RelationshipRule:
    return RelationshipRule(id, name, category, arity, modes, detector, short, technical)


RULES: tuple[RelationshipRule, ...] = (
    _rule(
        "authentic",
        "authentic cadence",
        "cadence",
        2,
        lambda w, _: _base(w[0]) in {"V", "vii"} and _base(w[1]) in {"I", "i"},
        "Dominant harmony tends to settle on the tonic here.",
        "A V or leading-tone chord resolves to the tonic in this key.",
    ),
    _rule(
        "half",
        "half cadence",
        "cadence",
        2,
        lambda w, end: end and _base(w[1]) == "V" and _base(w[0]) not in {"V", "vii"},
        "The phrase pauses on the dominant, leaving a sense of continuation.",
        "The final chord is V rather than a tonic resolution.",
    ),
    _rule(
        "plagal",
        "plagal cadence",
        "cadence",
        2,
        lambda w, _: _base(w[0]) == "IV" and _base(w[1]) in {"I", "i"},
        "IV returns to the tonic with a gentle sense of arrival.",
        "Subdominant harmony resolves directly to the tonic.",
    ),
    _rule(
        "minor_plagal",
        "minor plagal cadence",
        "cadence",
        2,
        lambda w, _: _base(w[0]) == "iv" and _base(w[1]) == "I",
        "Borrowed iv adds color before the major tonic returns.",
        "The lowered sixth in iv moves toward the fifth of I.",
    ),
    _rule(
        "deceptive",
        "deceptive cadence",
        "cadence",
        2,
        lambda w, _: _base(w[0]) == "V" and _base(w[1]) in {"vi", "VI", "bVI"},
        "The dominant moves to a submediant instead of the tonic.",
        "V diverts its expected tonic resolution to vi, VI, or bVI.",
    ),
    _rule(
        "secondary_dominant",
        "secondary dominant",
        "functional",
        2,
        lambda w, _: w[0].applied_role == "V" and w[0].applied_to == _base(w[1]),
        "An applied dominant points toward the following chord.",
        "The first chord is V of the following diatonic target.",
    ),
    _rule(
        "applied_lt",
        "applied leading tone",
        "functional",
        2,
        lambda w, _: w[0].applied_role == "viio" and w[0].applied_to == _base(w[1]),
        "An applied leading-tone chord leads into its target.",
        "The diminished root rises by semitone to its target root.",
    ),
    _rule(
        "tritone_sub",
        "tritone substitution",
        "chromatic",
        2,
        lambda w, _: w[0].applied_role == "subV" and _root_motion(w) == 11,
        "A substitute dominant slides down into its target.",
        "The dominant seventh a semitone above the target substitutes for V7.",
    ),
    _rule(
        "backdoor",
        "backdoor resolution",
        "cadence",
        2,
        lambda w, _: _base(w[0]) == "bVII" and w[0].quality_class == "dom7" and _base(w[1]) == "I",
        "The flat-seven dominant approaches the tonic from the backdoor.",
        "bVII7 resolves to I without the leading tone of V7.",
    ),
    _rule(
        "backdoor_three",
        "backdoor progression",
        "cadence",
        3,
        lambda w, _: (
            _base(w[0]) == "iv"
            and _base(w[1]) == "bVII"
            and w[1].quality_class == "dom7"
            and _base(w[2]) == "I"
        ),
        "Minor subdominant prepares a backdoor arrival on I.",
        "iv7–bVII7–I combines parallel-minor mixture with bVII dominant motion.",
    ),
    _rule(
        "aeolian",
        "Aeolian cadence",
        "modal",
        3,
        lambda w, _: _base(w[0]) == "bVI" and _base(w[1]) == "bVII" and _base(w[2]) == "I",
        "Borrowed flat-six and flat-seven chords rise into the tonic.",
        "bVI–bVII–I draws on parallel-minor scale degrees.",
    ),
    _rule(
        "double_plagal",
        "double plagal cadence",
        "cadence",
        3,
        lambda w, _: _base(w[0]) == "bVII" and _base(w[1]) == "IV" and _base(w[2]) == "I",
        "Two subdominant moves lead into the tonic.",
        "bVII–IV–I descends by fourth-related roots.",
    ),
    _rule(
        "circle_fifths",
        "circle-of-fifths motion",
        "functional",
        2,
        lambda w, _: _root_motion(w) == 5,
        "The roots move by a descending fifth.",
        "The second root lies a perfect fifth below the first modulo octave.",
    ),
    _rule(
        "chromatic_mediant",
        "chromatic mediant",
        "chromatic",
        2,
        lambda w, _: (
            _root_motion(w) in {3, 4, 8, 9}
            and _shared(w) == 1
            and w[0].quality_class in {"maj", "min"}
            and w[1].quality_class in {"maj", "min"}
        ),
        "Third-related chords share a tone while changing harmonic color.",
        "Major/minor triads a chromatic third apart share exactly one pitch class.",
    ),
    _rule(
        "relative",
        "relative-key chord relation",
        "functional",
        2,
        lambda w, _: {_base(w[0]), _base(w[1])} == {"I", "vi"},
        "Tonic and relative-minor chords share much of their pitch content.",
        "I and vi are related by a minor third and two common tones.",
    ),
    _rule(
        "parallel",
        "parallel-mode chord relation",
        "modal",
        2,
        lambda w, _: {_base(w[0]), _base(w[1])} == {"I", "i"},
        "The tonic changes mode while keeping its root.",
        "Major and minor tonic triads differ in their third.",
    ),
    _rule(
        "picardy",
        "Picardy third",
        "cadence",
        2,
        lambda w, end: (
            end
            and w[0].mode == "minor"
            and _base(w[0]) in {"V", "vii", "iv"}
            and _base(w[1]) == "I"
            and w[1].quality_class == "maj"
        ),
        "A major tonic closes a minor-key phrase with a brighter color.",
        "The final tonic raises the third relative to the minor mode.",
        ("minor",),
    ),
    _rule(
        "stepwise_bass",
        "stepwise bass motion",
        "voice_leading",
        2,
        lambda w, _: (w[1].bass_pc - w[0].bass_pc) % 12 in {1, 2, 10, 11},
        "The bass moves by step between these chords.",
        "The bass pitch classes are separated by one or two semitones.",
    ),
    _rule(
        "common_tone",
        "common-tone motion",
        "voice_leading",
        2,
        lambda w, _: _shared(w) >= 2,
        "The chords retain at least two common tones.",
        "Their pitch-class sets overlap in at least two places.",
    ),
    _rule(
        "neapolitan_to_v",
        "Neapolitan to dominant",
        "functional",
        2,
        lambda w, _: "neapolitan" in w[0].tags and _base(w[1]) == "V",
        "The flat-two chord prepares the dominant.",
        "A major bII functions as a predominant before V.",
    ),
)


def analyze_relationships(tokens: Sequence[RomanToken]) -> list[RelationshipFact]:
    facts: list[RelationshipFact] = []
    for rule in RULES:
        for index in range(len(tokens) - rule.arity + 1):
            window = tokens[index : index + rule.arity]
            if window[0].mode not in rule.modes or any(t.mode != window[0].mode for t in window):
                continue
            if not rule.detector(window, index + rule.arity == len(tokens)):
                continue
            last = index + rule.arity - 1
            fact_id = f"relationship:{rule.id}:{index}:{last}"
            facts.append(
                RelationshipFact(
                    id=rule.id,
                    name=rule.name,
                    category=rule.category,
                    from_index=index,
                    to_index=last,
                    short_explanation=rule.fact_template,
                    technical_explanation=rule.technical_template,
                    fact_ids=[fact_id],
                )
            )
    return sorted(facts, key=lambda fact: (fact.from_index, fact.to_index, fact.id))
