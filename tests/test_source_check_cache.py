from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_check_cache import (  # noqa: E402
    SourceCheckCache,
    cache_key,
    check_result_key,
)


class SourceCheckCacheTests(unittest.TestCase):
    def repository(self, directory: str) -> Path:
        root = Path(directory)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        return root

    def test_round_trips_separate_timing_and_result_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = SourceCheckCache(self.repository(directory))

            cache.store("timing", "linux-3.13", {"checks": {"one": 1.5}})
            cache.store("results", "full-linux-3.13", {"status": "passed"})

            self.assertEqual(
                cache.load("timing", "linux-3.13").value,
                {"checks": {"one": 1.5}},
            )
            self.assertEqual(
                cache.load("results", "full-linux-3.13").value,
                {"status": "passed"},
            )

    def test_round_trips_content_addressed_check_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = SourceCheckCache(self.repository(directory))
            identity = {"contract": "test", "input": "sha256:value"}
            key = check_result_key("example-check", identity)
            cache.store("checks", key, {"status": "passed"})

            self.assertEqual(
                cache.load("checks", key).value,
                {"status": "passed"},
            )
            self.assertEqual(key, check_result_key("example-check", identity))

    def test_runtime_cache_keys_partition_result_profiles_only(self) -> None:
        timing = cache_key("full", include_profile=False)

        self.assertNotIn("full", timing)
        self.assertEqual(cache_key("full"), f"full-{timing}")

    def test_prune_keeps_newest_bounded_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = SourceCheckCache(self.repository(directory))
            paths = [
                cache.store("checks", f"check-{index}", {"index": index})
                for index in range(4)
            ]
            for index, path in enumerate(paths):
                os.utime(path, ns=(index + 1, index + 1))

            removed = cache.prune("checks", max_records=2)

            self.assertEqual(removed, tuple(paths[:2]))
            self.assertEqual(
                sorted(path.name for path in paths if path.exists()),
                ["check-2.json", "check-3.json"],
            )

    def test_prune_rejects_non_positive_retention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = SourceCheckCache(self.repository(directory))

            with self.assertRaisesRegex(ValueError, "retention must be positive"):
                cache.prune("checks", max_records=0)

    def test_corruption_fails_open_as_a_cache_miss(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = SourceCheckCache(self.repository(directory))
            path = cache.store("timing", "linux", {"checks": {}})
            path.write_text("{", encoding="utf-8")

            loaded = cache.load("timing", "linux")

            self.assertEqual(loaded.status, "corrupt")
            self.assertIsNone(loaded.value)

    def test_contract_mismatch_is_not_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = SourceCheckCache(self.repository(directory))
            path = cache.store("results", "full", {"status": "passed"})
            record = json.loads(path.read_text(encoding="utf-8"))
            record["schema_version"] = 99
            path.write_text(json.dumps(record), encoding="utf-8")

            self.assertEqual(cache.load("results", "full").status, "unsupported")

    def test_rejects_unsafe_keys_and_symlink_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.repository(directory)
            cache = SourceCheckCache(root)
            with self.assertRaises(ValueError):
                cache.load("results", "../escape")
            record = cache.store("results", "full", {"status": "passed"})
            target = record.with_name("other.json")
            target.write_text("{}", encoding="utf-8")
            record.unlink()
            try:
                record.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            self.assertEqual(cache.load("results", "full").status, "unsafe")


if __name__ == "__main__":
    unittest.main()
