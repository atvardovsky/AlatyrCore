from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from conformance_artifacts import (  # noqa: E402
    ARTIFACT_ROOT_ENV,
    METADATA,
    materialize_support_profile,
    publish_support_profile,
)


class ConformanceArtifactTests(unittest.TestCase):
    def test_round_trip_copies_only_valid_run_local_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            artifacts = root / "artifacts"
            source.mkdir()
            target.mkdir()
            (source / ".ai").mkdir()
            (source / ".ai" / "example.txt").write_text("value\n", encoding="utf-8")

            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("kernel", source))
                self.assertEqual(materialize_support_profile("kernel", target), 1)

            self.assertEqual(
                (target / ".ai" / "example.txt").read_text(encoding="utf-8"),
                "value\n",
            )
            self.assertFalse((target / METADATA).exists())

    def test_missing_or_relative_artifact_root_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            with patch.dict(os.environ, {}, clear=True):
                self.assertIsNone(materialize_support_profile("kernel", target))
            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: "relative"}):
                self.assertIsNone(materialize_support_profile("kernel", target))

    def test_tampered_metadata_denies_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            artifacts = root / "artifacts"
            source.mkdir()
            target.mkdir()
            (source / "value.txt").write_text("value\n", encoding="utf-8")

            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("core", source))
                metadata = artifacts / "support-profile-core" / METADATA
                metadata.write_text("{}\n", encoding="utf-8")
                self.assertIsNone(materialize_support_profile("core", target))

    def test_tampered_artifact_content_denies_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            artifacts = root / "artifacts"
            source.mkdir()
            target.mkdir()
            (source / "value.txt").write_text("value\n", encoding="utf-8")

            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("standard", source))
                artifact = artifacts / "support-profile-standard" / "value.txt"
                artifact.write_text("tampered\n", encoding="utf-8")
                self.assertIsNone(materialize_support_profile("standard", target))


if __name__ == "__main__":
    unittest.main()
