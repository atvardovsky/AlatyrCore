"""Read-only, capability-selected hook setup plans; never client installation."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from lifecycle_checkpoints import EVENTS, NATIVE_EVENTS, ROOT, decision
from lifecycle_policy import POLICY, PROVIDERS, identifier, load_policy
from request_brief import request_path
from support_write_transaction import safe_output


INTERPRETERS = ("python", "python3", "py")


def setup_plan(target: Path, provider: str, installation_kind: str, *,
               native_setup_approved: bool = False, client_version: str | None = None,
               config_path: str | None = None, interpreter: str = "python") -> dict:
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ValueError("select an exact supported native route or procedural fallback")
    if installation_kind not in ("new", "update") or type(native_setup_approved) is not bool:
        raise ValueError("setup requires new/update identity and Boolean native approval")
    if interpreter not in INTERPRETERS:
        raise ValueError("select python, python3 or py as the reviewed interpreter")
    if client_version is not None:
        identifier(client_version, "client_version")
        if client_version.casefold() in {"unknown", "unverified", "none"} or "{" in client_version:
            raise ValueError("native client version must be resolved")
    if config_path is not None:
        request_path(config_path)
        if config_path == ".git" or config_path.startswith(".git/"):
            raise ValueError("native configuration must be a project-local client file, not Git internals")
        safe_output(target, target / config_path)
    if native_setup_approved and (provider == "procedural" or client_version is None or config_path is None):
        raise ValueError("native setup approval requires an exact native route, client version and project-local configuration path")

    raw, existing = load_policy(target)
    result = decision("setup-plan", "Review the plan and actual installation scope; no configuration was written.")
    result.update(installation_kind=installation_kind, selected_provider=provider,
        policy_path=POLICY, policy_action="none", policy_candidate=None,
        existing_policy_sha256=hashlib.sha256(raw).hexdigest() if raw is not None else None,
        setup_disposition="adoption-decision-required", callbacks=[],
        configuration_path=config_path, client_version=client_version,
        native_hook_status="not-established", configuration_write_performed=False,
        approval_provenance="caller-declaration-not-authenticated",
        required_actions=[], procedural_events=[],
        enforcement_status={"policy_enabled": existing["enabled"] if existing else False,
            "policy_origin": "existing" if existing else "absent",
            "provider": existing["provider"] if existing else "procedural",
            "mode": existing["mode"] if existing else "not-configured",
            "recorded_native_evidence": existing["native_evidence"]["state"] if existing else "unverified",
            "native_interception_verified": False},
        limitations=["A policy or plan does not prove client installation, trust, loading or interception.",
                     "No plugins, global settings, automatic continuation, commits or pushes are performed."])
    if existing is not None:
        result.update(policy_action="preserve", policy_candidate=existing,
            setup_disposition="existing-policy-preserved",
            required_actions=["Retain policy bytes, native definitions and trust choices; use an explicitly scoped adoption change for new setup."])
        if not existing["enabled"]:
            result["required_actions"].append("Delivery is disabled: preserve the opt-out and report that no pre-action interception is established.")
        return result
    if installation_kind == "update":
        result["required_actions"] = ["Retain the absent policy; a fresh-install default is not upgrade adoption consent."]
        return result

    _, template = load_policy(ROOT / "templates/target")
    if (template is None or template["enabled"] is not True or template["provider"] != "procedural"
            or template["mode"] != "observe" or template["max_reminders"] != 0
            or template["native_evidence"]["state"] != "unverified"):
        raise ValueError("source hook default must be enabled procedural observe-only, unverified and reminder-free")
    candidate = copy.deepcopy(template)
    result["enforcement_status"].update(policy_enabled=True, policy_origin="proposed", mode="observe")
    result.update(policy_action="create", policy_candidate=candidate,
        setup_disposition="procedural-fallback",
        required_actions=["Include this project policy in the approved installation scope; keep ordinary procedural checkpoints."])
    if not native_setup_approved:
        if provider != "procedural":
            result["required_actions"].append("Include exact project-local native setup in installation approval before selecting its provider.")
        return result

    candidate["provider"] = provider
    result["enforcement_status"]["provider"] = provider
    result.update(setup_disposition="native-setup-proposed",
        required_actions=["Confirm this exact client/runtime route is supported; merge only the approved project-local hook configuration, preserving existing definitions.",
                          "Respect native trust prompts; verify interpreter, delegate locator, Git-root working directory and ignored runtime storage.",
                          "Select only verified mutating tools for pre-action/post-change callbacks; never intercept helper review commands or all reads.",
                          "Exercise request, selected mutation, compaction, completion, interruption and callback error/timeout behavior in the actual client.",
                          "Keep observe mode and zero reminders. Consider checkpoint mode only after explicit adoption and fresh exact-client evidence."])
    for event, normalized in NATIVE_EVENTS[provider].items():
        result["callbacks"].append({"event": event, "checkpoint": normalized,
            "selection": "verified-mutating-tools-only" if normalized in {"before-action", "after-change"} else "session-event",
            "argv": [interpreter, ".ai/assistant/tools/alatyr_delegate.py", "lifecycle-checkpoint",
                     "--target", ".", "--provider", provider, "event", "--event", event, "--native-output"]})
    covered = set(NATIVE_EVENTS[provider].values())
    result["procedural_events"] = sorted(EVENTS - covered)
    return result
