# Live AI follow-up — 2026-09-30

[GitHub run 36798353165](https://github.com/siddsan7/HarmonicColorGraph/actions/runs/36798353165) tested commit a352a4a using live Anthropic models and seeded domain services. All 40 cases completed; metered and accounted cost were $2.386143, under the $5 cap. No unknown-cost cases occurred. This is not production-corpus verification.

Acceptance still failed. Intent parsing was 0.8333, combined intent/color match 0.5, routing/tool correctness/required tags 0.95. Schema, forbidden-claim, theory and fact-coverage metrics were 1.0. Two comparison requests failed to reach color_profile. Some explanations fell back with explanation_validation_failed:ValueError; this run did not expose individual validation rule codes. The next change exposes only stable validator codes to repair and diagnostics, without raw provider errors or rejected prose.

The run improves completion and intent parsing over the earlier 7/40 baseline, but does not establish that prompt size alone caused the earlier failures. Full results: [JSON](ai-live-followup-2026-09-30.json).
