"""Freeze and compare an exact local commit request without contacting a hook."""

from __future__ import annotations

import hashlib
from pathlib import Path

from path_spec import logical_path
from project_evidence import ProjectEvidence
from publication_preflight import _git

MAX_PATCH_BYTES = 8 * 1024 * 1024
FIELDS = {"argv", "message_sha256", "staged_patch_sha256", "paths", "worktree", "branch", "base_revision", "validation_report"}


def _patch(target: Path) -> bytes:
    return _git(target, "diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv",
                "--no-color", "--no-renames", "HEAD", "--", max_output=MAX_PATCH_BYTES)


def packet(target: Path, message: str, previous: str | None = None, validation: str | None = None) -> dict:
    target = target.resolve()
    message = logical_path(message)
    root = Path(_git(target, "rev-parse", "--show-toplevel").decode("utf-8").rstrip("\r\n")).resolve()
    if root != target:
        raise ValueError("commit request requires the exact worktree root")
    branch = _git(target, "symbolic-ref", "--short", "HEAD").decode("utf-8").strip()
    revision = _git(target, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    raw = _patch(target)
    paths = _git(target, "diff", "--cached", "--name-only", "--no-renames", "-z", "HEAD", "--")
    if not raw or not paths:
        raise ValueError("no staged changes to review")
    if _git(target, "ls-files", "--unmerged", "-z"):
        raise ValueError("unmerged paths prevent a frozen commit request")
    with ProjectEvidence(target) as evidence:
        data = evidence.read(target / message, max_bytes=32 * 1024)
        if not data.decode("utf-8").strip() or b"\0" in data:
            raise ValueError("commit message must be nonempty UTF-8 text")
        observation = None
        if validation is not None:
            observed = evidence.object(validation)
            facts = observed.get("evidence")
            counts = observed.get("counts")
            if (not isinstance(facts, dict) or not isinstance(counts, dict)
                    or type(counts.get("errors")) is not int or counts["errors"] < 0
                    or observed.get("status") not in ("passed", "failed")):
                raise ValueError("validation observation requires a structured acceptance or staging report")
            observation = {"path": validation, "sha256": evidence.inputs[target / validation],
                           "reported_status": observed["status"], "errors": counts["errors"],
                           "observed_base_matches": facts.get("observed_revision") == revision,
                           "staged_patch_qualified": False}
        binding = {"argv": ["git", "commit", "-F", "./" + message],
                   "message_sha256": hashlib.sha256(data).hexdigest(),
                   "staged_patch_sha256": hashlib.sha256(raw).hexdigest(),
                   "paths": sorted(p.decode("utf-8") for p in paths.split(b"\0") if p),
                   "branch": branch, "base_revision": revision, "worktree": str(target),
                   "validation_report": observation}
        changed = []
        if previous is not None:
            earlier = evidence.object(previous)
            old = earlier.get("binding")
            if earlier.get("report_kind") != "alatyr-local-commit-review" or not isinstance(old, dict) or set(old) != FIELDS:
                raise ValueError("previous packet does not have the exact local-commit binding")
            changed = sorted(key for key in FIELDS if binding[key] != old[key])
        if (_patch(target) != raw or _git(target, "rev-parse", "--verify", "HEAD").decode("ascii").strip() != revision
                or _git(target, "symbolic-ref", "--short", "HEAD").decode("utf-8").strip() != branch):
            raise ValueError("staged changes or worktree revision changed during inspection")
    return {"schema_version": 1, "report_kind": "alatyr-local-commit-review",
            "state": "awaiting-client-admission", "binding": binding, "changed_bindings": changed,
            "prior_admission_reusable": False, "qualification_granted": False,
            "authorization_granted": False, "commit_performed": False,
            "limitation": "Review input only. Current user authorization, qualification and fresh independent client admission remain separate."}
