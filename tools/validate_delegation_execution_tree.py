#!/usr/bin/env python3
"""Validate one resolved target delegation execution tree and its artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from delegation_evidence import (
    DelegationEvidenceError,
    load_json_object,
    validate_execution_tree,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Validate measured recursive delegation evidence without changing files."
    )
    result.add_argument("--target-root", type=Path, required=True)
    result.add_argument("--tree", type=Path, required=True)
    result.add_argument("--policy", type=Path)
    result.add_argument("--artifact-root", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    target_root = args.target_root.resolve()
    policy_path = args.policy or target_root / ".ai/assistant/delegation-policy.json"
    artifact_root = (args.artifact_root or target_root).resolve()
    try:
        policy = load_json_object(policy_path, "delegation policy")
        tree = load_json_object(args.tree, "delegation execution tree")
        validate_execution_tree(tree, policy, artifact_root=artifact_root)
    except DelegationEvidenceError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "OK: delegation execution tree, recursive envelopes, measured results, "
        "summary load, and convergence are consistent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
