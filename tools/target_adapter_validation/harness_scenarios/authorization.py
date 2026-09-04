"""Target-validator scenarios for authorization."""

from __future__ import annotations

from .common import (
    ROOT,
    json,
    validator,
    write_json,
)


def run(target: Path, failures: list[str]) -> None:
    policy_source = (
        ROOT
        / "templates"
        / "target"
        / ".ai"
        / "assistant"
        / "policies"
        / "action-authorization.json"
    )
    authorization_policy = json.loads(policy_source.read_text(encoding="utf-8"))
    write_json(
        target / ".ai/assistant/policies/action-authorization.json",
        authorization_policy,
    )
    authorization_surfaces = {
        "AGENTS.md": (
            "ALATYR-AUTHORIZATION-001\n"
            "Implementation does not imply commit; commit does not imply push\n"
        ),
        ".ai/assistant/gates/core.md": (
            "Issue/backlog returns\n"
            "Do not infer commit from implementation, publish from commit\n"
        ),
        ".ai/assistant/gates/final-evidence.md": (
            "`current_user_authorization`\n"
            "latest commit/publish/live confirmation\n"
        ),
        ".ai/assistant/contour.md": (
            ".ai/assistant/policies/action-authorization.json\n"
            "current-scope action authorization\n"
        ),
        ".ai/assistant/module-profile.md": (
            "current-scope-action-authorization\n"
            ".ai/assistant/policies/action-authorization.json\n"
        ),
        ".ai/assistant/maturity-profile.md": (
            ".ai/assistant/policies/action-authorization.json\n"
            "Prior authorization\n"
        ),
        ".ai/assistant/templates/installation-note.md": (
            ".ai/assistant/policies/action-authorization.json\n"
            "previous task's authorization expires\n"
        ),
        ".ai/assistant/templates/operation-request.md": (
            "Current logical scope:\n"
            "Current user authorization:\n"
            "Authorization source/message:\n"
            "Prior authorization invalidated:\n"
        ),
    }
    for relpath, content in authorization_surfaces.items():
        surface = target / relpath
        surface.parent.mkdir(parents=True, exist_ok=True)
        surface.write_text(content, encoding="utf-8")
    authorization = validator(target)
    authorization.check_action_authorization_contract()
    if any(
        finding.code.startswith("AUTHORIZATION_")
        for finding in authorization.findings
    ):
        failures.append("valid action authorization contract should pass")

    authorization_policy["scope"]["prior_authorization_reusable"] = True
    write_json(
        target / ".ai/assistant/policies/action-authorization.json",
        authorization_policy,
    )
    reusable = validator(target)
    reusable.check_action_authorization_contract()
    if "AUTHORIZATION_SCOPE_REUSE" not in {
        finding.code for finding in reusable.findings
    }:
        failures.append("reusable prior authorization must be rejected")
    authorization_policy["scope"]["prior_authorization_reusable"] = False
    write_json(
        target / ".ai/assistant/policies/action-authorization.json",
        authorization_policy,
    )
