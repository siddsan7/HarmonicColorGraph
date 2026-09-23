"""F11: fit `theory/keys.py`'s score weights and softmax temperature on the
dev half of `data/gold/keys.jsonl`, freeze the winner in
`theory/keys_params.json`, and report dev/test metrics for `docs/eval/keys.md`.

Each of the gold set's 20 templates was transposed to 4 tonics (C, Eb, F#,
A); the C and F# transpositions form the dev half, Eb and A form the held-out
test half, so every template is represented in both.
"""

import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path

from app.theory.chord_normalizer import normalize_chord
from app.theory.keys import (
    ALL_CANDIDATES,
    PROFILES,
    KeyCandidate,
    _cadence_features,
    _chord_fit_share,
    _minor_plagal_count,
    _pearson_correlation,
    _rotate_profile_to_absolute_pcs,
    salience_vector,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_PATH = REPO_ROOT / "data" / "gold" / "keys.jsonl"
PARAMS_PATH = REPO_ROOT / "backend" / "app" / "theory" / "keys_params.json"
REPORT_PATH = REPO_ROOT / "docs" / "eval" / "keys.md"

DEV_TONIC_LETTERS = {"C", "F#"}
TEST_TONIC_LETTERS = {"Eb", "A"}

Features = tuple[float, float, float, float, float, float]


@dataclass(frozen=True)
class GoldItem:
    template: str
    tonic_letter: str
    targets: list[str]  # 1 exact key, or every acceptable_keys entry
    notes: str


def load_gold_items() -> list[GoldItem]:
    items = []
    with GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            targets = raw["acceptable_keys"] if "acceptable_keys" in raw else [raw["key"]]
            # Split dev/test by transposition tonic, taken from the recorded
            # key (first target's tonic letter), not the first chord's root.
            tonic_letter = targets[0].split()[0]
            items.append(
                GoldItem(
                    template=raw["template"],
                    tonic_letter=tonic_letter,
                    targets=targets,
                    notes=raw.get("notes", ""),
                )
            )
    return items


def parse_gold_chords() -> list[list]:
    chord_lists = []
    with GOLD_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            chords = []
            for symbol in raw["chords"]:
                result = normalize_chord(symbol)
                if result.chord is None:
                    raise ValueError(f"gold chord failed to parse: {symbol!r} in {raw}")
                chords.append(result.chord)
            chord_lists.append(chords)
    return chord_lists


def precompute_features(chord_lists: list[list]) -> list[dict[str, dict[KeyCandidate, Features]]]:
    all_features = []
    for chords in chord_lists:
        salience = salience_vector(chords)
        per_profile: dict[str, dict[KeyCandidate, Features]] = {}
        for profile_name, (profile_major, profile_minor) in PROFILES.items():
            per_candidate: dict[KeyCandidate, Features] = {}
            for candidate in ALL_CANDIDATES:
                profile = profile_major if candidate.mode == "major" else profile_minor
                aligned = _rotate_profile_to_absolute_pcs(profile, candidate.tonic_pc)
                correlation = _pearson_correlation(salience, aligned)
                chord_fit = _chord_fit_share(chords, candidate.tonic_pc, candidate.mode)
                cadence, final_is_tonic, first_is_tonic = _cadence_features(
                    chords, candidate.tonic_pc
                )
                per_candidate[candidate] = (
                    correlation,
                    chord_fit,
                    cadence,
                    final_is_tonic,
                    first_is_tonic,
                    _minor_plagal_count(chords, candidate.tonic_pc),
                )
            per_profile[profile_name] = per_candidate
        all_features.append(per_profile)
    return all_features


def softmax_estimates(
    features: dict[KeyCandidate, Features], weights: dict[str, float], temperature: float
) -> list[tuple[KeyCandidate, float]]:
    scores = {}
    for candidate, (
        corr,
        fit,
        cadence,
        final_is_tonic,
        first_is_tonic,
        minor_plagal,
    ) in features.items():
        scores[candidate] = (
            weights["profile_correlation"] * corr
            + weights["chord_fit"] * fit
            + weights["cadence_count"] * cadence
            + weights["final_is_tonic"] * final_is_tonic
            + weights["first_is_tonic"] * first_is_tonic
            + weights["minor_plagal"] * minor_plagal
        )
    max_score = max(scores.values())
    exp_scores = {c: math.exp((s - max_score) / temperature) for c, s in scores.items()}
    total = sum(exp_scores.values())
    return sorted(
        ((c, exp_scores[c] / total) for c in scores), key=lambda pair: pair[1], reverse=True
    )


def evaluate(
    items: list[GoldItem],
    all_features: list[dict[str, dict[KeyCandidate, Features]]],
    indices: list[int],
    profile: str,
    weights: dict[str, float],
    temperature: float,
) -> dict:
    top1_hits = 0
    top2_hits = 0
    probs_for_ece: list[tuple[float, bool]] = []
    for index in indices:
        item = items[index]
        estimates = softmax_estimates(all_features[index][profile], weights, temperature)
        top1_key = estimates[0][0].key
        top2_keys = {estimates[0][0].key, estimates[1][0].key}
        if top1_key in item.targets:
            top1_hits += 1
        if top2_keys & set(item.targets):
            top2_hits += 1
        probs_for_ece.append((estimates[0][1], top1_key in item.targets))
    n = len(indices)
    return {
        "top1": top1_hits / n,
        "top2": top2_hits / n,
        "ece": expected_calibration_error(probs_for_ece),
    }


def expected_calibration_error(
    probs_and_correctness: list[tuple[float, bool]], bins: int = 10
) -> float:
    if not probs_and_correctness:
        return 0.0
    bucket_totals = [0] * bins
    bucket_correct = [0] * bins
    bucket_confidence = [0.0] * bins
    for probability, correct in probs_and_correctness:
        bucket = min(int(probability * bins), bins - 1)
        bucket_totals[bucket] += 1
        bucket_correct[bucket] += int(correct)
        bucket_confidence[bucket] += probability
    n = len(probs_and_correctness)
    ece = 0.0
    for total, correct, confidence in zip(
        bucket_totals, bucket_correct, bucket_confidence, strict=True
    ):
        if total == 0:
            continue
        accuracy = correct / total
        mean_confidence = confidence / total
        ece += (total / n) * abs(accuracy - mean_confidence)
    return ece


def grid_search(
    items: list[GoldItem],
    all_features: list[dict[str, dict[KeyCandidate, Features]]],
    dev_indices: list[int],
) -> tuple[str, dict[str, float], float, float]:
    profile_correlation_grid = [0.5, 1.0, 1.5]
    chord_fit_grid = [1.0, 2.0, 3.0, 4.0]
    cadence_grid = [0.0, 0.5, 1.0]
    final_is_tonic_grid = [0.0, 0.3, 0.6]
    first_is_tonic_grid = [0.0, 0.2]
    temperature_grid = [0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]

    best = (None, None, None, -1.0)
    for profile in PROFILES:
        for w_corr, w_fit, w_cad, w_final, w_first, temperature in itertools.product(
            profile_correlation_grid,
            chord_fit_grid,
            cadence_grid,
            final_is_tonic_grid,
            first_is_tonic_grid,
            temperature_grid,
        ):
            weights = {
                "profile_correlation": w_corr,
                "chord_fit": w_fit,
                "cadence_count": w_cad,
                "final_is_tonic": w_final,
                "first_is_tonic": w_first,
                "minor_plagal": 0.8,
            }
            metrics = evaluate(items, all_features, dev_indices, profile, weights, temperature)
            # Require top1/top2 to clear the acceptance thresholds, then
            # minimize ECE among qualifying candidates - ranking accuracy is
            # already well above the bar with room to spare, so once it
            # clears we optimize purely for calibration.
            meets_bar = metrics["top1"] >= 0.90 and metrics["top2"] >= 0.95
            objective = (
                (10.0 - metrics["ece"]) if meets_bar else (metrics["top1"] + 0.5 * metrics["top2"])
            )
            if objective > best[3]:
                best = (profile, weights, temperature, objective)
    return best[0], best[1], best[2], best[3]


def main() -> None:
    items = load_gold_items()
    chord_lists = parse_gold_chords()
    all_features = precompute_features(chord_lists)

    dev_indices = [i for i, item in enumerate(items) if item.tonic_letter in DEV_TONIC_LETTERS]
    test_indices = [i for i, item in enumerate(items) if item.tonic_letter in TEST_TONIC_LETTERS]
    assert len(dev_indices) + len(test_indices) == len(items), "tonic split must cover every item"

    profile, weights, temperature, objective = grid_search(items, all_features, dev_indices)

    dev_metrics = evaluate(items, all_features, dev_indices, profile, weights, temperature)
    test_metrics = evaluate(items, all_features, test_indices, profile, weights, temperature)
    all_metrics = evaluate(
        items, all_features, list(range(len(items))), profile, weights, temperature
    )

    params = {"profile": profile, "weights": weights, "temperature": temperature}
    PARAMS_PATH.write_text(json.dumps(params, indent=2) + "\n", encoding="utf-8")

    report = _render_report(
        len(dev_indices),
        len(test_indices),
        profile,
        weights,
        temperature,
        dev_metrics,
        test_metrics,
        all_metrics,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(f"profile={profile} weights={weights} temperature={temperature}")
    print(f"dev_objective={objective:.4f}")
    for name, metrics in (("dev", dev_metrics), ("test", test_metrics)):
        print(
            f"{name}: top1={metrics['top1']:.3f} "
            f"top2={metrics['top2']:.3f} ece={metrics['ece']:.3f}"
        )
    print(f"Wrote {PARAMS_PATH}")
    print(f"Wrote {REPORT_PATH}")


def _render_report(
    dev_n, test_n, profile, weights, temperature, dev_metrics, test_metrics, all_metrics
) -> str:
    lines = [
        "# 24-Key Finder Calibration (F11)",
        "",
        "Weights and softmax temperature fit by grid search on the dev half of "
        "`data/gold/keys.jsonl` (20 templates x 4 transpositions; C and F# transpositions "
        "are dev, Eb and A are held-out test).",
        "",
        f"- Profile: **{profile}**",
        f"- Weights: `{json.dumps(weights)}`",
        f"- Temperature: **{temperature}**",
        "",
        "## Metrics",
        "",
        "| Split | n | Top-1 | Top-2 | ECE (10 bins) |",
        "| --- | ---: | ---: | ---: | ---: |",
        _metric_row("Dev", dev_n, dev_metrics),
        _metric_row("Test", test_n, test_metrics),
        _metric_row("All 80", dev_n + test_n, all_metrics),
        "",
    ]
    return "\n".join(lines)


def _metric_row(name: str, count: int, metrics: dict) -> str:
    return (
        f"| {name} | {count} | {metrics['top1']:.1%} | "
        f"{metrics['top2']:.1%} | {metrics['ece']:.3f} |"
    )


if __name__ == "__main__":
    main()
