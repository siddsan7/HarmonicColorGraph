# Color prefix reuse — 2026-10-20

The color profile path repeated expensive raw color and voice-leading work for
all earlier positions each time it built the next perceptual arc position.
For a key region of n chords, this called raw color n + n(n+1)/2 times.
The service now keeps its own request-local raw prefix and shares the existing
perceptual aggregation. Raw color runs n times. Region boundaries, arithmetic
order, source, confidence, explanation, and every output field stay unchanged.
The public perceptual entry point, including predictor support, stays unchanged.
No state survives between requests.

Two development and four held-out contexts were frozen before the edit.
After implementation, seven AB/BA repetitions compared the complete color profile
path with the pre-change build_arc reference. Every output hash also matched the
saved original baseline. The held-out data was not used to change the fix.

| Fresh context | Before median | After median |
|---|---:|---:|
| Ab major extended chords | 111.565 ms | 26.207 ms |
| C# minor extended chords | 59.271 ms | 20.409 ms |
| D major inversion and cadence | 132.172 ms | 31.299 ms |
| Unmarked Eb / E modulation | 37.856 ms | 14.551 ms |

These local CPU times improved by 61.6–76.5%. They are not production completion
or p95 measurements. In the existing six-pair candidate run, the median interval
from validated candidate delivery to final delivery is 8.482 seconds. That interval
includes explanation, repair, formatting, audit and delivery; the evidence does
not isolate provider latency. Saving tens of milliseconds per color profile
cannot establish the eight-second completion target.

Production tail acceptance remains unverified. The existing failure-aware tail
gate requires representative independent production HTTP/SSE attempts and a
one-sided 95% exact binomial lower bound of at least 95% below 20 seconds. At
least 59 attempts with no failures are needed; failures require more evidence.
Six controlled pairs cannot meet that gate. No additional paid requests ran.

The fresh tests check full profile equality, region isolation, invalid raw/token
lengths, and one raw computation per chord. The benchmark, scorer, validator,
models, timeouts, and cost limits were not changed.

[Raw evidence and frozen output hashes](color-prefix-reuse-2026-10-20.json).
