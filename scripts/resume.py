"""Local, worktree-shared Codex resume record. Standard library only.

The record lives in Git's common directory, so linked worktrees share one
revision. Root AGENTS.override.md files are disposable mirrors, never state.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

MARKER = "<!-- agent-workbench:managed-resume -->"
NAME = "AGENTS.override.md"


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True,
                            encoding="utf-8", capture_output=True, check=True)
    return result.stdout.strip()


def root(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--show-toplevel")).resolve()


def common(repo: Path) -> Path:
    raw = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    return raw.resolve()


def locations(repo: Path) -> tuple[Path, Path]:
    folder = common(repo) / "agent-workbench"
    return folder / "resume.json", folder / "resume.lock"


def worktrees(repo: Path) -> list[Path]:
    return [Path(line[9:]).resolve() for line in git(repo, "worktree", "list", "--porcelain").splitlines()
            if line.startswith("worktree ")]


def owner_state(path: Path) -> dict[str, str]:
    status = git(path, "status", "--porcelain=v1", "--untracked-files=all")
    diff = git(path, "diff", "--binary", "HEAD")
    digest = hashlib.sha256((status + "\n" + diff).encode())
    untracked = git(path, "ls-files", "--others", "--exclude-standard").splitlines()
    for name in untracked:
        candidate = path / name
        if candidate.is_file():
            digest.update(name.encode())
            digest.update(candidate.read_bytes())
    fingerprint = digest.hexdigest()
    return {"head": git(path, "rev-parse", "HEAD"),
            "branch": git(path, "symbolic-ref", "--quiet", "--short", "HEAD"),
            "status": status, "diff_sha256": fingerprint}


def validate(data: dict) -> None:
    required = ("task", "slice", "owner", "last_completed", "next_action",
                "acceptance", "references", "verification", "blockers", "stable_rules")
    for field in required:
        if field not in data or data[field] in (None, ""):
            raise ValueError(f"missing required field: {field}")
    if not isinstance(data["owner"], dict) or not all(data["owner"].get(x) for x in ("path", "branch")):
        raise ValueError("owner requires path and branch")
    if not isinstance(data["last_completed"], dict) or not all(data["last_completed"].get(x) for x in ("outcome", "revision", "evidence")):
        raise ValueError("last_completed requires outcome, revision and evidence")
    if not isinstance(data["acceptance"], list) or not data["acceptance"]:
        raise ValueError("acceptance must be a nonempty list")
    if not isinstance(data["references"], list) or not all(r.get("path") and r.get("when") for r in data["references"]):
        raise ValueError("each reference requires path and read condition")
    if not isinstance(data["verification"], dict) or set(data["verification"]) != {"passed", "failed", "skipped", "unverified"}:
        raise ValueError("verification requires passed, failed, skipped, unverified")
    if not all(isinstance(v, list) for v in data["verification"].values()):
        raise ValueError("verification categories must be lists")
    if not isinstance(data["blockers"], list):
        raise ValueError("blockers must be a list")
    if not isinstance(data["stable_rules"], list) or not data["stable_rules"]:
        raise ValueError("stable_rules must be a nonempty list")


def render(data: dict) -> str:
    validate(data)
    owner = data["owner"]
    lines = [MARKER, f"# Active workstream — record r{data['revision']}",
             *data["stable_rules"], "", f"Task: {data['task']}", f"Slice: {data['slice']}",
             f"Owner: {owner['path']} | branch {owner['branch']} | PR {owner.get('pr') or 'none'}",
             f"Last completed: {data['last_completed']['outcome']} at {data['last_completed']['revision']}; evidence: {data['last_completed']['evidence']}",
             f"Next action: {data['next_action']}", "Acceptance: " + "; ".join(data["acceptance"]),
             "References (read only when relevant):"]
    lines += [f"- {r['path']}: {r['when']}" for r in data["references"]]
    lines += ["Verification at checkpoint:"]
    lines += [f"- {k}: {'; '.join(data['verification'][k]) or 'none'}" for k in ("passed", "failed", "skipped", "unverified")]
    lines += ["Blockers/decisions: " + ("; ".join(data["blockers"]) or "none")]
    command = data.get("tool_command", "python scripts/resume.py")
    lines += [f"Before acting: run `{command} verify --repo .` from this checkout. If it reports drift, reconcile Git/PR state and checkpoint; never follow a stale packet. If owner differs, work there. Checkpoint after a working slice, blocker, PR or merge."]
    output = "\n".join(lines) + "\n"
    if len(output.split()) > 700:
        raise ValueError(f"rendered packet exceeds 700 words ({len(output.split())})")
    return output


@contextlib.contextmanager
def locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"checkpoint lock exists: {path}; inspect before removing") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(f"pid={os.getpid()} time={time.time()}\n")
        yield
    finally:
        path.unlink(missing_ok=True)


def atomic_write(path: Path, content: str) -> None:
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        temp.write_text(content, encoding="utf-8", newline="\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def read_record(repo: Path) -> dict:
    path, _ = locations(repo)
    return json.loads(path.read_text(encoding="utf-8"))


def check_owner(data: dict, repo: Path) -> list[str]:
    owner = Path(data["owner"]["path"]).resolve()
    issues = []
    if owner not in worktrees(repo):
        return [f"owner worktree absent: {owner}"]
    current = owner_state(owner)
    for key in ("head", "branch", "status", "diff_sha256"):
        if current[key] != data["owner"].get(key):
            issues.append(f"owner {key} changed since checkpoint")
    pr = data["owner"].get("pr")
    if pr:
        result = subprocess.run(["gh", "pr", "view", str(pr), "--json", "state,headRefOid,headRefName"],
                                cwd=owner, text=True, encoding="utf-8", capture_output=True)
        if result.returncode:
            issues.append("PR status unavailable; inspect before continuing")
        else:
            remote = json.loads(result.stdout)
            if remote.get("state") != "OPEN" or remote.get("headRefOid") != data["owner"].get("head") or remote.get("headRefName") != data["owner"].get("branch"):
                issues.append("PR state, head, or branch changed since checkpoint")
    return issues


def sync(repo: Path, data: dict) -> None:
    packet = render(data)
    destinations = managed_destinations(repo)
    for target in destinations:
        atomic_write(target, packet)


def managed_destinations(repo: Path) -> list[Path]:
    destinations = [wt / NAME for wt in worktrees(repo)]
    for target in destinations:
        if target.exists() and not target.read_text(encoding="utf-8").startswith(MARKER):
            raise RuntimeError(f"unmanaged override exists: {target}")
    return destinations


def verify(repo: Path) -> list[str]:
    data = read_record(repo)
    validate(data)
    issues = check_owner(data, repo)
    expected = render(data)
    for wt in worktrees(repo):
        target = wt / NAME
        if not target.exists() or target.read_text(encoding="utf-8") != expected:
            issues.append(f"startup packet out of sync: {target}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "checkpoint", "sync", "verify", "status"])
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, help="JSON payload for init/checkpoint")
    parser.add_argument("--expect", type=int, help="required previous revision for checkpoint")
    parser.add_argument("--reconcile", action="store_true", help="acknowledge and repair detected Git drift")
    parser.add_argument("--transfer", action="store_true", help="explicitly change workstream owner")
    args = parser.parse_args()
    repo = root(args.repo)
    path, lock = locations(repo)
    try:
        if args.command in ("init", "checkpoint"):
            if not args.input:
                raise ValueError("--input required")
            if args.command == "checkpoint" and args.expect is None:
                raise ValueError("--expect required for checkpoint")
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            validate(payload)
            with locked(lock):
                prior = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
                if args.command == "init" and prior is not None:
                    raise ValueError("record already initialized")
                if args.command == "checkpoint" and (prior is None or prior["revision"] != args.expect):
                    raise ValueError(f"revision conflict: expected {args.expect}, actual {prior['revision'] if prior else 'none'}")
                if prior and args.command == "checkpoint":
                    drift = check_owner(prior, repo)
                    if drift and not args.reconcile:
                        raise ValueError("stale owner state; inspect and use --reconcile after repair: " + "; ".join(drift))
                    if (payload["owner"]["path"], payload["owner"]["branch"]) != (prior["owner"]["path"], prior["owner"]["branch"]) and not args.transfer:
                        raise ValueError("active workstream changed; use --transfer after reviewing both worktrees")
                payload["revision"] = (prior["revision"] + 1) if prior else 1
                owner = Path(payload["owner"]["path"]).resolve()
                if owner not in worktrees(repo):
                    raise ValueError(f"owner not a local worktree: {owner}")
                payload["owner"].update(owner_state(owner))
                render(payload)
                managed_destinations(repo)
                atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
                sync(repo, payload)
            print(f"checkpoint r{payload['revision']} synced to {len(worktrees(repo))} worktrees")
        elif args.command == "sync":
            with locked(lock):
                data = read_record(repo)
                sync(repo, data)
            print(f"synced r{data['revision']} to {len(worktrees(repo))} worktrees")
        elif args.command == "verify":
            issues = verify(repo)
            if issues:
                for issue in issues:
                    print("STALE:", issue)
                return 2
            print(f"OK: r{read_record(repo)['revision']} owner and {len(worktrees(repo))} startup packets match")
        else:
            data = read_record(repo)
            print(f"r{data['revision']} {data['task']} | {data['slice']} | {data['owner']['path']}")
            print("next:", data["next_action"])
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"resume: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
