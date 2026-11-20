from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContextClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name)
        self.before = self.write("before.json", self.report())
        self.after = self.write("after.json", self.report())
        self.capability = self.write("capability.json", self.capability_value())
        self.epoch = self.write("epoch.json", self.epoch_value())
        self.status = self.write("status.json", self.status_value())

    def write(self, name: str, value: dict) -> Path:
        path = self.target / name
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        return path

    def report(
        self, *, words: int = 1000, characters: int = 8000, files: int = 3,
        paths: list[str] | None = None, profile_words: int = 500,
    ) -> dict:
        resolved = paths or ["AGENTS.md", "a.md", "b.md"]
        return {
            "first_use": {
                "words": words,
                "characters": characters,
                "resolved_files": files,
                "missing_paths": [],
                "resolved_paths": resolved,
            },
            "operational_entry": {
                "words": words + 100,
                "characters": characters + 800,
                "resolved_files": files + 1,
                "missing_paths": [],
                "resolved_paths": resolved,
            },
            "profiles": {
                "docs-local": {
                    "words": profile_words,
                    "characters": profile_words * 8,
                    "resolved_files": 3,
                    "missing_paths": [],
                    "resolved_paths": resolved,
                }
            },
        }

    def capability_value(self, *, post: str = "supported") -> dict:
        return {
            "context_compaction": {
                "route": "supported",
                "automatic_compaction": "supported",
                "manual_compaction": "supported",
                "manual_trigger": "command",
                "pre_boundary_signal": "supported",
                "post_boundary_signal": post,
                "summary_inspection": "supported",
                "project_instruction_reload": "yes",
                "fallback": "session-continuity",
            }
        }

    def epoch_value(self, *, epoch: int = 4, event: str = "framework-update") -> dict:
        return {
            "schema_version": 1,
            "session_id": "ses_test",
            "epoch": epoch,
            "event": event,
            "source": "host-hook",
            "observed_at": "2026-11-20T10:00:00Z",
        }

    def status_value(
        self, *, epoch: int = 4, generation: int = 4,
        pending: bool = False, epoch_state: str = "current",
    ) -> dict:
        return {
            "state": "current",
            "generation": generation,
            "epoch": epoch,
            "epoch_state": epoch_state,
            "compaction_pending": pending,
        }

    def cli(self, *arguments: str):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/context_closure.py"),
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def run_closure(self, *extra: str, **overrides):
        arguments = [
            "--before", str(overrides.get("before", self.before)),
            "--after", str(overrides.get("after", self.after)),
            "--capability", str(overrides.get("capability", self.capability)),
            "--epoch-file", str(overrides.get("epoch", self.epoch)),
            "--ledger-status", str(overrides.get("status", self.status)),
            *extra,
        ]
        return self.cli(*arguments)

    def test_passes_with_epoch_and_supported_capability(self) -> None:
        result = self.run_closure()
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertFalse(payload["authority_granted"])
        self.assertIn("FIRST_USE_WORDS", {item["code"] for item in payload["checks"]})

    def test_passes_with_ttl_fallback_and_unsupported_capability(self) -> None:
        capability = self.write("capability-unsupported.json", self.capability_value(post="unsupported"))
        result = self.cli(
            "--before", str(self.before),
            "--after", str(self.after),
            "--capability", str(capability),
            "--ttl-seconds", "1800",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["ttl_seconds"], 1800)
        self.assertIsNone(payload["epoch"])

    def test_blocks_first_use_regression(self) -> None:
        after = self.write("after-regression.json", self.report(words=1200))
        result = self.run_closure(after=after)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("FIRST_USE_WORDS", " ".join(payload["failures"]))

    def test_blocks_missing_paths(self) -> None:
        report = self.report()
        report["first_use"]["missing_paths"] = ["missing.md"]
        after = self.write("after-missing.json", report)
        result = self.run_closure(after=after)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING_PATHS", " ".join(json.loads(result.stdout)["failures"]))

    def test_blocks_removed_coverage_without_omission(self) -> None:
        after = self.write("after-removed.json", self.report(paths=["AGENTS.md", "a.md"]))
        blocked = self.run_closure(after=after)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("COVERAGE_PATH_REMOVED", " ".join(json.loads(blocked.stdout)["failures"]))

        omissions = self.write(
            "omissions.json",
            {"items": [{"path": "b.md", "reason": "moved to a linked owner"}]},
        )
        passed = self.cli(
            "--before", str(self.before),
            "--after", str(after),
            "--capability", str(self.capability),
            "--epoch-file", str(self.epoch),
            "--ledger-status", str(self.status),
            "--omissions", str(omissions),
        )
        self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_blocks_removed_profile(self) -> None:
        report = self.report()
        report["profiles"] = {}
        after = self.write("after-no-profile.json", report)
        blocked = self.run_closure(after=after)
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("PROFILE_REMOVED", " ".join(json.loads(blocked.stdout)["failures"]))

        omissions = self.write(
            "profile-omissions.json",
            {"items": [{"path": "profile:docs-local", "reason": "profile retired"}]},
        )
        passed = self.cli(
            "--before", str(self.before),
            "--after", str(after),
            "--capability", str(self.capability),
            "--epoch-file", str(self.epoch),
            "--ledger-status", str(self.status),
            "--omissions", str(omissions),
        )
        self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_blocks_pending_compaction(self) -> None:
        status = self.write("status-pending.json", self.status_value(pending=True))
        result = self.run_closure(status=status)
        self.assertEqual(result.returncode, 1)
        self.assertIn("LEDGER_STATE", " ".join(json.loads(result.stdout)["failures"]))

    def test_blocks_supported_capability_without_epoch(self) -> None:
        result = self.cli(
            "--before", str(self.before),
            "--after", str(self.after),
            "--capability", str(self.capability),
            "--ttl-seconds", "1800",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "CAPABILITY_EPOCH_REQUIRED",
            " ".join(json.loads(result.stdout)["failures"]),
        )

    def test_blocks_epoch_status_mismatch(self) -> None:
        status = self.write("status-old.json", self.status_value(epoch=3, generation=3))
        result = self.run_closure(status=status)
        self.assertEqual(result.returncode, 1)
        self.assertIn("EPOCH_STATUS_MATCH", " ".join(json.loads(result.stdout)["failures"]))

    def test_rejects_invalid_epoch_event(self) -> None:
        epoch = self.write("epoch-invalid.json", self.epoch_value(event="manual"))
        result = self.run_closure(epoch=epoch)
        self.assertEqual(result.returncode, 2)
        self.assertIn("framework-update", result.stderr)

    def test_rejects_unresolved_capability_placeholders(self) -> None:
        capability = self.capability_value()
        capability["context_compaction"]["route"] = "{SUPPORTED_OR_UNKNOWN}"
        path = self.write("capability-placeholder.json", capability)
        result = self.run_closure(capability=path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("placeholder", result.stderr)

    def test_rejects_profile_growth(self) -> None:
        after = self.write("after-profile.json", self.report(profile_words=700))
        result = self.run_closure(after=after)
        self.assertEqual(result.returncode, 1)
        self.assertIn("PROFILE_DOCS_LOCAL_WORDS", " ".join(json.loads(result.stdout)["failures"]))

    def test_threshold_zero_rejects_any_growth(self) -> None:
        after = self.write("after-one-word.json", self.report(words=1001))
        blocked = self.run_closure("--threshold", "0", after=after)
        self.assertEqual(blocked.returncode, 1)
        passed = self.run_closure("--threshold", "0")
        self.assertEqual(passed.returncode, 0, passed.stderr)

    def test_capability_index_resolution(self) -> None:
        surface = self.write("opencode.json", self.capability_value())
        index = self.write(
            "assistant-capabilities.json",
            {"surfaces": {"opencode": surface.name}},
        )
        result = self.cli(
            "--before", str(self.before),
            "--after", str(self.after),
            "--capability", str(index),
            "--surface", "opencode",
            "--root", str(self.target),
            "--epoch-file", str(self.epoch),
            "--ledger-status", str(self.status),
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_output_requires_write(self) -> None:
        output = self.target / "closure.json"
        refused = self.run_closure("--output", str(output))
        self.assertEqual(refused.returncode, 2)
        written = self.run_closure("--output", str(output), "--write")
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertTrue(output.is_file())
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "passed")


if __name__ == "__main__":
    unittest.main()
