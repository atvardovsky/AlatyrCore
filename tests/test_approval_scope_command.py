from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "tools" / "report_approval_scope.py"


def run_git(target: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=target, check=True)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def approval_record(allowed: list[str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_kind": "alatyr-approval-record",
        "evidence_classification": "historical-record",
        "approval_id": "approval-test",
        "operation": {"id": "operation-test", "type": "code-change"},
        "plan": {"version": "1", "sha256": "not available: test", "file": "not available: test"},
        "diff": {
            "base": "HEAD",
            "patch_sha256": "not available: test",
            "repository_revision_at_approval": "HEAD",
        },
        "scope": {
            "allowed_protected_changes": ["implementation"],
            "allowed_files_or_surfaces": allowed,
            "excluded_files_or_surfaces": [],
            "excluded_actions": ["publish", "live-external"],
            "allowed_actions_mode": "code-and-tests",
            "invalidation_rule": "any scope change invalidates approval",
        },
        "approval": {
            "approved_by": "tester",
            "approved_at": "2026-08-30T00:00:00Z",
        },
        "use_result": {},
    }


class ApprovalScopeCommandTests(unittest.TestCase):
    def make_repo(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        directory = tempfile.TemporaryDirectory()
        target = Path(directory.name)
        run_git(target, "init", "-q")
        run_git(target, "config", "user.email", "alatyr@example.invalid")
        run_git(target, "config", "user.name", "Alatyr Check")
        (target / "src").mkdir()
        (target / "src" / "allowed.txt").write_text("before\n", encoding="utf-8")
        (target / "src" / "outside.txt").write_text("before\n", encoding="utf-8")
        run_git(target, "add", ".")
        run_git(target, "commit", "-qm", "fixture")
        (target / "src" / "allowed.txt").write_text("after\n", encoding="utf-8")
        (target / "src" / "outside.txt").write_text("after\n", encoding="utf-8")
        (target / "src" / "untracked.txt").write_text("new\n", encoding="utf-8")
        approval = target / ".ai" / "assistant" / "approvals" / "approval.json"
        return directory, target, approval

    def run_command(self, target: Path, approval: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(COMMAND),
                "--target",
                str(target),
                "--diff-ref",
                "HEAD",
                "--approval-record",
                approval.relative_to(target).as_posix(),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_rejects_out_of_scope_tracked_and_untracked_paths(self) -> None:
        directory, target, approval = self.make_repo()
        with directory:
            write_json(
                approval,
                approval_record([
                    "src/allowed.txt",
                    ".ai/assistant/approvals/approval.json",
                ]),
            )

            result = self.run_command(target, approval)

            self.assertEqual(result.returncode, 1)
            self.assertIn("Approval scope check: failed", result.stdout)
            self.assertIn("APPROVAL_SCOPE_MISMATCH", result.stdout)
            self.assertIn("src/outside.txt", result.stdout)
            self.assertIn("src/untracked.txt", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_accepts_complete_explicit_scope(self) -> None:
        directory, target, approval = self.make_repo()
        with directory:
            write_json(
                approval,
                approval_record([
                    "src/*",
                    ".ai/assistant/approvals/approval.json",
                ]),
            )

            result = self.run_command(target, approval)

            self.assertEqual(result.returncode, 0)
            self.assertIn("Approval scope check: passed", result.stdout)
            self.assertIn("APPROVAL_SCOPE_ENFORCED", result.stdout)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
