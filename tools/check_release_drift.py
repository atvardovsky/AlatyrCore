#!/usr/bin/env python3
"""Check source contract drift against an explicit change or release baseline."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from report_migration_diff import contract_surface_digest
except ModuleNotFoundError:  # Support package-style imports in source tests.
    from tools.report_migration_diff import contract_surface_digest


ROOT = Path(__file__).resolve().parents[1]
REPORTER = ROOT / "tools" / "report_migration_diff.py"
SHIPPED_SCHEMA_PATHS = {
    path.relative_to(ROOT).as_posix()
    for path in (ROOT / "schemas").rglob("*.json")
}
SCHEMA_CONTRACT_PATHS = SHIPPED_SCHEMA_PATHS | {
    "framework/capabilities.json",
    "templates/target/.ai/alatyr.yaml",
    "templates/target/.ai/assistant/module-profile.md",
    "templates/target/.ai/assistant/context-router.json",
    "templates/target/.ai/assistant/operation-catalog.json",
    "templates/target/.ai/assistant/operation-index.json",
    "templates/target/.ai/assistant/assistant-capabilities.json",
    "templates/target/.ai/assistant/approvals/approval-record-template.json",
    "templates/target/.ai/assistant/team/context-overlay.json",
    "templates/target/.ai/assistant/team/work-registry.json",
    "templates/target/.ai/assistant/team/active-work-index.json",
    "templates/target/.ai/assistant/team/backend-contract.json",
    "templates/target/.ai/assistant/team/task-record-template.json",
    "templates/target/.ai/project/team-policy.json",
}
CONTRACT_VERSION_FILES = ("VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION")


def git(
    *args: str, text: bool = True
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=text,
    )


def require_git_text(*args: str) -> str:
    result = git(*args)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(error or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def read_current(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").strip()


def read_at(ref: str, path: str) -> str:
    return require_git_text("show", f"{ref}:{path}")


def changed_paths(ref: str) -> set[str]:
    tracked = set(
        filter(
            None,
            require_git_text(
                "diff", "--name-only", ref, "--", "framework", "schemas", "templates/target"
            ).splitlines(),
        )
    )
    untracked = set(
        filter(
            None,
            require_git_text(
                "ls-files",
                "--others",
                "--exclude-standard",
                "--",
                "framework",
                "schemas",
                "templates/target",
            ).splitlines(),
        )
    )
    return tracked | untracked


def materialize(ref: str, prefix: str, destination: Path) -> None:
    (destination / prefix).mkdir(parents=True, exist_ok=True)
    paths = require_git_text("ls-tree", "-r", "--name-only", ref, "--", prefix)
    for relpath in filter(None, paths.splitlines()):
        result = git("show", f"{ref}:{relpath}", text=False)
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(error or f"cannot read {ref}:{relpath}")
        output = destination / relpath
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(result.stdout)


def contract_digest(root: Path) -> str:
    versions = [
        (root / filename).read_text(encoding="utf-8").strip()
        for filename in CONTRACT_VERSION_FILES
    ]
    return contract_surface_digest(
        root / "framework",
        root / "schemas",
        root / "templates" / "target",
        versions[0],
        versions[1],
        versions[2],
    )


def validate_committed_report(
    *,
    baseline: str,
    from_version: str,
    to_version: str,
    from_adapter: str,
    to_adapter: str,
    from_template: str,
    to_template: str,
    from_digest: str,
    to_digest: str,
) -> list[str]:
    report_path = ROOT / "docs" / "releases" / f"{to_version}-migration.md"
    if not report_path.is_file():
        return [f"missing committed migration report: {report_path.relative_to(ROOT)}"]
    text = report_path.read_text(encoding="utf-8")
    required = [
        f"From manifest: `{baseline}:framework/rule-registry.json`",
        "To manifest: `framework/rule-registry.json`",
        f"From framework version: `{from_version}`",
        f"To framework version: `{to_version}`",
        f"From adapter schema version: `{from_adapter}`",
        f"To adapter schema version: `{to_adapter}`",
        f"From template version: `{from_template}`",
        f"To template version: `{to_template}`",
        f"From contract SHA-256: `{from_digest}`",
        f"To contract SHA-256: `{to_digest}`",
    ]
    return [
        f"{report_path.relative_to(ROOT)} missing release binding {item}"
        for item in required
        if item not in text
    ]


def report_has_changes(report: str) -> bool:
    counts = [
        int(value)
        for value in re.findall(
            r"^- (?:Added|Changed|Removed) "
            r"(?:rules|rule owner categories|framework files|schema contracts|target template surfaces): "
            r"(\d+)$",
            report,
            flags=re.MULTILINE,
        )
    ]
    return bool(counts) and any(counts)


def prior_changelog_versions(current_version: str) -> list[str]:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    versions = re.findall(
        r"^## (?!Unreleased\b)v?([^\s]+)(?: - \d{4}-\d{2}-\d{2})?$",
        changelog,
        flags=re.MULTILINE,
    )
    try:
        current_index = versions.index(current_version)
    except ValueError as exc:
        raise RuntimeError(
            f"CHANGELOG.md has no release section for VERSION={current_version}"
        ) from exc
    if current_index + 1 >= len(versions):
        raise RuntimeError(f"VERSION={current_version} has no prior changelog release")
    return versions[current_index + 1 :]


def nearest_tagged_baseline(current_version: str) -> tuple[str, list[str]]:
    prior_versions = prior_changelog_versions(current_version)
    for index, version in enumerate(prior_versions):
        tag = f"v{version}"
        result = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
        if result.returncode != 0:
            continue
        intervening = prior_versions[:index]
        missing_reports = [
            item
            for item in intervening
            if not (ROOT / "docs" / "releases" / f"{item}-migration.md").is_file()
        ]
        if missing_reports:
            raise RuntimeError(
                "release history has untagged versions without migration evidence: "
                + ", ".join(missing_reports)
            )
        return tag, intervening
    raise RuntimeError(
        "release mode requires at least one reachable prior changelog release tag; "
        "fetch complete tag history or repair the release baseline"
    )


def resolve_baseline(mode: str, from_ref: str | None) -> str:
    if mode == "change":
        if not from_ref:
            raise RuntimeError("change mode requires --from-ref")
        require_git_text("rev-parse", "--verify", f"{from_ref}^{{commit}}")
        return from_ref

    current_version = read_current("VERSION")
    expected_tag, _intervening = nearest_tagged_baseline(current_version)
    if from_ref and from_ref != expected_tag:
        raise RuntimeError(
            f"release mode baseline must be the nearest reachable prior release "
            f"tag {expected_tag}, "
            f"not {from_ref}"
        )
    return expected_tag


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare source contracts with an explicit change or release baseline."
    )
    parser.add_argument(
        "--mode",
        choices=["change", "release"],
        required=True,
        help="Use an explicit Git base ref for changes or the prior version tag for release.",
    )
    parser.add_argument(
        "--from-ref",
        help="Required in change mode; optional prior release tag assertion in release mode.",
    )
    parser.add_argument("--report-output", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    baseline = "unknown"
    framework_changed = False
    schema_changed = False
    templates_changed = False
    try:
        baseline = resolve_baseline(args.mode, args.from_ref)
        paths = changed_paths(baseline)
        framework_changed = any(
            path.startswith("framework/") or path.startswith("schemas/")
            for path in paths
        )
        templates_changed = any(path.startswith("templates/target/") for path in paths)
        schema_changed = bool(paths & SCHEMA_CONTRACT_PATHS)

        from_version = read_at(baseline, "VERSION")
        from_adapter = read_at(baseline, "ADAPTER_SCHEMA_VERSION")
        from_template = read_at(baseline, "TEMPLATE_VERSION")
        to_version = read_current("VERSION")
        to_adapter = read_current("ADAPTER_SCHEMA_VERSION")
        to_template = read_current("TEMPLATE_VERSION")

        if framework_changed and to_version == from_version:
            failures.append(
                f"framework changed since {baseline} but VERSION remains {to_version}"
            )
        if schema_changed and int(to_adapter) <= int(from_adapter):
            failures.append(
                f"adapter schema contracts changed since {baseline} but "
                f"ADAPTER_SCHEMA_VERSION did not increase above {from_adapter}"
            )
        if templates_changed and int(to_template) <= int(from_template):
            failures.append(
                f"target templates changed since {baseline} but TEMPLATE_VERSION "
                f"did not increase above {from_template}"
            )

        with tempfile.TemporaryDirectory(prefix="alatyr-release-baseline-") as directory:
            previous = Path(directory)
            materialize(baseline, "framework", previous)
            materialize(baseline, "schemas", previous)
            materialize(baseline, "templates/target", previous)
            for filename in CONTRACT_VERSION_FILES:
                output = previous / filename
                output.write_text(read_at(baseline, filename) + "\n", encoding="utf-8")
            command = [
                sys.executable,
                str(REPORTER),
                "--from-rules",
                str(previous / "framework" / "rule-registry.json"),
                "--to-rules",
                str(ROOT / "framework" / "rule-registry.json"),
                "--from-version",
                from_version,
                "--to-version",
                to_version,
                "--from-adapter-schema-version",
                from_adapter,
                "--to-adapter-schema-version",
                to_adapter,
                "--from-template-version",
                from_template,
                "--to-template-version",
                to_template,
                "--from-framework-dir",
                str(previous / "framework"),
                "--to-framework-dir",
                str(ROOT / "framework"),
                "--from-schema-dir",
                str(previous / "schemas"),
                "--to-schema-dir",
                str(ROOT / "schemas"),
                "--from-template-dir",
                str(previous / "templates" / "target"),
                "--to-template-dir",
                str(ROOT / "templates" / "target"),
            ]
            result = subprocess.run(
                command, cwd=ROOT, check=False, capture_output=True, text=True
            )
            if result.returncode != 0:
                failures.append(result.stderr.strip() or "migration reporter failed")
                report = ""
            else:
                report = result.stdout
                if paths and not report_has_changes(report):
                    failures.append(
                        "migration report declared no contract changes against a changed release baseline"
                    )
                if args.mode == "release":
                    failures.extend(
                        validate_committed_report(
                            baseline=baseline,
                            from_version=from_version,
                            to_version=to_version,
                            from_adapter=from_adapter,
                            to_adapter=to_adapter,
                            from_template=from_template,
                            to_template=to_template,
                            from_digest=contract_digest(previous),
                            to_digest=contract_digest(ROOT),
                        )
                    )
                if args.report_output:
                    output = args.report_output.resolve()
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(report, encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as exc:
        failures.append(str(exc))

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print(
        f"OK: {args.mode} drift against {baseline}; framework_changed={framework_changed} "
        f"schema_changed={schema_changed} templates_changed={templates_changed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
