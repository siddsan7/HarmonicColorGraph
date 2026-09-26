"""Run a repository's explicit verification manifest with bounded console output."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


def stop_tree(process, output=subprocess.DEVNULL):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=output, stderr=subprocess.STDOUT, timeout=15, check=False)
    else:
        os.killpg(process.pid, signal.SIGKILL)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_process(argv, *, timeout, cwd=None, stdout=None, stderr=None):
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen(argv, cwd=cwd, stdout=stdout, stderr=stderr, **kwargs)
    try:
        return process.wait(timeout=timeout)
    finally:
        stop_tree(process, stdout if stdout is not None else subprocess.DEVNULL)


def run_checks(manifest, scope, log_dir):
    manifest = Path(manifest).resolve()
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    root = (manifest.parent / spec.get("root", ".")).resolve()
    selected = spec["scopes"].get(scope)
    if selected is None:
        raise ValueError(f"Unknown scope: {scope}")
    log_dir = Path(log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    results = []
    for index, check in enumerate(selected):
        argv = [sys.executable if x == "{python}" else x for x in check["argv"]]
        argv[0] = shutil.which(argv[0]) or argv[0]
        cwd = (root / check.get("cwd", ".")).resolve()
        if not cwd.is_relative_to(root):
            raise ValueError(f"Check cwd escapes repository: {cwd}")
        log = log_dir / f"{run_id}-{index}.log"
        started = time.monotonic()
        code, error = None, None
        with log.open("w", encoding="utf-8") as out:
            try:
                # On Windows subprocess resolves a trusted .cmd executable via the OS.
                # Arguments come from the reviewed manifest, never from model text.
                code = run_process(argv, cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
                                   timeout=check.get("timeout_seconds", 600))
            except subprocess.TimeoutExpired:
                code, error = 124, "timeout"
                out.write("\nVerification timed out.\n")
            except OSError as exc:
                code, error = 127, str(exc)
                out.write(f"\nCould not run check: {exc}\n")
        row = {"name": check["name"], "exit_code": code, "passed": code == 0,
               "seconds": round(time.monotonic() - started, 3), "log": str(log), "error": error}
        results.append(row)
        print(f"{'PASS' if row['passed'] else 'FAIL'} {check['name']} ({row['seconds']}s); log={log}")
    report = {"schema_version": 1, "scope": scope, "passed": bool(results) and all(r["passed"] for r in results), "checks": results}
    report_path = log_dir / f"{run_id}-summary.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Summary: {report_path}")
    failures = [r["exit_code"] for r in results if r["exit_code"] != 0]
    return failures[0] if failures else (0 if results else 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope")
    adjacent = Path(__file__).with_name("checks.json")
    parser.add_argument("--manifest", type=Path, default=adjacent if adjacent.exists() else Path("checks.json"))
    parser.add_argument("--logs", type=Path, default=Path(".agent-logs"))
    args = parser.parse_args()
    try:
        code = run_checks(args.manifest, args.scope, args.logs)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f"Invalid verification setup: {exc}\n")
    raise SystemExit(code if 0 <= code <= 255 else 1)


if __name__ == "__main__":
    main()
