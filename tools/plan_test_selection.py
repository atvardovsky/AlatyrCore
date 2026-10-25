#!/usr/bin/env python3
"""Reconcile an exact test request with captured discovery; run no tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from test_selection import observed_selection, read_selection_json
from plan_test_resources import resolved_test_policy
from target_adapter_validation.context import TargetRepositoryView


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--observations", required=True)
    args = parser.parse_args()
    try:
        view = TargetRepositoryView(args.target.resolve())
        policy = resolved_test_policy(view)
        command = next((item for item in policy["commands"] if item["id"] == args.command), None)
        if command is None:
            raise ValueError("select a command from the canonical target testing policy")
        request = read_selection_json(view, args.request)
        observations = read_selection_json(view, args.observations)
        result = observed_selection(view, request, observations, command_id=args.command)
        result["control_adoption"] = command["execution"].get("selection_contract", "not-required")
        result["policy_sha256"] = view.content_digest(view.target / policy["execution_contract"]["canonical_policy"])
        if view.finalize():
            raise ValueError("selection inputs changed during preflight")
        print(json.dumps(result, indent=2))
        return 1 if result["failures"] else 0
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"state": "unavailable", "error": str(exc), "execution_performed": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
