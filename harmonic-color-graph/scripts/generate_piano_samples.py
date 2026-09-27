"""Create the small, self-hosted piano-like sample set used by the browser sampler."""

from math import exp, pi, sin
from pathlib import Path
from struct import pack
import wave


TARGET = Path(__file__).resolve().parents[1] / "public" / "samples" / "piano"
RATE = 22050
DURATION = 2.0


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, midi in (("C3", 48), ("C4", 60), ("C5", 72)):
        fundamental = 440 * 2 ** ((midi - 69) / 12)
        samples = bytearray()
        for index in range(int(RATE * DURATION)):
            time = index / RATE
            attack = min(1.0, time / 0.008)
            tone = sum(
                amplitude * exp(-decay * time) * sin(2 * pi * fundamental * harmonic * time)
                for harmonic, amplitude, decay in ((1, 0.65, 2.2), (2, 0.22, 3.5), (3, 0.1, 5.0), (4, 0.04, 8.0))
            )
            samples.extend(pack("<h", int(max(-1, min(1, tone * attack)) * 28000)))
        with wave.open(str(TARGET / f"{name}.wav"), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes(samples)


if __name__ == "__main__":
    main()
