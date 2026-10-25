#!/usr/bin/env python3
"""Plan resource-safe test concurrency without running any selected command."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from resource_access import command_resource_plan, presence_resource_scopes
from test_execution_contract import TestExecutionContract, policy_projection_failures
from target_adapter_validation.context import TargetRepositoryView


def resolved_test_policy(view: TargetRepositoryView) -> dict:
    result = view.read_json_result(view.target / ".ai/project/testing/test-first-policy.json")
    if result.error:
        raise ValueError(result.error)
    failures = TestExecutionContract().policy_failures(result.value)
    if failures:
        raise ValueError("; ".join(failures))
    canonical = view.read_json_result(view.target / result.value["execution_contract"]["canonical_policy"])
    if canonical.error:
        raise ValueError(canonical.error)
    failures = policy_projection_failures(result.value, canonical.value)
    if failures:
        raise ValueError("; ".join(failures))
    return result.value


def resource_plan(target: Path, command_ids: list[str]) -> dict:
    view = TargetRepositoryView(target.resolve())
    policy = resolved_test_policy(view)
    plan = command_resource_plan(policy, command_ids)
    resources = [resource for command in policy["commands"] if command["id"] in command_ids
                 for resource in command["execution"]["resources"]]
    plan["presence_scope_refs"] = sorted({scope for resource in resources
                                         for scope in presence_resource_scopes([resource])})
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--command", action="append", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(resource_plan(args.target, args.command), indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
