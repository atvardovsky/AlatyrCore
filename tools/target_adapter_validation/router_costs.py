"""Budget and measured-cost checks for an installed context router."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Protocol

from target_validation_support import is_placeholder


SOURCE = ".ai/assistant/context-router.json"


class FindingSink(Protocol):
    allow_placeholders: bool

    def error(self, code: str, message: str, path: str | None = None) -> None: ...

    def warn(self, code: str, message: str, path: str | None = None) -> None: ...

    def info(self, code: str, message: str, path: str | None = None) -> None: ...

    def target_path(self, relpath: str) -> Path: ...

    def read_text(self, path: Path) -> str: ...


def validate_budget_shape(sink: FindingSink, budgets: dict[str, Any]) -> None:
    bootstrap = budgets.get("bootstrap")
    profile = budgets.get("profile_default")
    if not isinstance(bootstrap, dict):
        sink.error("ROUTER_BUDGET_BOOTSTRAP", "bootstrap budget must be an object", SOURCE)
        bootstrap = {}
    if not isinstance(profile, dict):
        sink.error(
            "ROUTER_BUDGET_PROFILE", "profile_default budget must be an object", SOURCE
        )
        profile = {}

    for field in ["max_files", "max_words", "soft_max_words"]:
        value = bootstrap.get(field)
        if not isinstance(value, int) or value <= 0:
            sink.error(
                "ROUTER_BUDGET_VALUE",
                f"context_budgets.bootstrap.{field} must be a positive integer",
                SOURCE,
            )
    soft = bootstrap.get("soft_max_words")
    hard = bootstrap.get("max_words")
    if isinstance(soft, int) and isinstance(hard, int) and soft >= hard:
        sink.error(
            "ROUTER_BUDGET_ORDER",
            "bootstrap soft_max_words must be below max_words",
            SOURCE,
        )

    for field in [
        "max_files",
        "max_total_words",
        "max_portable_words",
        "reserved_target_words",
    ]:
        value = profile.get(field)
        if not isinstance(value, int) or value <= 0:
            sink.error(
                "ROUTER_BUDGET_VALUE",
                f"context_budgets.profile_default.{field} must be a positive integer",
                SOURCE,
            )
    total = profile.get("max_total_words")
    portable = profile.get("max_portable_words")
    reserved = profile.get("reserved_target_words")
    if all(isinstance(value, int) for value in [total, portable, reserved]):
        if portable + reserved > total:
            sink.error(
                "ROUTER_BUDGET_ORDER",
                "max_portable_words plus reserved_target_words exceeds max_total_words",
                SOURCE,
            )
    if not isinstance(budgets.get("on_exceed"), str) or not budgets["on_exceed"]:
        sink.error(
            "ROUTER_BUDGET_ON_EXCEED",
            "context_budgets.on_exceed must describe safe expansion evidence",
            SOURCE,
        )


def validate_installed_costs(
    sink: FindingSink,
    router: dict[str, Any],
    profiles: dict[str, Any],
    budgets: dict[str, Any],
) -> None:
    bootstrap_budget = budgets.get("bootstrap", {})
    profile_budget = budgets.get("profile_default", {})

    def measure(references: list[str], label: str) -> tuple[int, int, int, int]:
        words = 0
        portable_words = 0
        target_words = 0
        concrete_files = 0
        for reference in dict.fromkeys(references):
            if is_placeholder(reference):
                report = sink.warn if sink.allow_placeholders else sink.error
                report(
                    "ROUTER_CONTEXT_COST_UNRESOLVED",
                    f"{label} cannot measure unresolved context {reference}",
                    SOURCE,
                )
                continue
            candidate = Path(reference)
            if candidate.is_absolute() or ".." in candidate.parts:
                sink.error(
                    "ROUTER_CONTEXT_PATH_UNSAFE",
                    f"{label} contains unsafe context path {reference}",
                    SOURCE,
                )
                continue
            path = sink.target_path(reference)
            if not path.is_file():
                sink.warn(
                    "ROUTER_CONTEXT_PATH_MISSING",
                    f"{label} cannot measure missing context {reference}",
                    SOURCE,
                )
                continue
            text = sink.read_text(path)
            if not text and path.stat().st_size:
                sink.warn(
                    "ROUTER_CONTEXT_COST_UNREADABLE",
                    f"{label} cannot read {reference}",
                    SOURCE,
                )
                continue
            count = len(re.findall(r"\S+", text))
            concrete_files += 1
            words += count
            if reference.startswith(".ai/framework/"):
                portable_words += count
            else:
                target_words += count
        return concrete_files, words, portable_words, target_words

    bootstrap_refs = [
        *router.get("preloaded_context", []),
        *router.get("bootstrap_context", []),
    ]
    bootstrap_files, bootstrap_words, _, _ = measure(bootstrap_refs, "bootstrap")
    max_bootstrap_files = bootstrap_budget.get("max_files")
    max_bootstrap_words = bootstrap_budget.get("max_words")
    if isinstance(max_bootstrap_files, int) and bootstrap_files > max_bootstrap_files:
        sink.error("ROUTER_BOOTSTRAP_COST", "bootstrap exceeds max_files", SOURCE)
    if isinstance(max_bootstrap_words, int) and bootstrap_words > max_bootstrap_words:
        sink.error("ROUTER_BOOTSTRAP_COST", "bootstrap exceeds max_words", SOURCE)

    profile_index = router.get("profile_index", {})
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        entry = profile_index.get(name, {}) if isinstance(profile_index, dict) else {}
        descriptor = entry.get("descriptor") if isinstance(entry, dict) else None
        references = [
            value
            for value in [descriptor, *profile.get("required_context", [])]
            if isinstance(value, str) and value
        ]
        files, total_words, portable_words, target_words = measure(
            references, f"profile {name}"
        )
        max_files = profile_budget.get("max_files")
        max_total = profile_budget.get("max_total_words")
        max_portable = profile_budget.get("max_portable_words")
        if isinstance(max_files, int) and len(dict.fromkeys(references)) > max_files:
            sink.error(
                "ROUTER_PROFILE_COST",
                f"profile {name} declares more than {max_files} context files",
                SOURCE,
            )
        if isinstance(max_total, int) and total_words > max_total:
            sink.error(
                "ROUTER_PROFILE_COST",
                f"profile {name} measures {total_words} words above max_total_words {max_total}",
                SOURCE,
            )
        if isinstance(max_portable, int) and portable_words > max_portable:
            sink.error(
                "ROUTER_PROFILE_COST",
                f"profile {name} measures {portable_words} portable words above {max_portable}",
                SOURCE,
            )
        sink.info(
            "ROUTER_PROFILE_COST_MEASURED",
            f"profile {name} measures total={total_words} portable={portable_words} "
            f"target={target_words} words",
            SOURCE,
        )
        if files == 0 and references:
            sink.warn(
                "ROUTER_PROFILE_COST_EMPTY",
                f"profile {name} has no measurable context files",
                SOURCE,
            )
