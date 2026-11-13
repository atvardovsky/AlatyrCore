"""Exact, model-local locations for immutable analysis bytes; never authority."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable

from analysis_evidence import MAX_ARTIFACT_BYTES, MAX_EVIDENCE_BYTES, artifact_bindings
from support_write_transaction import safe_output
from target_validation_support import is_target_relative_path

MAX_MANIFEST_BYTES = 64 * 1024
MAX_ENTRIES = 128


def safe_path(value: object) -> str:
    if (not isinstance(value, str) or len(value) > 1024 or not is_target_relative_path(value)
            or "\\" in value or ":" in value or PureWindowsPath(value).drive
            or PurePosixPath(value).as_posix() != value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("unsafe retained artifact path")
    if any(re.match(r"^(?:\.env(?:[.-]|$)|secrets?(?:[.-]|$)|credentials?(?:[.-]|$)|keys?(?:[.-]|$))", part, re.I)
           or re.search(r"\.(?:pem|key|p12|pfx|env)$", part, re.I) for part in value.split("/")):
        raise ValueError("private artifact paths cannot be retained")
    return value


def binding(value: object) -> dict:
    if (not isinstance(value, dict) or set(value) != {"path", "sha256"}
            or not isinstance(value["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None):
        raise ValueError("retained artifacts require exact path/hash bindings")
    safe_path(value["path"])
    return value


def consumed_ignored(model: dict, is_ignored: Callable) -> dict[str, str]:
    result, identities = {}, {}
    for path, digest in artifact_bindings(model):
        binding({"path": path, "sha256": digest})
        identity = path.casefold()
        if identity in identities and identities[identity] != path:
            raise ValueError("ambiguous portable artifact identities")
        identities[identity] = path
        state = is_ignored(path)
        if state is None:
            raise ValueError("artifact retainability is unavailable")
        if path in result and result[path] != digest:
            raise ValueError("conflicting consumed artifact hashes")
        if state:
            result[path] = digest
    if len(result) > MAX_ENTRIES:
        raise ValueError("retained artifact entry limit exceeded")
    return result


def read_safe(target: Path, relative: str, limit: int, read: Callable) -> bytes | None:
    safe_path(relative)
    safe_output(target, target / relative)
    raw = read(relative, limit)
    if raw is not None and (not isinstance(raw, bytes) or len(raw) > limit):
        raise ValueError("retained artifact exceeds byte budget")
    return raw


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate manifest key")
        value[key] = item
    return value


def load_aliases(target: Path, task_id: str, source_model: dict, model: dict,
                 manifest_binding: dict, *, read: Callable, is_ignored: Callable) -> dict[str, str]:
    """Verify a closed manifest and both available originals and retained copies."""
    binding(source_model)
    binding(manifest_binding)
    if not isinstance(task_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", task_id) is None:
        raise ValueError("unsafe retained task identity")
    prefix = f".ai/assistant/task-evidence/{task_id}/{source_model['sha256']}/"
    if not manifest_binding["path"].startswith(prefix) or is_ignored(manifest_binding["path"]) is not False:
        raise ValueError("manifest must be retainable in its exact task/model namespace")
    raw = read_safe(target, manifest_binding["path"], MAX_MANIFEST_BYTES, read)
    if raw is None or hashlib.sha256(raw).hexdigest() != manifest_binding["sha256"]:
        raise ValueError("retained manifest hash mismatch")
    manifest = json.loads(raw, object_pairs_hook=unique_object)
    if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "record_kind", "source_model", "artifacts"}
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or manifest["record_kind"] != "alatyr-retained-analysis-artifacts"
            or manifest["source_model"] != source_model):
        raise ValueError("retained manifest does not bind the exact source model")
    needed = consumed_ignored(model, is_ignored)
    rows = manifest["artifacts"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ENTRIES:
        raise ValueError("retained manifest requires bounded nonempty entries")
    aliases, destinations, total = {}, set(), 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"source_path", "retained"}:
            raise ValueError("invalid retained artifact entry")
        logical = safe_path(row["source_path"])
        physical = binding(row["retained"])
        destination = physical["path"]
        if (logical in aliases or logical not in needed or physical["sha256"] != needed[logical]
                or destination.casefold() in destinations
                or not destination.startswith(prefix + "artifacts/")
                or is_ignored(destination) is not False):
            raise ValueError("retained mapping has duplicate, foreign or mismatched identity")
        limit = min(MAX_ARTIFACT_BYTES, MAX_EVIDENCE_BYTES - total)
        copy = read_safe(target, destination, limit, read)
        if copy is None or hashlib.sha256(copy).hexdigest() != needed[logical]:
            raise ValueError("retained artifact hash mismatch")
        original = read_safe(target, logical, limit, read)
        if original is not None and hashlib.sha256(original).hexdigest() != needed[logical]:
            raise ValueError("extant original conflicts with retained evidence")
        total += len(copy)
        aliases[logical] = destination
        destinations.add(destination.casefold())
    if set(aliases) != set(needed):
        raise ValueError("retained mapping must cover exactly consumed ignored artifacts")
    return aliases
