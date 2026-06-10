from app.schemas import TransitionRecord

CIRCLE_MOTIONS = {
    ("ii", "V"),
    ("II", "V"),
    ("V", "I"),
    ("vi", "ii"),
    ("VI", "ii"),
}


def label_progression_relationships(
    roman_chords: list[str],
    mode_context: str = "unknown",
) -> list[TransitionRecord]:
    return [
        label_transition(from_roman, to_roman, mode_context)
        for from_roman, to_roman in zip(roman_chords, roman_chords[1:])
    ]


def label_transition(
    from_roman: str,
    to_roman: str,
    mode_context: str = "unknown",
) -> TransitionRecord:
    labels: list[str] = []
    short_explanation = None
    technical_explanation = None

    from_core = _strip_extensions(from_roman)
    to_core = _strip_extensions(to_roman)

    if from_core == "V" and to_core == "I":
        labels.extend(["authentic cadence", "dominant resolution"])
        short_explanation = "Dominant V resolves to tonic I, creating strong closure."
        technical_explanation = (
            "The dominant chord contains scale degree 7, which resolves by "
            "step to tonic in common-practice tonal syntax."
        )

    if from_core == "IV" and to_core == "I":
        labels.append("plagal cadence")
        short_explanation = "IV moves back to I with a softer cadence."
        technical_explanation = (
            "The predominant IV returns to tonic without dominant-leading-tone pull."
        )

    if from_core == "iv" and to_core == "I":
        labels.extend(["minor plagal cadence", "modal interchange"])
        short_explanation = (
            "The borrowed minor iv darkens the major key before resolving to tonic."
        )
        technical_explanation = (
            "The iv chord borrows the lowered sixth scale degree from the "
            "parallel minor, then resolves back to the major tonic."
        )

    if from_core == "V" and to_core == "vi":
        labels.append("deceptive cadence")
        short_explanation = (
            "V sets up tonic resolution but moves to vi instead, creating a detour."
        )
        technical_explanation = (
            "The dominant expectation is diverted to the submediant rather than I."
        )

    if (from_core, to_core) in CIRCLE_MOTIONS:
        labels.append("circle-of-fifths motion")

    if from_core.startswith("V/") and to_core == from_core.split("/", 1)[1]:
        labels.append("secondary dominant")

    if from_core == "bII" and to_core == "I":
        labels.extend(["tritone substitution", "subV-like resolution"])
        short_explanation = (
            "bII7 resolves down by half step to I, creating a strong chromatic pull."
        )
        technical_explanation = (
            "In a major-key context, bII7 can behave like a substitute dominant "
            "because its guide tones overlap with V7-related voice leading."
        )

    if _is_chromatic_mediant(from_core, to_core):
        labels.append("chromatic mediant")

    labels = list(dict.fromkeys(labels))
    return TransitionRecord(
        from_roman=from_roman,
        to_roman=to_roman,
        mode_context=mode_context,  # type: ignore[arg-type]
        relationship_labels=labels,
        short_explanation=short_explanation or _default_short_explanation(labels),
        technical_explanation=technical_explanation
        or _default_technical_explanation(labels),
    )


def _strip_extensions(roman: str) -> str:
    stripped = roman.replace("maj7", "")
    for suffix in ("7b5", "7", "6", "9", "11", "13"):
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)]
    return stripped


def _is_chromatic_mediant(from_core: str, to_core: str) -> bool:
    pairs = {
        ("I", "bIII"),
        ("I", "bVI"),
        ("i", "III"),
        ("i", "VI"),
        ("bIII", "I"),
        ("bVI", "I"),
    }
    return (from_core, to_core) in pairs


def _default_short_explanation(labels: list[str]) -> str | None:
    if not labels:
        return None
    return f"This transition is associated with {', '.join(labels)}."


def _default_technical_explanation(labels: list[str]) -> str | None:
    if not labels:
        return None
    return "The labels come from rule-based Roman numeral relationship analysis."
