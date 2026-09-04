from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_check_cache import SourceCheckCache, cache_key  # noqa: E402


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

    def test_runtime_cache_keys_partition_result_profiles_only(self) -> None:
        timing = cache_key("full", include_profile=False)

        self.assertNotIn("full", timing)
        self.assertEqual(cache_key("full"), f"full-{timing}")

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
