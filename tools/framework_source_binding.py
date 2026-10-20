"""Resolve installed source identity without activating or changing a checkout."""

from __future__ import annotations

import re
import io
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from target_validation_support import GitEvidenceView


def resolve_installed_commit(source: Path, pin: str, version: str) -> str:
    if not isinstance(pin, str) or re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", pin) is None:
        raise ValueError("installed source_commit must be a full Git commit ID")
    git = GitEvidenceView(source)
    revision = git.resolve_ref(pin)
    if revision is None or revision.casefold() != pin.casefold():
        raise ValueError("installed source_commit is unavailable locally; provide its source history (no automatic fetch)")
    recorded = git.bounded_file_at_ref(revision, "VERSION", 1024)
    if recorded is None or recorded.decode("utf-8").strip() != version:
        raise ValueError("installed source_commit VERSION differs from the target manifest")
    return revision


def materialize_git_subtree(source: Path, commit: str, relpath: str, destination: Path) -> bool:
    """Copy bounded regular Git blobs, never archive links or executable instructions."""
    git = GitEvidenceView(source)
    revision = git.resolve_ref(commit)
    prefix = PurePosixPath(relpath)
    if revision is None or prefix.is_absolute() or any(part in {"..", ".git"} for part in prefix.parts) or "\\" in relpath:
        return False
    listing = subprocess.run(["git", "ls-tree", "-r", "-l", "-z", revision, "--", relpath], cwd=source, check=False, capture_output=True)
    if listing.returncode:
        return False
    entries = [item for item in listing.stdout.split(b"\0") if item]
    if not entries or len(entries) > 4096:
        return False
    remaining = 64 * 1024 * 1024
    requests = []
    for entry in entries:
        metadata, separator, raw_path = entry.partition(b"\t")
        if not separator or not metadata.startswith((b"100644 blob ", b"100755 blob ")):
            return False
        fields = metadata.split()
        if len(fields) != 4 or not fields[3].isdigit() or re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", fields[2]) is None:
            return False
        size = int(fields[3])
        if size > min(remaining, 4 * 1024 * 1024):
            return False
        try:
            value = raw_path.decode("utf-8")
        except UnicodeError:
            return False
        path = PurePosixPath(value)
        if path.is_absolute() or "\\" in value or any(part in {"..", ".git"} or ":" in part for part in path.parts):
            return False
        try:
            relative = path.relative_to(prefix)
        except ValueError:
            return False
        remaining -= size
        requests.append((relative, fields[2], size))
    # Immutable blob IDs give exact content without archive attributes or one
    # Git process per file. Preflight sizes bound the complete batch response.
    batch = subprocess.run(["git", "cat-file", "--batch"], cwd=source, check=False,
        input=b"".join(oid + b"\n" for _, oid, _ in requests), capture_output=True)
    if batch.returncode:
        return False
    stream = io.BytesIO(batch.stdout)
    outputs = []
    for relative, oid, size in requests:
        header = stream.readline(256).split()
        if header != [oid, b"blob", str(size).encode("ascii")]:
            return False
        content = stream.read(size)
        if len(content) != size or stream.read(1) != b"\n":
            return False
        outputs.append((relative, content))
    if stream.read(1):
        return False
    for relative, content in outputs:
        output = destination.joinpath(*relative.parts)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
    return True


@contextmanager
def baseline_framework(source: Path, *, pin: str | None, version: str, role: str = "installed"):
    if not isinstance(role, str) or role not in {"installed", "candidate"}:
        raise ValueError("source role must be installed or candidate")
    if role == "candidate" or pin is None:
        yield source / "framework"
        return
    revision = resolve_installed_commit(source, pin, version)
    # A clean matching checkout needs no historical file materialization.
    versions = ("VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION")
    status = subprocess.run(["git", "status", "--porcelain=v1", "--ignored=matching", "--untracked-files=all", "--", "framework", *versions], cwd=source, check=False, capture_output=True)
    framework_root = source / "framework"
    if GitEvidenceView(source).resolve_ref("HEAD") == revision and status.returncode == 0 and not status.stdout and not framework_root.is_symlink() and not any(path.is_symlink() for path in framework_root.rglob("*")):
        yield source / "framework"
        return
    with tempfile.TemporaryDirectory(prefix="alatyr-installed-baseline-") as directory:
        framework = Path(directory) / "framework"
        if not materialize_git_subtree(source, revision, "framework", framework):
            raise ValueError("installed framework cannot be read as bounded regular Git blobs")
        git = GitEvidenceView(source)
        for name in versions:
            content = git.bounded_file_at_ref(revision, name, 1024)
            if content is not None:
                (framework.parent / name).write_bytes(content)
        yield framework
