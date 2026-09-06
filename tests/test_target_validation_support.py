from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_validation_support import (  # noqa: E402
    GitEvidenceState,
    GitEvidenceView,
)
from validate_target_adapter import (  # noqa: E402
    AdapterValidatorConfig,
    Validator,
    is_blocking_finding,
    load_validator_config,
    result_code,
)


def run_git(target: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=target,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.strip()


def commit(target: Path, message: str) -> str:
    run_git(target, "add", ".")
    run_git(target, "commit", "-qm", message)
    return run_git(target, "rev-parse", "HEAD")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class GitChangeSetTests(unittest.TestCase):
    def test_change_set_uses_one_merge_base_for_every_repository_layer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            run_git(target, "init", "-q")
            run_git(target, "config", "user.name", "Alatyr Tests")
            run_git(target, "config", "user.email", "tests@example.invalid")
            (target / "rename-old.txt").write_text(
                "".join(f"stable line {index}\n" for index in range(20)),
                encoding="utf-8",
            )
            for name in ("deleted.txt", "staged.txt", "unstaged.txt"):
                (target / name).write_text("before\n", encoding="utf-8")
            common_revision = commit(target, "common base")
            feature_branch = run_git(target, "branch", "--show-current")
            run_git(target, "branch", "comparison")

            (target / "feature.txt").write_text("feature branch\n", encoding="utf-8")
            feature_revision = commit(target, "feature change")

            run_git(target, "switch", "-q", "comparison")
            (target / "base-only.txt").write_text("comparison branch\n", encoding="utf-8")
            comparison_revision = commit(target, "comparison-only change")
            run_git(target, "switch", "-q", feature_branch)

            run_git(target, "mv", "rename-old.txt", "rename-new.txt")
            (target / "staged.txt").write_text("staged after\n", encoding="utf-8")
            run_git(target, "add", "staged.txt")
            (target / "unstaged.txt").write_text("unstaged after\n", encoding="utf-8")
            (target / "deleted.txt").unlink()
            (target / "untracked.txt").write_text("untracked\n", encoding="utf-8")

            evidence = GitEvidenceView(target)
            changed_files = evidence.changed_files("comparison")
            change_set = evidence.change_set("comparison")

            self.assertIsNotNone(change_set)
            assert change_set is not None
            expected = {
                "deleted.txt",
                "feature.txt",
                "rename-new.txt",
                "rename-old.txt",
                "staged.txt",
                "unstaged.txt",
                "untracked.txt",
            }
            self.assertEqual(set(changed_files or []), expected)
            self.assertEqual(set(change_set.changed_files), expected)
            self.assertNotIn("base-only.txt", change_set.changed_files)
            self.assertEqual(change_set.base_revision, common_revision)
            self.assertEqual(change_set.head_revision, feature_revision)
            self.assertEqual(change_set.selected_revision, comparison_revision)

            payload = json.loads(change_set.canonical_payload)
            self.assertEqual(set(payload["changed_files"]), expected)
            self.assertEqual(
                [layer["id"] for layer in payload["layers"]],
                ["committed", "staged", "unstaged"],
            )
            self.assertTrue(
                all(len(layer["patch_sha256"]) == 64 for layer in payload["layers"])
            )
            self.assertEqual(
                [item["path"] for item in payload["untracked"]],
                ["untracked.txt"],
            )
            self.assertEqual(
                change_set.content_sha256,
                hashlib.sha256(change_set.canonical_payload.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(evidence.diff_patch("comparison"), change_set.canonical_payload)
            self.assertIs(evidence.change_set("comparison"), change_set)

            run_git(target, "branch", "-f", "comparison", common_revision)
            self.assertIs(evidence.change_set("comparison"), change_set)
            self.assertTrue(evidence.refs_match(comparison_revision, "comparison"))

    def test_git_evidence_distinguishes_stable_mutated_and_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            unavailable = GitEvidenceView(Path(directory))
            self.assertIs(unavailable.stability(), GitEvidenceState.UNAVAILABLE)
            self.assertFalse(unavailable.finalize())
            self.assertEqual(unavailable.telemetry()["stability"], "unavailable")

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            run_git(target, "init", "-q")
            run_git(target, "config", "user.name", "Alatyr Tests")
            run_git(target, "config", "user.email", "tests@example.invalid")
            (target / "tracked.txt").write_text("before\n", encoding="utf-8")
            commit(target, "fixture")
            evidence = GitEvidenceView(target)
            self.assertIs(evidence.stability(), GitEvidenceState.STABLE)
            (target / "tracked.txt").write_text("after\n", encoding="utf-8")
            self.assertIs(evidence.stability(), GitEvidenceState.MUTATED)
            self.assertFalse(evidence.finalize())


class ValidatorTrustBoundaryTests(unittest.TestCase):
    def test_non_git_diff_evidence_is_blocking_without_false_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            validator = Validator(
                Path(directory),
                framework_source=None,
                diff_ref="HEAD",
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=True,
                allow_local_paths=[],
                config=AdapterValidatorConfig(),
            )

            validator.run()

            unavailable = [
                finding
                for finding in validator.findings
                if finding.code == "DIFF_SCOPE_UNAVAILABLE"
            ]
            self.assertEqual(len(unavailable), 1)
            self.assertTrue(is_blocking_finding(unavailable[0]))
            self.assertEqual(
                result_code(validator.findings, strict_warnings=False), 1
            )
            self.assertIs(validator.git.stability(), GitEvidenceState.UNAVAILABLE)
            self.assertNotIn(
                "TARGET_GIT_STATE_MUTATED",
                {finding.code for finding in validator.findings},
            )

    def test_unsupported_config_schema_is_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "validator-config.json"
            write_json(
                path,
                {
                    "schema_version": 999,
                    "allow_local_path_patterns": ["/secret/**"],
                    "severity_overrides": {"EXAMPLE_ERROR": "ignore"},
                    "accepted_deviations": [
                        {"code": "EXAMPLE_WARNING", "reason": "accepted"}
                    ],
                },
            )

            config, findings = load_validator_config(Path(directory), path)

            self.assertEqual(config.local_path_patterns(), [])
            self.assertEqual(config.severity_overrides, None)
            self.assertEqual(config.deviations(), [])
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].code, "VALIDATOR_CONFIG_SCHEMA_VERSION")
            self.assertEqual(findings[0].level, "error")

    def test_unreadable_or_invalid_utf8_config_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            invalid_utf8 = target / "invalid.json"
            invalid_utf8.write_bytes(b"\xff")

            _, unicode_findings = load_validator_config(target, invalid_utf8)
            with patch.object(Path, "read_text", side_effect=PermissionError("denied")):
                _, os_findings = load_validator_config(target, target / "denied.json")

            self.assertEqual(unicode_findings[0].code, "VALIDATOR_CONFIG_READ_ERROR")
            self.assertEqual(unicode_findings[0].level, "error")
            self.assertEqual(os_findings[0].code, "VALIDATOR_CONFIG_READ_ERROR")
            self.assertEqual(os_findings[0].level, "error")

    def test_reasonless_deviation_is_rejected_and_hard_error_cannot_be_demoted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            path = target / "validator-config.json"
            write_json(
                path,
                {
                    "schema_version": 1,
                    "severity_overrides": {"EXAMPLE_ERROR": "ignore"},
                    "accepted_deviations": [
                        {"code": "EXAMPLE_ERROR"},
                        {
                            "code": "EXAMPLE_WARNING",
                            "path": 42,
                            "reason": "must not become a global deviation",
                        },
                    ],
                },
            )

            config, findings = load_validator_config(target, path)
            validator = Validator(
                target,
                framework_source=None,
                diff_ref=None,
                approval_records=[],
                enforce_approval_scope=False,
                change_packages=[],
                enforce_change_package=False,
                migration_diff=None,
                allow_placeholders=True,
                allow_local_paths=[],
                config=config,
                initial_findings=findings,
            )
            validator.error("EXAMPLE_ERROR", "must remain blocking")

            self.assertEqual(config.deviations(), [])
            self.assertIn(
                ("VALIDATOR_CONFIG_ACCEPTED_DEVIATION", "error"),
                {(finding.code, finding.level) for finding in validator.findings},
            )
            self.assertEqual(
                sum(
                    finding.code == "VALIDATOR_CONFIG_ACCEPTED_DEVIATION"
                    for finding in validator.findings
                ),
                2,
            )
            self.assertIn(
                ("EXAMPLE_ERROR", "error"),
                {(finding.code, finding.level) for finding in validator.findings},
            )


if __name__ == "__main__":
    unittest.main()
