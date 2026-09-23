"""F10: vocabulary coverage over a Chordonomicon source file.

Counts every chord token the normalizer cannot parse, by frequency, so
`theory/chord_normalizer.py`'s aliases can be extended until token parse
rate clears the 99.95% bar (feature-specs/v2-implementation-plan.md, F10).
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.chordonomicon import iter_chordonomicon_rows


@dataclass(frozen=True)
class VocabReport:
    source_path: str
    rows_processed: int
    total_tokens: int
    parsed_tokens: int
    unparseable_counts: Counter[str]

    @property
    def parse_rate(self) -> float:
        return self.parsed_tokens / self.total_tokens if self.total_tokens else 0.0


def build_vocab_report(source_path: str | Path, limit: int | None = None) -> VocabReport:
    rows_processed = 0
    total_tokens = 0
    parsed_tokens = 0
    unparseable_counts: Counter[str] = Counter()

    for row in iter_chordonomicon_rows(source_path, limit=limit):
        rows_processed += 1
        normalized = row.normalized_progression
        total_tokens += len(normalized.chords) + len(normalized.skipped_tokens)
        parsed_tokens += len(normalized.chords)
        unparseable_counts.update(normalized.skipped_tokens)

    return VocabReport(
        source_path=str(source_path),
        rows_processed=rows_processed,
        total_tokens=total_tokens,
        parsed_tokens=parsed_tokens,
        unparseable_counts=unparseable_counts,
    )


def render_vocab_report_markdown(report: VocabReport, top_n: int = 200) -> str:
    shown = min(top_n, len(report.unparseable_counts))
    lines = [
        "# Vocabulary Coverage Report",
        "",
        f"Source: `{report.source_path}`",
        "",
        f"- Rows (progressions) processed: {report.rows_processed:,}",
        f"- Total chord tokens: {report.total_tokens:,}",
        f"- Parsed tokens: {report.parsed_tokens:,}",
        f"- **Parse rate: {report.parse_rate:.4%}**",
        f"- Unique unparseable symbols: {len(report.unparseable_counts):,}",
        "",
        f"## Top {shown} unparseable symbols by frequency",
        "",
        "| Symbol | Count |",
        "| --- | ---: |",
    ]
    for token, count in report.unparseable_counts.most_common(top_n):
        escaped = token.replace("|", "\\|") or "(empty)"
        lines.append(f"| `{escaped}` | {count:,} |")
    lines.append("")
    return "\n".join(lines)
