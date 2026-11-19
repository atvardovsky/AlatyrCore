from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import runtime_store  # noqa: E402


class RuntimeStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "target"
        self.target.mkdir()

    def cli(self, *arguments: str, input: bytes | None = None):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(ROOT / "tools/runtime_store.py"),
                "--target",
                str(self.target),
                *arguments,
            ],
            capture_output=True,
            input=input,
            text=input is None,
            check=False,
        )

    def test_put_dedup_index_and_bounded_get(self) -> None:
        first = runtime_store.put(
            self.target,
            kind="validation",
            task="TASK-1",
            summary="85 checks passed",
            data=b"full validation report\n",
        )
        second = runtime_store.put(
            self.target,
            kind="validation",
            task="TASK-1",
            summary="updated summary",
            data=b"full validation report\n",
        )
        third = runtime_store.put(
            self.target,
            kind="validation",
            task="TASK-2",
            summary="another task",
            data=b"full validation report\n",
        )

        self.assertFalse(first["deduplicated"])
        self.assertTrue(second["deduplicated"])
        self.assertFalse(second["repaired"])
        self.assertEqual(first["entry"]["digest"], second["entry"]["digest"])
        self.assertEqual(third["entry"]["digest"], first["entry"]["digest"])
        self.assertEqual(first["entry"]["summary"], "85 checks passed")
        self.assertEqual(second["entry"]["summary"], "updated summary")
        blobs = list((self.target / ".ai/.runtime/store/blobs").iterdir())
        self.assertEqual(len(blobs), 1)

        index = runtime_store.index_entries(
            self.target, task="TASK-1", kind="validation", limit=10
        )
        self.assertEqual(index["total"], 2)
        self.assertEqual(index["selected"], 1)
        self.assertEqual(index["entries"][0]["summary"], "updated summary")
        self.assertNotIn("full validation report", json.dumps(index))

        raw, size = runtime_store.get_bytes(
            self.target, first["entry"]["digest"], max_bytes=8
        )
        self.assertEqual(raw, b"full val")
        self.assertEqual(size, len(b"full validation report\n"))

    def test_corrupt_existing_blob_is_atomically_repaired(self) -> None:
        original = b"example log\n"
        first = runtime_store.put(
            self.target,
            kind="log",
            task=None,
            summary=None,
            data=original,
        )
        blob = self.target / first["path"]
        corrupted = b"X" + original[1:]
        self.assertEqual(len(corrupted), len(original))
        blob.write_bytes(corrupted)

        retry = runtime_store.put(
            self.target,
            kind="log",
            task=None,
            summary=None,
            data=original,
        )

        self.assertFalse(retry["deduplicated"])
        self.assertTrue(retry["repaired"])
        self.assertEqual(
            runtime_store.get_bytes(
                self.target, retry["entry"]["digest"], max_bytes=100
            )[0],
            original,
        )

    def test_cli_put_requires_write_and_index_is_read_only(self) -> None:
        empty = self.cli("index")
        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertEqual(json.loads(empty.stdout)["total"], 0)
        self.assertFalse((self.target / ".ai").exists())

        source = self.target / "output.log"
        source.write_bytes(b"line one\nline two\n")
        result = self.cli(
            "put", "--kind", "log", "--task", "TASK-1", "--file", str(source)
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --write", result.stderr)

        result = self.cli(
            "put",
            "--write",
            "--kind",
            "log",
            "--task",
            "TASK-1",
            "--summary",
            "two lines",
            "--file",
            str(source),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        digest = payload["entry"]["digest"]
        index_path = self.target / ".ai/.runtime/store/index.json"
        before = (index_path.read_bytes(), index_path.stat().st_mtime_ns)
        listing = self.cli("index", "--task", "TASK-1")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(json.loads(listing.stdout)["selected"], 1)
        self.assertEqual((index_path.read_bytes(), index_path.stat().st_mtime_ns), before)

        excerpt = self.cli("get", "--digest", digest, "--max-bytes", "4")
        self.assertEqual(excerpt.returncode, 0, excerpt.stderr)
        self.assertEqual(excerpt.stdout, "line")
        self.assertIn("truncated", excerpt.stderr)

        output = self.target / "restored.log"
        copied = self.cli("get", "--digest", digest, "--output", "restored.log")
        self.assertNotEqual(copied.returncode, 0)
        copied = self.cli(
            "get", "--digest", digest, "--output", "restored.log", "--write"
        )
        self.assertEqual(copied.returncode, 0, copied.stderr)
        self.assertEqual(output.read_bytes(), source.read_bytes())

    def test_stdin_put_and_unsafe_paths_are_bounded(self) -> None:
        result = self.cli(
            "put",
            "--write",
            "--kind",
            "log",
            "--stdin",
            "--summary",
            "stdin",
            input=b"captured\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        digest = json.loads(result.stdout)["entry"]["digest"]
        self.assertEqual(
            runtime_store.get_bytes(self.target, digest, max_bytes=100)[0],
            b"captured\n",
        )

        outside = Path(self.temporary.name) / "outside.log"
        outside.write_bytes(b"outside")
        copied = self.cli(
            "get", "--digest", digest, "--output", "../outside.log", "--write"
        )
        self.assertNotEqual(copied.returncode, 0)
        self.assertIn("escapes", copied.stderr)

        linked_target = Path(self.temporary.name) / "linked-target"
        linked_target.mkdir()
        (linked_target / ".ai").symlink_to(
            Path(self.temporary.name) / "elsewhere", target_is_directory=True
        )
        with self.assertRaisesRegex(ValueError, "symlink"):
            runtime_store.put(
                linked_target,
                kind="log",
                task=None,
                summary=None,
                data=b"blocked",
            )

    def test_digest_mismatch_and_size_bound_fail_closed(self) -> None:
        result = runtime_store.put(
            self.target,
            kind="log",
            task=None,
            summary=None,
            data=b"trusted",
        )
        blob = self.target / result["path"]
        blob.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "digest"):
            runtime_store.get_bytes(
                self.target, result["entry"]["digest"], max_bytes=100
            )
        with patch("runtime_store.MAX_BLOB_BYTES", 4):
            with self.assertRaisesRegex(ValueError, "exceeds"):
                runtime_store.put(
                    self.target,
                    kind="log",
                    task=None,
                    summary=None,
                    data=b"too large",
                )


if __name__ == "__main__":
    unittest.main()
