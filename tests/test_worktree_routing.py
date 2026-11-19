from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.worktree_routing import (  # noqa: E402
    branch_exists,
    routing_issues,
)
from validate_target_adapter import AdapterValidatorConfig, Validator  # noqa: E402
from worktree_readiness import readiness  # noqa: E402


def git(cwd: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class WorktreeRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "target"
        self.target.mkdir()
        git(self.target, "init", "-q")
        git(self.target, "symbolic-ref", "HEAD", "refs/heads/main")
        git(self.target, "config", "user.email", "fixture@example.invalid")
        git(self.target, "config", "user.name", "Fixture")
        (self.target / "README.md").write_text("fixture\n", encoding="utf-8")
        (self.target / ".ai").mkdir()
        self.write_manifest()
        git(self.target, "add", ".")
        git(self.target, "commit", "-qm", "fixture")

    def write_manifest(self, *, require: bool = False) -> None:
        require_line = "  require_canonical_worktree: true\n" if require else ""
        (self.target / ".ai/alatyr.yaml").write_text(
            "branch_policy:\n"
            "  alatyr_development_branch: preDev-alatyr\n"
            f"{require_line}",
            encoding="utf-8",
        )

    def manifest(self) -> dict:
        return {
            "branch_policy": {
                "alatyr_development_branch": "preDev-alatyr",
            }
        }

    def canonical_worktree(self) -> Path:
        path = Path(self.temporary.name) / "canonical"
        git(self.target, "branch", "preDev-alatyr")
        git(self.target, "worktree", "add", "-q", str(path), "preDev-alatyr")
        return path

    def test_current_main_requires_the_canonical_worktree(self) -> None:
        canonical = self.canonical_worktree()
        issues = routing_issues(self.target, self.manifest())

        self.assertEqual([issue["code"] for issue in issues], ["WORKTREE_ROUTING_REQUIRED"])
        self.assertTrue(issues[0]["blocking"])
        self.assertIn(canonical.as_posix(), issues[0]["message"])

    def test_current_canonical_branch_is_ready(self) -> None:
        git(self.target, "switch", "-q", "-c", "preDev-alatyr")

        self.assertEqual(routing_issues(self.target, self.manifest()), [])

    def test_missing_canonical_worktree_path_is_reported(self) -> None:
        canonical = self.canonical_worktree()
        shutil.rmtree(canonical)
        issues = routing_issues(self.target, self.manifest())

        self.assertEqual([issue["code"] for issue in issues], ["WORKTREE_PATH_MISSING"])
        self.assertTrue(issues[0]["blocking"])

    def test_missing_branch_and_absent_policy_keep_previous_behavior(self) -> None:
        self.assertFalse(branch_exists(self.target, "preDev-alatyr"))
        self.assertEqual(routing_issues(self.target, self.manifest()), [])
        self.assertEqual(routing_issues(self.target, {}), [])

    def test_detached_release_checkout_can_be_explicitly_allowed(self) -> None:
        self.canonical_worktree()
        git(self.target, "checkout", "-q", "--detach")

        self.assertEqual(
            [issue["code"] for issue in routing_issues(self.target, self.manifest())],
            ["WORKTREE_ROUTING_REQUIRED"],
        )
        self.assertEqual(
            routing_issues(
                self.target, self.manifest(), allow_detached=True
            ),
            [],
        )

    def test_readiness_surfaces_routing_issue(self) -> None:
        self.canonical_worktree()

        report = readiness(self.target, None)
        codes = {issue["code"] for issue in report["issues"]}

        self.assertEqual(report["state"], "blocked")
        self.assertIn("WORKTREE_ROUTING_REQUIRED", codes)

    def test_validator_warns_or_errors_according_to_policy(self) -> None:
        self.canonical_worktree()
        validator = Validator(
            self.target,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=True,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
            validation_phase="migration-staging",
        )
        validator.check_worktree_routing()
        self.assertIn(
            "WORKTREE_ROUTING_REQUIRED",
            {finding.code for finding in validator.findings},
        )
        self.assertEqual(
            {finding.level for finding in validator.findings},
            {"warning"},
        )

        self.write_manifest(require=True)
        strict = Validator(
            self.target,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=False,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
            validation_phase="acceptance",
        )
        strict.check_worktree_routing()
        self.assertIn(
            "WORKTREE_ROUTING_REQUIRED",
            {finding.code for finding in strict.findings},
        )
        self.assertEqual(
            {finding.level for finding in strict.findings},
            {"error"},
        )


if __name__ == "__main__":
    unittest.main()
