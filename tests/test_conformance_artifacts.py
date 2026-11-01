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
    ARTIFACT_REQUIRED_ENV,
    ARTIFACT_ROOT_ENV,
    METADATA,
    artifact_required,
    materialize_support_profile,
    publish_support_profile,
)
from target_adapter_validation.context import ValidationContext  # noqa: E402


class ConformanceArtifactTests(unittest.TestCase):
    def test_fresh_outputs_preserve_metadata_and_unrelated_target_content(self) -> None:
        import stat
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "artifacts"
            source, target = artifacts / "source", root / "target"
            source.mkdir(parents=True); target.mkdir()
            (source / ".ai").mkdir()
            (source / ".ai/owner.md").write_bytes(b"owner")
            script = source / "check.sh"
            script.write_bytes(b"#!/bin/sh\nexit 0\n")
            script.chmod(0o755)
            timestamp = 1_700_000_000_000_000_000
            os.utime(script, ns=(timestamp, timestamp))
            (target / "README.md").write_bytes(b"project-owned")
            (target / ".git").mkdir()
            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("kernel", source))
                self.assertEqual(materialize_support_profile("kernel", target), 2)
            copied = target / "check.sh"
            self.assertEqual(copied.read_bytes(), script.read_bytes())
            self.assertEqual(copied.stat().st_mtime_ns, timestamp)
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(copied.stat().st_mode), 0o755)
            self.assertEqual((target / "README.md").read_bytes(), b"project-owned")
            self.assertEqual(list((target / ".git").iterdir()), [])

    def test_late_file_collision_is_not_overwritten(self) -> None:
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, artifacts = (root / name for name in ("source", "target", "artifacts"))
            source.mkdir(); target.mkdir()
            (source / ".ai").mkdir()
            (source / ".ai/owner.md").write_bytes(b"owner")
            (source / "AGENTS.md").write_bytes(b"source instructions")
            copytree = shutil.copytree
            def publish_peer_file(*args, **kwargs):
                result = copytree(*args, **kwargs)
                (target / "AGENTS.md").write_bytes(b"peer instructions")
                return result
            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("kernel", source))
                with patch("conformance_artifacts.shutil.copytree", side_effect=publish_peer_file):
                    with self.assertRaises(FileExistsError):
                        materialize_support_profile("kernel", target)
            self.assertEqual((target / "AGENTS.md").read_bytes(), b"peer instructions")

    def test_publication_rejects_source_overlap_before_creating_outputs(self) -> None:
        for placement in ("destination", "temporary", "nested"):
            with self.subTest(placement=placement), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if placement == "nested":
                    source, artifacts = root / "source", root / "source/artifacts"
                else:
                    artifacts = root / "artifacts"
                    name = "support-profile-kernel" if placement == "destination" else f".support-profile-kernel-{os.getpid()}"
                    source = artifacts / name
                source.mkdir(parents=True)
                (source / "owner.md").write_bytes(b"owner")
                before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
                with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                    with self.assertRaisesRegex(ValueError, "must not overlap"):
                        publish_support_profile("kernel", source)
                self.assertEqual(sorted(path.relative_to(root).as_posix() for path in root.rglob("*")), before)
                self.assertEqual((source / "owner.md").read_bytes(), b"owner")

    def test_existing_support_cannot_be_merged_or_retimed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, artifacts = (root / name for name in ("source", "target", "artifacts"))
            observed = source / ".ai/assistant/approvals"
            observed.mkdir(parents=True)
            (observed / "approval.json").write_bytes(b"{}")
            old = 1_700_000_000_000_000_000
            os.utime(observed, ns=(old, old))
            target.mkdir()
            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("kernel", source))
                self.assertEqual(materialize_support_profile("kernel", target), 1)
                watched = target / ".ai/assistant/approvals"
                newer = old + 4_000_000_000
                os.utime(watched, ns=(newer, newer))
                context = ValidationContext(target)
                context.status(watched)
                rejected = False
                try:
                    materialize_support_profile("kernel", target)
                except ValueError:
                    rejected = True
                self.assertEqual(watched.stat().st_mtime_ns, newer,
                                 "cache merge restored an older observed directory timestamp")
                self.assertTrue(rejected, "existing support must not be a cache destination")
                self.assertEqual(context.finalize(), ())
                self.assertEqual((watched / "approval.json").read_bytes(), b"{}")

    def test_destination_collision_is_rejected_before_any_copy(self) -> None:
        for kind in ("same-file", "different-file", "directory", "dangling-link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, target, artifacts = (root / name for name in ("source", "target", "artifacts"))
                source.mkdir(); target.mkdir()
                (source / ".ai").mkdir()
                (source / ".ai/owner.md").write_bytes(b"owner")
                (source / "AGENTS.md").write_bytes(b"source instructions")
                collision = target / "AGENTS.md"
                if kind == "directory":
                    collision.mkdir()
                elif kind == "dangling-link":
                    try:
                        collision.symlink_to(target / "missing")
                    except OSError:
                        self.skipTest("symlinks unavailable")
                else:
                    collision.write_bytes(b"source instructions" if kind == "same-file" else b"project instructions")
                before = collision.lstat()
                with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                    self.assertTrue(publish_support_profile("kernel", source))
                    with self.assertRaisesRegex(ValueError, "destination already exists"):
                        materialize_support_profile("kernel", target)
                self.assertFalse((target / ".ai").exists())
                after = collision.lstat()
                self.assertEqual((after.st_ino, after.st_mtime_ns, after.st_size),
                                 (before.st_ino, before.st_mtime_ns, before.st_size))

    def test_artifact_and_destination_must_not_overlap(self) -> None:
        for relationship in ("same", "child", "parent"):
            with self.subTest(relationship=relationship), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, artifacts = root / "source", root / "artifacts"
                source.mkdir()
                (source / "owner.md").write_bytes(b"owner")
                with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                    self.assertTrue(publish_support_profile("kernel", source))
                    artifact = artifacts / "support-profile-kernel"
                    metadata = (artifact / METADATA).read_bytes()
                    target = {"same": artifact, "child": artifact / "child", "parent": artifacts}[relationship]
                    if relationship == "child":
                        target.mkdir()
                    with self.assertRaisesRegex(ValueError, "must not overlap"):
                        materialize_support_profile("kernel", target)
                    self.assertEqual((artifact / METADATA).read_bytes(), metadata)
                    self.assertEqual((artifact / "owner.md").read_bytes(), b"owner")

    def test_requirement_signal_is_independent_from_artifact_location(self) -> None:
        with patch.dict(
            os.environ,
            {ARTIFACT_ROOT_ENV: "/tmp/example"},
            clear=True,
        ):
            self.assertFalse(artifact_required())
        with patch.dict(
            os.environ,
            {
                ARTIFACT_ROOT_ENV: "/tmp/example",
                ARTIFACT_REQUIRED_ENV: "1",
            },
            clear=True,
        ):
            self.assertTrue(artifact_required())

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
