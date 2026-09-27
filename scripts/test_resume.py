import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "tools" / "resume.py"
if not SCRIPT.exists():
    SCRIPT = Path(__file__).with_name("resume.py")
spec = importlib.util.spec_from_file_location("resume", SCRIPT)
resume = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resume)


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True).stdout.strip()


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        run("git", "init", "-q", cwd=self.repo)
        run("git", "config", "user.name", "Test", cwd=self.repo)
        run("git", "config", "user.email", "test@example.com", cwd=self.repo)
        (self.repo / ".gitignore").write_text("AGENTS.override.md\n")
        (self.repo / "app.py").write_text("print(1)\n")
        (self.repo / "app").mkdir()
        (self.repo / "app" / "AGENTS.md").write_text("stale nested directions\n")
        run("git", "add", ".", cwd=self.repo)
        run("git", "commit", "-qm", "initial", cwd=self.repo)
        self.other = self.base / "other"
        run("git", "worktree", "add", "-qb", "feature", str(self.other), cwd=self.repo)
        self.payload = {
            "revision": 1, "task": "F1", "slice": "first slice",
            "owner": {"path": str(self.other), "branch": "feature", "pr": None},
            "last_completed": {"outcome": "baseline", "revision": run("git", "rev-parse", "HEAD", cwd=self.repo), "evidence": "initial commit"},
            "next_action": "implement first slice", "acceptance": ["result is correct"],
            "references": [{"path": "app.py", "when": "read before editing app"}],
            "verification": {"passed": ["baseline committed"], "failed": [], "skipped": [], "unverified": ["feature check pending"]},
            "blockers": [], "stable_rules": ["Use owner worktree."],
            "nested_overrides": ["app/AGENTS.override.md"],
            "nested_rules": ["Root packet chooses the active task."]}
        record, _ = resume.locations(self.repo)
        record.parent.mkdir(parents=True)
        self.payload["owner"].update(resume.owner_state(self.other))
        record.write_text(json.dumps(self.payload))
        resume.sync(self.repo, self.payload)

    def test_same_packet_in_both_worktrees_and_pending_evidence(self):
        a = (self.repo / resume.NAME).read_text()
        b = (self.other / resume.NAME).read_text()
        self.assertEqual(a, b)
        self.assertIn("Next action: implement first slice", a)
        self.assertIn("unverified: feature check pending", a)
        self.assertEqual((self.repo / "app" / resume.NAME).read_text(),
                         (self.other / "app" / resume.NAME).read_text())
        self.assertIn("Root packet chooses", (self.other / "app" / resume.NAME).read_text())
        self.assertEqual(resume.verify(self.repo), [])

    def test_partial_work_and_stale_packet_fail_closed(self):
        (self.other / "app.py").write_text("print(2)\n")
        self.assertTrue(any("diff_sha256" in x or "status" in x for x in resume.verify(self.repo)))
        (self.repo / resume.NAME).write_text("stale")
        self.assertTrue(any("startup packet" in x for x in resume.verify(self.repo)))
        (self.repo / resume.NAME).write_text(resume.render(self.payload), encoding="utf-8")
        resume.sync(self.repo, self.payload)
        (self.other / "app" / resume.NAME).write_text("stale nested")
        self.assertTrue(any("startup packet" in x for x in resume.verify(self.repo)))

    def test_changed_workstream_and_conflicting_revisions(self):
        self.assertNotEqual(str(self.repo), self.payload["owner"]["path"])
        next_payload = json.loads(json.dumps(self.payload))
        next_payload["owner"] = {"path": str(self.repo), "branch": run("git", "branch", "--show-current", cwd=self.repo)}
        self.assertNotEqual((next_payload["owner"]["path"], next_payload["owner"]["branch"]),
                            (self.payload["owner"]["path"], self.payload["owner"]["branch"]))
        # The CLI requires both an expected revision and explicit --transfer.
        cli = SCRIPT
        payload_file = self.base / "payload.json"
        payload_file.write_text(json.dumps(next_payload))
        result = subprocess.run(["python", str(cli), "checkpoint", "--repo", str(self.repo),
                                 "--input", str(payload_file), "--expect", "1"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--transfer", result.stderr)
        result = subprocess.run(["python", str(cli), "checkpoint", "--repo", str(self.repo),
                                 "--input", str(payload_file), "--expect", "0", "--transfer"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("revision conflict", result.stderr)

    def test_two_writers_cannot_claim_same_revision(self):
        payload_file = self.base / "payload.json"
        updated = json.loads(json.dumps(self.payload))
        updated["slice"] = "second slice"
        payload_file.write_text(json.dumps(updated))
        command = ["python", str(SCRIPT), "checkpoint", "--repo", str(self.repo),
                   "--input", str(payload_file), "--expect", "1"]
        first = subprocess.run(command, capture_output=True, text=True)
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 2)
        self.assertIn("revision conflict", second.stderr)
        self.assertEqual(resume.read_record(self.repo)["revision"], 2)


if __name__ == "__main__":
    unittest.main()
