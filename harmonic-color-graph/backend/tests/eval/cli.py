"""Dispatch evaluation suites without changing the F31 prediction interface."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "ai":
        from tests.eval.ai import main as ai_main

        ai_main(args[1:])
        return
    from tests.eval.prediction import main as prediction_main

    prediction_main(args)


if __name__ == "__main__":
    main()
