"""Local Git-common-directory storage with a brief OS-held metadata lock."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from session_presence_contract import (
    MAX_BYTES, MAX_SESSIONS, POLICY_PATH, SOURCE_POLICY_PATH, decode_json, encoded_registry,
    now_text, presence_policy, scope_reference, timestamp, uid, validate_entry, validate_registry,
)
from session_presence_summary import same_worktree, summarize
from local_file_lock import file_lock


def safe_regular(path: Path, *, missing_ok: bool = False) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return
        raise
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("presence files must be regular files without symlinks or hardlinks")


def read_bounded(path: Path) -> bytes:
    safe_regular(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("unsafe presence file")
        return stream.read(MAX_BYTES + 1)


def load_policy(target: Path, *, source_contour: bool = False) -> dict[str, Any]:
    path = target / (SOURCE_POLICY_PATH if source_contour else POLICY_PATH)
    for parent in (target / ("tools" if source_contour else ".ai"), path.parent.parent, path.parent):
        if parent.is_symlink():
            raise ValueError("presence policy parent must not be a symlink")
    if not path.exists() and not path.is_symlink():
        if source_contour:
            raise ValueError("source presence policy is missing")
        return presence_policy({})
    return presence_policy(decode_json(read_bounded(path)), source_contour=source_contour)


def git_identity(target: Path) -> tuple[Path, Path, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}

    def git(argument: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(target), "rev-parse", argument],
            capture_output=True, text=True, env=env, timeout=10, check=False,
        )
        if result.returncode:
            raise ValueError("session presence requires an accessible Git worktree")
        return result.stdout.strip()

    worktree = Path(git("--show-toplevel")).resolve()
    common = Path(git("--git-common-dir"))
    common = (common if common.is_absolute() else target / common).resolve()
    if not common.is_dir():
        raise ValueError("Git common directory is unavailable")
    if not same_worktree(str(target), str(worktree)):
        raise ValueError("presence target must be the worktree root")
    repository_id = hashlib.sha256(os.fsencode(str(common))).hexdigest()
    return worktree, common / "alatyr-session-presence", repository_id


def safe_hub(hub: Path, *, create: bool) -> None:
    if create:
        hub.mkdir(mode=0o700, exist_ok=True)
    if hub.is_symlink() or (hub.exists() and not hub.is_dir()):
        raise ValueError("presence hub must be a directory, not a symlink")


@contextmanager
def registry_lock(hub: Path, timeout: float = 5.0) -> Iterator[None]:
    safe_hub(hub, create=True)
    path = hub / "registry.lock"
    with file_lock(path, timeout=timeout):
        yield


def load_registry(hub: Path, repository_id: str) -> dict[str, Any]:
    safe_hub(hub, create=False)
    path = hub / "sessions.json"
    if not path.exists() and not path.is_symlink():
        return {"schema_version": 1, "repository_id": repository_id, "sessions": {}}
    return validate_registry(decode_json(read_bounded(path)), repository_id)


def save_registry(hub: Path, value: dict[str, Any], repository_id: str) -> None:
    raw = encoded_registry(value, repository_id)
    safe_hub(hub, create=False)
    output = hub / "sessions.json"
    safe_regular(output, missing_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".sessions-", dir=hub)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        deadline = time.monotonic() + 5.0
        while True:
            safe_hub(hub, create=False)
            safe_regular(output, missing_ok=True)
            try:
                os.replace(temporary, output)
                break
            except PermissionError:
                # Windows readers can briefly hold handles without delete sharing.
                if os.name != "nt" or time.monotonic() >= deadline:
                    raise
                time.sleep(0.02)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def operate(target: Path, action: str, *, write: bool = False,
            session_uid: str | None = None, parent_uid: str | None = None,
            task: str | None = None, scope: list[str] | None = None,
            activity: str | None = None, expected_version: int | None = None,
            full: bool = False, source_contour: bool = False) -> dict[str, Any]:
    target = target.resolve()
    policy = load_policy(target, source_contour=source_contour)
    if action not in ("status", "detail", "register", "update", "leave"):
        raise ValueError("unsupported presence action")
    if action not in ("status", "detail") and not write:
        raise ValueError("presence mutations require --write and current-scope authorization")
    if not policy["enabled"]:
        if action not in ("status", "detail"):
            raise ValueError("session presence is disabled")
        return {"enabled": False, "sessions": []}
    worktree, hub, repository_id = git_identity(target)
    if action in ("status", "detail"):
        value = load_registry(hub, repository_id)
        detail_uid = None
        if session_uid is not None:
            uid(session_uid)
            selected = value["sessions"].get(session_uid)
            if selected is None:
                raise ValueError("session UID is not registered")
            if action == "detail":
                detail_uid = session_uid
                session_uid = None
                full = True
            elif not same_worktree(selected["worktree"], str(worktree)):
                raise ValueError("session belongs to a different worktree")
        elif action == "detail":
            raise ValueError("detail requires a session UID")
        summary = summarize(value, str(worktree), policy, datetime.now(timezone.utc), session_uid=session_uid, full=full)
        if detail_uid is not None:
            summary["omitted_sessions"] = len(summary["sessions"]) - 1
            summary["sessions"] = [entry for entry in summary["sessions"] if entry["session_uid"] == detail_uid]
        return {"enabled": True, "registry": str(hub / "sessions.json"), **summary}
    if action == "register":
        session_uid = str(uuid.uuid4())
        created = now_text()
        entry = {"session_uid": session_uid, "parent_uid": parent_uid,
                 "worktree": str(worktree), "task": task, "scope": scope,
                 "activity": activity if activity is not None else "inspecting", "started_at": created, "updated_at": created, "version": 1}
        validate_entry(entry)
        for reference in entry["scope"]:
            scope_reference(reference)
    else:
        uid(session_uid)
        if type(expected_version) is not int or expected_version < 1:
            raise ValueError("update/leave require a positive expected_version")
    with registry_lock(hub):
        value = load_registry(hub, repository_id)
        sessions = value["sessions"]
        if action == "register":
            if len(sessions) >= MAX_SESSIONS or session_uid in sessions:
                raise ValueError("presence registry is at capacity or UID collides")
            sessions[session_uid] = entry
        else:
            previous = sessions.get(session_uid)
            if previous is None:
                raise ValueError("session UID is not registered")
            if not same_worktree(previous["worktree"], str(worktree)):
                raise ValueError("session belongs to a different worktree")
            if previous["version"] != expected_version:
                raise ValueError("session version changed; reread presence before retrying")
            if action == "leave":
                del sessions[session_uid]
            else:
                updated = now_text()
                if timestamp(updated, "updated_at") < timestamp(previous["updated_at"], "updated_at"):
                    raise ValueError("clock moved backwards; presence update refused")
                entry = {**previous, "task": task, "scope": scope, "activity": activity if activity is not None else previous["activity"],
                         "updated_at": updated, "version": expected_version + 1}
                validate_entry(entry)
                for reference in entry["scope"]:
                    scope_reference(reference)
                sessions[session_uid] = entry
        save_registry(hub, value, repository_id)
        summary = summarize(value, str(worktree), policy, datetime.now(timezone.utc),
                            session_uid=session_uid, scope=entry["scope"] if action != "leave" else previous["scope"])
    return {"enabled": True, "action": action, "session_uid": session_uid,
            "version": None if action == "leave" else entry["version"], "registry": str(hub / "sessions.json"), **summary}
