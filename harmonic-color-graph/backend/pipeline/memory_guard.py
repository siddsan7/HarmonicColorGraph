"""Hard memory ceiling for pipeline stages.

Three separate F22/F20 stages have driven this process to 15-17GB RSS on
the real corpus before a human had to notice and kill it (analyze's
unbatched write, then two different unbounded-cardinality bugs in
ngrams/patterns). Reviewing each stage's algorithm for memory safety is
necessary but has proven insufficient on its own -- a future stage (or an
edit to an existing one) can reintroduce the same class of bug. This is
the structural backstop: every stage runs under a watchdog thread that
polls this process's actual RSS and kills it immediately, with a clear
diagnostic, if it crosses a hard cap, instead of silently continuing
until the whole system is starved of memory.

This is deliberately blunt (os._exit, not a catchable exception): a
process that has already blown its memory budget may not have enough
headroom left to unwind cleanly, and the goal is stopping the bleeding
in seconds, not minutes.
"""

from __future__ import annotations

import os
import sys
import threading

DEFAULT_CHECK_INTERVAL_S = 2.0
# Half of total system RAM, capped at 8 GB -- generous enough for a
# legitimate full-corpus pass (the current stages peak around 4-6 GB), but
# low enough to leave the machine usable and to catch a runaway well
# before it reaches the kind of 0.3 GB-free crisis this has caused before.
DEFAULT_MAX_FRACTION_OF_TOTAL = 0.5
DEFAULT_MAX_RSS_MB_CAP = 8192


def _default_max_rss_mb() -> int:
    import psutil

    total_mb = psutil.virtual_memory().total / (1024 * 1024)
    return int(min(DEFAULT_MAX_RSS_MB_CAP, total_mb * DEFAULT_MAX_FRACTION_OF_TOTAL))


class MemoryGuard:
    """Context manager: `with MemoryGuard(label="analyze"): ...`.

    Starts a daemon thread that polls this process's RSS every
    `check_interval_s`. If RSS exceeds `max_rss_mb`, it prints a
    diagnostic to stderr and terminates the process immediately via
    `os._exit`, without raising into the guarded code (there may not be
    enough safe headroom left to run exception-handling machinery).
    """

    def __init__(
        self,
        label: str,
        max_rss_mb: int | None = None,
        check_interval_s: float = DEFAULT_CHECK_INTERVAL_S,
    ):
        self.label = label
        self.max_rss_mb = max_rss_mb if max_rss_mb is not None else _default_max_rss_mb()
        self.check_interval_s = check_interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _watch(self) -> None:
        import psutil

        process = psutil.Process(os.getpid())
        while not self._stop.wait(self.check_interval_s):
            # Include worker subprocesses (e.g. analyze's ProcessPoolExecutor
            # pool): a stage's memory budget is the whole process tree's, not
            # just what the parent itself is holding.
            try:
                children_rss = sum(
                    child.memory_info().rss for child in process.children(recursive=True)
                )
            except psutil.Error:
                children_rss = 0
            rss_mb = (process.memory_info().rss + children_rss) / (1024 * 1024)
            if rss_mb > self.max_rss_mb:
                sys.stderr.write(
                    f"\n[memory_guard] ABORTING: stage '{self.label}' hit "
                    f"{rss_mb:.0f} MB RSS (cap {self.max_rss_mb} MB). Killing the "
                    "process now to protect the rest of the system, rather than "
                    "continuing to grow. This is a hard safety cap, not a crash: "
                    "if this stage legitimately needs more memory, raise the cap "
                    "or fix the stage's memory usage -- don't just retry.\n"
                )
                sys.stderr.flush()
                os._exit(1)

    def __enter__(self) -> MemoryGuard:
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.check_interval_s + 1)
