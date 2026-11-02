from __future__ import annotations

import ctypes
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch


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
import conformance_artifacts as artifacts  # noqa: E402


class WindowsNewFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = SimpleNamespace(CreateFileW=Mock(return_value=0x100000001), CloseHandle=Mock(return_value=1))
        self.crt = SimpleNamespace(open_osfhandle=Mock(return_value=37))
        self.stream = MagicMock()
        self.stream.__enter__.return_value = self.stream
        self.stream.__exit__.return_value = False
        self.api_loader = artifacts._windows_file_api
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(artifacts, "_windows_file_api", return_value=self.api))
        stack.enter_context(patch.dict(sys.modules, {"msvcrt": self.crt}))
        self.fdopen = stack.enter_context(patch("conformance_artifacts.os.fdopen", return_value=self.stream))
        self.close = stack.enter_context(patch("conformance_artifacts.os.close"))
        self.last_error = stack.enter_context(patch.object(ctypes, "get_last_error", return_value=5, create=True))
        self.win_error = stack.enter_context(
            patch.object(ctypes, "WinError", return_value=PermissionError("native creation failed"), create=True)
        )

    def test_api_declares_pointer_sized_handles(self) -> None:
        from ctypes import wintypes
        self.api_loader.cache_clear()
        self.addCleanup(self.api_loader.cache_clear)
        with patch.object(ctypes, "WinDLL", return_value=self.api, create=True) as load:
            self.assertIs(self.api_loader(), self.api)
            self.assertIs(self.api_loader(), self.api)
        load.assert_called_once_with("kernel32", use_last_error=True)
        self.assertIs(self.api.CreateFileW.restype, wintypes.HANDLE)
        self.assertEqual(self.api.CloseHandle.argtypes, [wintypes.HANDLE])

    def test_creation_uses_no_follow_and_transfers_handle_once(self) -> None:
        with artifacts._windows_new_file("target.bin") as stream:
            self.assertIs(stream, self.stream)
        self.api.CreateFileW.assert_called_once_with("target.bin", 0x40000000, 0, None, 1, 0x00200080, None)
        self.crt.open_osfhandle.assert_called_once_with(
            0x100000001, getattr(os, "O_BINARY", 0) | getattr(os, "O_NOINHERIT", 0)
        )
        self.fdopen.assert_called_once_with(37, "wb", closefd=False)
        self.close.assert_called_once_with(37)
        self.api.CloseHandle.assert_not_called()

    def test_native_creation_errors_never_transfer_or_close_invalid_handles(self) -> None:
        self.api.CreateFileW.return_value = ctypes.c_void_p(-1).value
        for code, expected in ((80, FileExistsError), (183, FileExistsError), (5, PermissionError)):
            with self.subTest(code=code):
                self.last_error.return_value = code
                with self.assertRaises(expected):
                    with artifacts._windows_new_file("target.bin"):
                        self.fail("failed creation must not yield a stream")
        self.crt.open_osfhandle.assert_not_called()
        self.close.assert_not_called()
        self.api.CloseHandle.assert_not_called()

    def test_transfer_failure_closes_native_handle(self) -> None:
        for error in (OSError("transfer failed"), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                self.api.CloseHandle.reset_mock()
                self.crt.open_osfhandle.side_effect = error
                with self.assertRaises(type(error)):
                    with artifacts._windows_new_file("target.bin"):
                        self.fail("failed transfer must not yield a stream")
                self.api.CloseHandle.assert_called_once_with(0x100000001)
        self.close.assert_not_called()
        self.fdopen.assert_not_called()

    def test_native_cleanup_failure_is_not_suppressed(self) -> None:
        self.crt.open_osfhandle.side_effect = OSError("transfer failed")
        self.api.CloseHandle.return_value = 0
        with self.assertRaisesRegex(PermissionError, "native creation failed"):
            with artifacts._windows_new_file("target.bin"):
                self.fail("failed cleanup must not yield a stream")
        self.win_error.assert_called_once_with(5)
        self.close.assert_not_called()

    def test_stream_creation_failure_closes_descriptor(self) -> None:
        self.fdopen.side_effect = OSError("stream failed")
        with self.assertRaisesRegex(OSError, "stream failed"):
            with artifacts._windows_new_file("target.bin"):
                self.fail("failed stream creation must not yield")
        self.close.assert_called_once_with(37)
        self.api.CloseHandle.assert_not_called()

    def test_body_and_flush_failures_close_descriptor(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "copy failed"):
            with artifacts._windows_new_file("target.bin"):
                raise RuntimeError("copy failed")
        self.close.assert_called_once_with(37)
        self.close.reset_mock()
        self.stream.__exit__.side_effect = OSError("flush failed")
        with self.assertRaisesRegex(OSError, "flush failed"):
            with artifacts._windows_new_file("target.bin"):
                pass
        self.close.assert_called_once_with(37)
        self.api.CloseHandle.assert_not_called()


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

    def test_late_nested_collisions_preserve_peer_entries(self) -> None:
        paths = ("owner.md", "assistant/owner.md", "assistant/approvals/owner.md")
        for relative in paths:
            for kind in ("file", "directory", "symlink", "dangling-link"):
                with self.subTest(relative=relative, kind=kind), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source, target, artifacts = (root / name for name in ("source", "target", "artifacts"))
                    cached = source / ".ai" / relative
                    cached.parent.mkdir(parents=True)
                    cached.write_bytes(b"cached owner")
                    target.mkdir()
                    destination = target / ".ai" / relative
                    peer = root / "peer.md"
                    peer.write_bytes(b"peer bytes")
                    makedirs = os.makedirs
                    injected = []

                    def introduce_peer(name, *args, **kwargs):
                        result = makedirs(name, *args, **kwargs)
                        if Path(name) == destination.parent and not injected:
                            if kind == "file":
                                destination.write_bytes(b"peer bytes")
                            elif kind == "directory":
                                destination.mkdir()
                                (destination / "peer.md").write_bytes(b"peer bytes")
                            else:
                                referent = peer if kind == "symlink" else root / "missing.md"
                                try:
                                    destination.symlink_to(referent)
                                except OSError:
                                    self.skipTest("symlinks unavailable")
                            injected.append(destination.lstat())
                        return result

                    with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                        self.assertTrue(publish_support_profile("kernel", source))
                        with patch("conformance_artifacts.shutil.os.makedirs", side_effect=introduce_peer):
                            with self.assertRaises(shutil.Error) as raised:
                                materialize_support_profile("kernel", target)
                    self.assertEqual(len(injected), 1, "late collision boundary was not exercised")
                    self.assertIn(destination.name, str(raised.exception))
                    after = destination.lstat()
                    self.assertEqual((after.st_ino, after.st_mode, after.st_mtime_ns),
                                     (injected[0].st_ino, injected[0].st_mode, injected[0].st_mtime_ns))
                    self.assertEqual(peer.read_bytes(), b"peer bytes")
                    if kind == "file":
                        self.assertEqual(destination.read_bytes(), b"peer bytes")
                    elif kind == "directory":
                        self.assertEqual((destination / "peer.md").read_bytes(), b"peer bytes")
                    else:
                        self.assertTrue(destination.is_symlink())
                        if kind == "dangling-link":
                            self.assertFalse((root / "missing.md").exists())

    def test_fresh_nested_files_preserve_content_and_metadata(self) -> None:
        import stat
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, artifacts = (root / name for name in ("source", "target", "artifacts"))
            target.mkdir()
            paths = ("check.sh", ".ai/check.sh", ".ai/assistant/tools/check.sh")
            timestamp = 1_700_000_000_000_000_000
            for relative in paths:
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"#!/bin/sh\nexit 0\n")
                path.chmod(0o755)
                os.utime(path, ns=(timestamp, timestamp))
            for path in source.rglob("*"):
                if path.is_dir():
                    os.utime(path, ns=(timestamp, timestamp))
            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("kernel", source))
                self.assertEqual(materialize_support_profile("kernel", target), len(paths))
            for original in source.rglob("*"):
                copied = target / original.relative_to(source)
                with self.subTest(path=original.relative_to(source).as_posix()):
                    self.assertEqual(copied.stat().st_mtime_ns, original.stat().st_mtime_ns)
                    if os.name != "nt":
                        self.assertEqual(stat.S_IMODE(copied.stat().st_mode),
                                         stat.S_IMODE(original.stat().st_mode))
                    if original.is_file():
                        self.assertEqual(copied.read_bytes(), original.read_bytes())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs unavailable")
    def test_nonregular_cache_entry_is_rejected_before_opening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, artifacts = (root / name for name in ("source", "target", "artifacts"))
            (source / ".ai").mkdir(parents=True)
            (source / ".ai/owner.md").write_bytes(b"owner")
            target.mkdir()
            real_open = open
            with patch.dict(os.environ, {ARTIFACT_ROOT_ENV: str(artifacts)}):
                self.assertTrue(publish_support_profile("kernel", source))
                fifo = artifacts / "support-profile-kernel/.ai/late.pipe"
                os.mkfifo(fifo)

                def reject_fifo_open(file, *args, **kwargs):
                    if isinstance(file, (str, os.PathLike)) and Path(file) == fifo:
                        self.fail("nonregular cache entry must be rejected before stream open")
                    return real_open(file, *args, **kwargs)

                with patch("builtins.open", side_effect=reject_fifo_open), patch("io.open", side_effect=reject_fifo_open):
                    with self.assertRaises(shutil.Error):
                        materialize_support_profile("kernel", target)
                self.assertFalse((target / ".ai/late.pipe").exists())

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
