#!/usr/bin/env python3
"""Inspect or explicitly reconcile source-only self-adoption, never install Alatyr."""

from __future__ import annotations

import argparse
import json

from source_adoption import (ROOT, MARKER, MAX_BYTES, assert_current, assert_source_root,
    desired_runtime, parse_knowledge, parse_source_policy, policy_inputs, reconcile, sha, source_object, validate_knowledge_owner)
from request_values import request_path, strings, text
from support_write_transaction import SupportTransaction, read_output, support_writer_lock
from target_validation_support import GitEvidenceView


def knowledge(root, query: str) -> dict:
    text(query, "source knowledge query", 160)
    _, policy = source_object(root, "tools/source_adoption.json")
    parse_source_policy(policy)
    _, catalog = source_object(root, policy["knowledge_catalog"])
    parse_knowledge(catalog)
    matches = {key: row for key, row in catalog["items"].items()
               if query.casefold() in " ".join([key, *row["aliases"]]).casefold()}
    owners = {}
    for key, row in matches.items():
        if row["owner"] not in owners:
            owners[row["owner"]] = read_output(root, root / row["owner"], max_bytes=MAX_BYTES)
        validate_knowledge_owner(key, row, owners[row["owner"]])
    return {"query": query, "matches": matches, "authority": "referenced owners, not this index"}


def bridge(root, surface: str, *, write: bool) -> dict:
    assert_source_root(root)
    _, catalog = source_object(root, "conformance/runs/assistant-surfaces.json")
    values = catalog.get("surfaces")
    if not isinstance(values, list) or not 1 <= len(values) <= 32:
        raise ValueError("assistant surface catalog requires 1..32 records")
    ids = []
    for row in values:
        if not isinstance(row, dict):
            raise ValueError("assistant surface record requires an object")
        ids.append(text(row.get("id"), "assistant surface ID"))
        text(row.get("support_status"), "assistant support status")
        strings(row.get("bridge_paths"), "assistant bridge paths", minimum=1)
        for path in row["bridge_paths"]:
            request_path(path)
    if len(set(ids)) != len(ids):
        raise ValueError("assistant surface IDs must be unique")
    selected = next((row for row in values if row["id"] == surface), None)
    if selected is None:
        raise ValueError("unknown canonical assistant surface: " + surface)
    outputs, existing, previews = {}, {}, {}
    git = GitEvidenceView(root)
    for path in selected["bridge_paths"]:
        if path in {"AGENTS.md", "AI_ASSISTANTS.md"}:
            continue
        content = ("# AlatyrCore Source Entry\n\nRead the repository-root AGENTS.md first.\n"
            "Choose the smallest profile via tools/source-context/index.json.\n"
            "For material source work, follow docs/source-self-application.md.\n"
            "Do not activate an installed target or nested dependency adapter here.\n")
        if path.endswith(".mdc"):
            content = "---\ndescription: AlatyrCore source entry\nalwaysApply: true\n---\n\n" + content
        elif path.startswith(".github/prompts/"):
            content = "---\ndescription: Review selected AlatyrCore source gates\n---\n\n" + content
        previews[path] = content
        if write:
            if git.is_ignored(path) is not True or git.is_tracked(path) is not False:
                raise ValueError("source bridge output must already be ignored and untracked: " + path)
            prior = read_output(root, root / path, max_bytes=MAX_BYTES)
            if prior is not None and prior != content.encode():
                raise ValueError("preserve existing assistant instructions: " + path)
            existing[root / path] = prior
            outputs[root / path] = content.encode()
    if write and outputs:
        with support_writer_lock(root):
            transaction = SupportTransaction(root)
            try:
                transaction.apply(outputs, expected_inputs=existing)
            except Exception:
                transaction.rollback()
                raise
    return {"surface": surface, "support_status": selected["support_status"], "write": write,
        "canonical_entries": [path for path in selected["bridge_paths"] if path not in previews],
        "previews": previews, "native_interception_verified": False, "client_loading_verified": False}


def status(root) -> dict:
    policy, inputs = policy_inputs(root)
    raw = read_output(root, root / MARKER, max_bytes=MAX_BYTES)
    runtime, diagnostic, strategies = "not-projected", None, "not-projected"
    if raw is not None:
        try:
            assert_current(root)
            runtime = "current-policy-projection"
            expected, _ = desired_runtime(root)
            drift = [path for path, raw in expected.items() if read_output(root, root / path, max_bytes=MAX_BYTES) != raw]
            strategies = "reconciliation-required" if drift else "current"
            if drift:
                runtime, diagnostic = "reconciliation-required", "source projection drift: " + ", ".join(drift)
        except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
            runtime, diagnostic = "reconciliation-required", str(exc)
    return {"scope": "source-repository", "runtime": runtime, "diagnostic": diagnostic,
        "modules": policy["modules"], "module_exercise": "not-established-by-configuration", "strategy_projection": strategies,
        "policy_sha256": sha(inputs["tools/source_adoption.json"]),
        "measurements": {"provider_billing": None, "provider_tokens": None, "native_client_exercise": None},
        "authorization_granted": False, "acceptance_granted": False, "guide": policy["guide"]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("status", allow_abbrev=False)
    projection = commands.add_parser("reconcile", allow_abbrev=False)
    projection.add_argument("--write", action="store_true")
    projection.add_argument("--approve-policy-update", action="store_true")
    lookup = commands.add_parser("knowledge", allow_abbrev=False)
    lookup.add_argument("--query", required=True)
    entry = commands.add_parser("bridge", allow_abbrev=False)
    entry.add_argument("--surface", required=True)
    entry.add_argument("--write", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.action == "status":
            result = status(ROOT)
        elif args.action == "reconcile":
            result = reconcile(ROOT, write=args.write, approve_policy_update=args.approve_policy_update)
        elif args.action == "knowledge":
            result = knowledge(ROOT, args.query)
        else:
            result = bridge(ROOT, args.surface, write=args.write)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, UnicodeError, ValueError, RuntimeError, RecursionError) as exc:
        print(json.dumps({"status": "unavailable", "reason": str(exc), "authorization_granted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
