#!/usr/bin/env python3
"""Validate current-scope action authorization source contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "templates" / "target"
POLICY = TARGET / ".ai" / "assistant" / "policies" / "action-authorization.json"
SCENARIOS = ROOT / "conformance" / "authorization-intent-scenarios.json"

PHASES = ["inspect", "modify", "commit", "publish", "live-external"]
PHASE_EFFECT_KEYS = set(PHASES)
EXPECTED_SCENARIOS = {
    "backlog-return-is-read-only": ["inspect"],
    "issue-status-is-read-only": ["inspect"],
    "fix-authorizes-working-tree-only": ["inspect", "modify"],
    "commit-existing-does-not-authorize-edit-or-push": ["inspect", "commit"],
    "stage-existing-is-local-git-only": ["inspect", "commit"],
    "pull-authorizes-working-tree-and-local-git": ["inspect", "modify", "commit"],
    "push-existing-does-not-authorize-edit-or-commit": ["inspect", "publish"],
    "combined-request-authorizes-named-phases": [
        "inspect",
        "modify",
        "commit",
        "publish",
    ],
    "commit-and-push-existing-does-not-authorize-edit": [
        "inspect",
        "commit",
        "publish",
    ],
    "issue-comment-is-publication-only": ["inspect", "publish"],
    "continue-unfinished-inherits-explicit-phases": ["inspect", "modify"],
    "continue-after-completion-is-read-only": ["inspect"],
    "protected-approval-does-not-grant-publish": ["inspect", "modify"],
    "subagent-inherits-no-publish": ["inspect", "modify"],
    "deployment-is-separate": ["inspect", "live-external"],
}

REQUIRED_TEXT = {
    ROOT / "framework" / "action-authorization.md": [
        "Authorization belongs to one current logical scope.",
        "implementation intent does not authorize commit or publish",
        "commit intent does not authorize publish",
        "backlog return as implementation authorization",
        "current_user_authorization",
    ],
    TARGET / "AGENTS.md": [
        "ALATYR-AUTHORIZATION-001",
        "Implementation does not imply commit; commit does not imply push",
        ".ai/assistant/policies/action-authorization.json",
    ],
    TARGET / "AI_ASSISTANTS.md": [
        ".ai/assistant/policies/action-authorization.json",
        "backlog/issue return",
        "commit does not imply push",
    ],
    TARGET / ".ai" / "assistant" / "flows" / "operation-routing.flow.md": [
        "backlog returns",
        "Prior completed-scope authorization is invalid.",
        "Before every `modify`, `commit`, `publish`, or `live-external` phase",
    ],
    TARGET / ".ai" / "assistant" / "gates" / "core.md": [
        "ALATYR-AUTHORIZATION-001",
        "Issue/backlog returns",
        "Do not infer commit from implementation, publish from commit",
    ],
    TARGET / ".ai" / "assistant" / "gates" / "final-evidence.md": [
        "`current_user_authorization`",
        "latest commit/publish/live confirmation",
    ],
    TARGET / ".ai" / "assistant" / "contour.md": [
        ".ai/assistant/policies/action-authorization.json",
        "current-scope action authorization",
    ],
    TARGET / ".ai" / "assistant" / "module-profile.md": [
        "current-scope-action-authorization",
        ".ai/assistant/policies/action-authorization.json",
    ],
    TARGET / ".ai" / "assistant" / "maturity-profile.md": [
        ".ai/assistant/policies/action-authorization.json",
        "Prior authorization",
    ],
    TARGET / ".ai" / "assistant" / "templates" / "installation-note.md": [
        ".ai/assistant/policies/action-authorization.json",
        "previous task's authorization expires",
    ],
    TARGET / ".ai" / "assistant" / "templates" / "operation-request.md": [
        "Current logical scope:",
        "Current user authorization:",
        "Authorization source/message:",
        "Prior authorization invalidated:",
    ],
    TARGET / ".ai" / "assistant" / "templates" / "pre-change-preview.md": [
        "It is also not action authorization.",
        "Next phase authorized:",
    ],
    TARGET / ".ai" / "assistant" / "templates" / "post-install-message.md": [
        ".ai/assistant/policies/action-authorization.json",
        "Implementation intent does not authorize commit",
    ],
    TARGET / ".ai" / "assistant" / "templates" / "post-update-message.md": [
        ".ai/assistant/policies/action-authorization.json",
        "Issue/backlog returns",
    ],
    ROOT / "installer" / "installed-operation-request-template.md": [
        "Current logical scope:",
        "Current user authorization:",
        "Implementation does not imply commit;",
        "does not imply push",
    ],
    ROOT / "installer" / "readiness-checklist.md": [
        "current-scope action authorization",
        "action-authorization policy",
    ],
    ROOT / "installer" / "installation-plan-template.md": [
        "Current-scope action authorization policy",
        "Current user authorization",
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssertionError(f"missing {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain an object")
    return data


def string_list(value: Any, label: str, failures: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        failures.append(f"{label} must be a string list")
        return []
    return value


def main() -> int:
    failures: list[str] = []
    try:
        policy = load_json(POLICY)
        scenarios = load_json(SCENARIOS)
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if policy.get("schema_version") != 1:
        failures.append("action authorization policy schema_version must be 1")
    if policy.get("policy_kind") != "target-action-authorization-policy":
        failures.append("action authorization policy kind is invalid")
    if policy.get("canonical_rule") != "ALATYR-AUTHORIZATION-001":
        failures.append("action authorization policy canonical rule is invalid")
    if policy.get("phases") != PHASES:
        failures.append(f"action authorization phases must be {PHASES}")
    phase_effects = policy.get("phase_effects")
    if not isinstance(phase_effects, dict) or set(phase_effects) != PHASE_EFFECT_KEYS:
        failures.append("action authorization phase effects must cover every phase")
    elif not all(isinstance(value, str) and value for value in phase_effects.values()):
        failures.append("action authorization phase effects must be non-empty strings")
    if policy.get("default_phase") != "inspect":
        failures.append("ambiguous action authorization must default to inspect")

    scope = policy.get("scope")
    if not isinstance(scope, dict):
        failures.append("action authorization policy scope must be an object")
    else:
        if scope.get("prior_authorization_reusable") is not False:
            failures.append("prior scope authorization must not be reusable")
        invalidations = string_list(
            scope.get("invalidate_on"), "scope.invalidate_on", failures
        )
        for required in [
            "operation completed",
            "new logical scope",
            "user redirection",
            "material changed-fact or surface expansion",
        ]:
            if required not in invalidations:
                failures.append(f"scope invalidation missing {required}")

    separation = policy.get("separation")
    expected_separation = {
        "allowed_actions": "ceiling-not-grant",
        "protected_change_approval": "additional-gate-not-grant",
        "tool_permission": "capability-not-grant",
        "operation_routing": "process-selection-not-grant",
        "team_assignment": "coordination-not-grant",
        "project_decision": "fact-authority-not-grant",
        "workspace_mode": "context-selection-not-grant",
        "delegation": "inherited-boundary-not-grant",
        "validation_result": "evidence-not-grant",
    }
    if separation != expected_separation:
        failures.append("authorization separation contract is incomplete or changed")

    phase_rules = policy.get("phase_rules")
    if not isinstance(phase_rules, dict):
        failures.append("phase_rules must be an object")
    else:
        if phase_rules.get("publish_requires_explicit_current_scope_intent") is not True:
            failures.append("publish must require explicit current-scope intent")
        if phase_rules.get("live_external_requires_explicit_current_scope_intent") is not True:
            failures.append("live external work must require explicit current-scope intent")
        if phase_rules.get("commit_does_not_grant") != [
            "modify",
            "publish",
            "live-external",
        ]:
            failures.append("commit phase must not grant modify, publish, or live-external")

    delegation = policy.get("delegation")
    if not isinstance(delegation, dict) or delegation.get("may_broaden_phases") is not False:
        failures.append("delegation must not broaden authorized phases")
    if policy.get("final_evidence_field") != "current_user_authorization":
        failures.append("authorization final evidence field is invalid")

    if scenarios.get("schema_version") != 1:
        failures.append("authorization scenarios schema_version must be 1")
    if scenarios.get("canonical_rule") != "ALATYR-AUTHORIZATION-001":
        failures.append("authorization scenarios canonical rule is invalid")
    scenario_items = scenarios.get("scenarios")
    actual_scenarios: dict[str, list[str]] = {}
    if not isinstance(scenario_items, list):
        failures.append("authorization scenarios must be a list")
    else:
        for index, scenario in enumerate(scenario_items):
            if not isinstance(scenario, dict):
                failures.append(f"scenarios[{index}] must be an object")
                continue
            scenario_id = scenario.get("id")
            if not isinstance(scenario_id, str) or not scenario_id:
                failures.append(f"scenarios[{index}] missing id")
                continue
            if scenario_id in actual_scenarios:
                failures.append(f"duplicate authorization scenario {scenario_id}")
            phases = string_list(
                scenario.get("authorized_phases"),
                f"scenarios[{index}].authorized_phases",
                failures,
            )
            unknown = sorted(set(phases) - set(PHASES))
            if unknown:
                failures.append(f"scenario {scenario_id} uses unknown phases {unknown}")
            actual_scenarios[scenario_id] = phases
    if actual_scenarios != EXPECTED_SCENARIOS:
        failures.append("authorization scenario expectations differ from the canonical set")

    catalog = load_json(TARGET / ".ai" / "assistant" / "operation-catalog.json")
    if catalog.get("action_authorization_policy") != (
        ".ai/assistant/policies/action-authorization.json"
    ):
        failures.append("operation catalog does not route action authorization policy")
    if catalog.get("authorization_phases") != PHASES:
        failures.append("operation catalog authorization phases differ from policy")
    if catalog.get("required_final_evidence") != ["current_user_authorization"]:
        failures.append("operation catalog must require current user authorization evidence")

    manifest = (TARGET / ".ai" / "alatyr.yaml").read_text(encoding="utf-8")
    if (
        'action_authorization_policy: ".ai/assistant/policies/action-authorization.json"'
        not in manifest
    ):
        failures.append("target manifest does not route action authorization policy")

    for path, snippets in REQUIRED_TEXT.items():
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            failures.append(f"missing authorization surface {path.relative_to(ROOT)}")
            continue
        for snippet in snippets:
            if snippet not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {snippet}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print(
        "OK: checked current-scope authorization policy and "
        f"{len(actual_scenarios)} intent scenarios"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
