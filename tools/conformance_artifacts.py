"""Run-local immutable scaffold artifacts shared by conformance checks."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT_ENV = "ALATYR_CONFORMANCE_ARTIFACT_ROOT"
ARTIFACT_REQUIRED_ENV = "ALATYR_CONFORMANCE_ARTIFACT_REQUIRED"
METADATA = ".alatyr-conformance-artifact.json"
SOURCE_PATHS = (
    ROOT / "VERSION",
    ROOT / "ADAPTER_SCHEMA_VERSION",
    ROOT / "TEMPLATE_VERSION",
    ROOT / "framework",
    ROOT / "templates" / "target",
    ROOT / "tools",
)


def _files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file()
        and "__pycache__" not in candidate.parts
        and candidate.suffix not in {".pyc", ".pyo"}
    )


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in _files(path):
        if file.name == METADATA:
            continue
        digest.update(file.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


@lru_cache(maxsize=1)
def source_digest() -> str:
    digest = hashlib.sha256()
    for source in SOURCE_PATHS:
        for path in _files(source):
            digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def artifact_root() -> Path | None:
    value = os.environ.get(ARTIFACT_ROOT_ENV)
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        return None
    return path


def artifact_required() -> bool:
    return os.environ.get(ARTIFACT_REQUIRED_ENV) == "1"


def publish_support_profile(profile: str, source: Path) -> bool:
    root = artifact_root()
    if root is None:
        return False
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"support-profile-{profile}"
    temporary = root / f".support-profile-{profile}-{os.getpid()}"
    shutil.rmtree(temporary, ignore_errors=True)
    shutil.copytree(source, temporary)
    artifact_digest = tree_digest(temporary)
    (temporary / METADATA).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "artifact_kind": "alatyr-run-local-scaffold",
                "profile": profile,
                "source_digest": source_digest(),
                "artifact_digest": artifact_digest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        temporary.replace(destination)
    except FileExistsError:
        shutil.rmtree(temporary, ignore_errors=True)
    return _valid_artifact(destination, profile)


def _valid_artifact(path: Path, profile: str) -> bool:
    try:
        metadata = json.loads((path / METADATA).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        isinstance(metadata, dict)
        and metadata.get("schema_version") == 1
        and metadata.get("artifact_kind") == "alatyr-run-local-scaffold"
        and metadata.get("profile") == profile
        and metadata.get("source_digest") == source_digest()
        and metadata.get("artifact_digest") == tree_digest(path)
    )


def materialize_support_profile(profile: str, target: Path) -> int | None:
    root = artifact_root()
    source = root / f"support-profile-{profile}" if root is not None else None
    if source is None or not _valid_artifact(source, profile):
        return None
    copied = 0
    for item in sorted(source.iterdir(), key=lambda path: path.name):
        if item.name == METADATA:
            continue
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
            copied += sum(1 for path in item.rglob("*") if path.is_file())
        elif item.is_file():
            shutil.copy2(item, destination)
            copied += 1
    return copied
