from __future__ import annotations

import json
import ntpath
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import read_ledger  # noqa: E402


class ReadLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "target"
        self.target.mkdir()
        (self.target / "a.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
        (self.target / "b.txt").write_text("b1\nb2\n", encoding="utf-8")

    def cli(self, *arguments: str):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/read_ledger.py"),
                "--target",
                str(self.target),
                *arguments,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def record(self, *extra: str, session: str = "s1", task: str = "t1", path: str = "a.txt"):
        result = self.cli(
            "record", "--session", session, "--task", task, "--path", path, *extra
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def check(self, *extra: str, session: str = "s1", task: str = "t1", path: str = "a.txt"):
        result = self.cli(
            "check", "--session", session, "--task", task, "--path", path, *extra
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def ledger_path(self, session: str = "s1") -> Path:
        return read_ledger._store_paths(self.target, session, create=False)[1]

    def test_record_and_check_full_and_range(self) -> None:
        recorded = self.record("--full")
        self.assertEqual(recorded["state"], "recorded")
        self.assertEqual(recorded["authority"], "none")

        full = self.check("--full")
        self.assertEqual(full["state"], "reused")
        self.assertTrue(full["reusable"])
        self.assertFalse(full["authority_granted"])

        ranged = self.check("--range", "2:3")
        self.assertEqual(ranged["state"], "reused")
        self.assertEqual(ranged["covered_ranges"], [[2, 3]])

    def test_partial_coverage_returns_missing_only(self) -> None:
        self.record("--range", "1:2")
        result = self.check("--range", "1:3")
        self.assertEqual(result["state"], "partial")
        self.assertFalse(result["reusable"])
        self.assertEqual(result["covered_ranges"], [[1, 2]])
        self.assertEqual(result["missing_ranges"], [[3, 3]])

    def test_adjacent_ranges_merge(self) -> None:
        self.record("--range", "1:2")
        self.record("--range", "3:3")
        result = self.check("--range", "1:3")
        self.assertEqual(result["state"], "reused")
        self.assertEqual(result["covered_ranges"], [[1, 3]])

    def test_changed_file_invalidates_and_re_records(self) -> None:
        self.record("--full")
        (self.target / "a.txt").write_text("one\nTWO\nthree\nfour\n", encoding="utf-8")
        changed = self.check("--full")
        self.assertEqual(changed["state"], "changed")
        self.assertNotEqual(changed["file_sha256"], changed["previous_sha256"])

        self.record("--full")
        self.assertEqual(self.check("--full")["state"], "reused")

    def test_task_and_session_are_isolated(self) -> None:
        self.record("--full")
        self.assertEqual(self.check("--full", task="t2")["state"], "miss")
        self.assertEqual(self.check("--full", session="s2")["state"], "miss")

    def test_compaction_forces_redelivery(self) -> None:
        self.record("--full")
        compact = self.cli("compact", "--session", "s1")
        self.assertEqual(compact.returncode, 0, compact.stderr)
        self.assertEqual(json.loads(compact.stdout)["generation"], 1)

        decision = self.check("--full")
        self.assertEqual(decision["state"], "redeliver")
        self.assertEqual(decision["retention"], "compacted")

        self.record("--full")
        reused = self.check("--full")
        self.assertEqual(reused["state"], "reused")
        self.assertEqual(reused["generation"], 1)

    def test_status_and_prune(self) -> None:
        self.record("--full", path="a.txt")
        self.record("--full", path="b.txt")
        status = self.cli("status", "--session", "s1")
        self.assertEqual(status.returncode, 0, status.stderr)
        payload = json.loads(status.stdout)
        self.assertEqual(payload["entries"], 2)
        self.assertGreater(payload["delivered_words"], 0)
        self.assertFalse(payload["authority_granted"])

        pruned = self.cli("prune", "--session", "s1", "--max-entries", "1")
        self.assertEqual(pruned.returncode, 0, pruned.stderr)
        self.assertEqual(json.loads(pruned.stdout)["removed"], 1)
        self.assertEqual(json.loads(self.cli("status", "--session", "s1").stdout)["entries"], 1)

    def test_corrupt_ledger_fails_closed_and_reset_recovers(self) -> None:
        self.record("--full")
        self.ledger_path().write_text("{not json", encoding="utf-8")

        unavailable = self.check("--full")
        self.assertEqual(unavailable["state"], "unavailable")
        self.assertFalse(unavailable["reusable"])

        failed = self.cli(
            "record", "--session", "s1", "--task", "t1", "--path", "a.txt", "--full"
        )
        self.assertEqual(failed.returncode, 1)
        self.assertIn("unavailable", failed.stderr)

        reset = self.cli("reset", "--session", "s1", "--write")
        self.assertEqual(reset.returncode, 0, reset.stderr)
        self.assertEqual(self.check("--full")["state"], "miss")

    def test_check_is_read_only_and_does_not_create_state(self) -> None:
        decision = self.check("--full")
        self.assertEqual(decision["state"], "miss")
        self.assertFalse((self.target / ".ai").exists())

    def test_session_directory_is_hashed(self) -> None:
        self.record("--full")
        session_dir = read_ledger._session_dir(self.target, "s1")
        self.assertRegex(session_dir.name, r"^[0-9a-f]{16}$")
        self.assertTrue((session_dir / "index.json").is_file())

    def test_path_safety(self) -> None:
        outside = Path(self.temporary.name) / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        escaped = self.cli(
            "check", "--session", "s1", "--task", "t1", "--path", "../outside.txt", "--full"
        )
        self.assertEqual(escaped.returncode, 2)
        self.assertIn("repository-relative", escaped.stderr)

        drive = self.cli(
            "check", "--session", "s1", "--task", "t1", "--path", "C:\\temp\\a.txt", "--full"
        )
        self.assertEqual(drive.returncode, 2)

        linked = self.target / "linked.txt"
        linked.symlink_to(self.target / "a.txt")
        symlink = self.cli(
            "check", "--session", "s1", "--task", "t1", "--path", "linked.txt", "--full"
        )
        self.assertEqual(symlink.returncode, 2)
        self.assertIn("symlink", symlink.stderr)

    def test_crlf_ranges_are_stable(self) -> None:
        (self.target / "crlf.txt").write_bytes(b"one\r\ntwo\r\nthree\r\n")
        self.record("--range", "1:2", path="crlf.txt")
        self.assertEqual(self.check("--range", "1:2", path="crlf.txt")["state"], "reused")
        partial = self.check("--range", "2:3", path="crlf.txt")
        self.assertEqual(partial["state"], "partial")
        self.assertEqual(partial["missing_ranges"], [[3, 3]])

    def test_range_validation(self) -> None:
        for value in ("0:1", "3:2", "1:9"):
            result = self.cli(
                "check", "--session", "s1", "--task", "t1", "--path", "a.txt",
                "--range", value,
            )
            self.assertEqual(result.returncode, 2, value)

    def test_large_file_is_not_hashed_for_reuse(self) -> None:
        with patch.object(read_ledger, "MAX_FILE_BYTES", 4):
            decision = read_ledger.check_delivery(
                self.target,
                session_id="s1",
                task_id="t1",
                relpath="a.txt",
                full=True,
            )
        self.assertEqual(decision["state"], "too-large")
        self.assertFalse(decision["reusable"])

    def test_windows_case_normalization_is_explicit(self) -> None:
        with patch("read_ledger.os.path.normcase", side_effect=ntpath.normcase):
            self.assertEqual(read_ledger._path_key("Docs/A.md"), "docs\\a.md")

    def test_status_without_ledger_is_read_only(self) -> None:
        status = self.cli("status", "--session", "none")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["entries"], 0)
        self.assertFalse((self.target / ".ai").exists())


if __name__ == "__main__":
    unittest.main()
