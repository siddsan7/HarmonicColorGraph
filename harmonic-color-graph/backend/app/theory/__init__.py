"""Music theory, parsing, and analysis modules."""

from app.theory.chord_normalizer import normalize_chord
from app.theory.progression_normalizer import normalize_progression

__all__ = ["normalize_chord", "normalize_progression"]
