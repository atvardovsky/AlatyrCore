#!/usr/bin/env python3
"""Check source contract drift against an explicit change or release baseline."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
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
    "templates/target/.ai/assistant/context/consistency-routing.json",
    "templates/target/.ai/assistant/context/cost-scenarios.json",
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
    "templates/target/.ai/project/consistency-map.json",
}
CONTRACT_VERSION_FILES = ("VERSION", "ADAPTER_SCHEMA_VERSION", "TEMPLATE_VERSION")
RELEASE_BASELINE_DIR = ROOT / "docs" / "releases" / "baselines"


@dataclass(frozen=True)
class ReleaseBaseline:
    ref: str
    label: str
    version: str
    kind: str
    expected_digest: str | None = None


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


def _safe_archive_path(destination: Path, name: str, *, root: Path | None = None) -> Path:
    member_path = Path(name)
    if member_path.is_absolute() or ".." in member_path.parts:
        raise RuntimeError(f"unsafe archive member path: {name}")
    output = (destination / member_path).resolve()
    try:
        output.relative_to(root or destination.resolve())
    except ValueError as exc:
        raise RuntimeError(f"unsafe archive member path: {name}") from exc
    return output


def materialize(ref: str, prefix: str, destination: Path) -> None:
    result = git("archive", "--format=tar", ref, prefix, text=False)
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(error or f"cannot archive {ref}:{prefix}")
    root = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:*") as archive:
        for member in archive:
            output = _safe_archive_path(destination, member.name, root=root)
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            output.parent.mkdir(parents=True, exist_ok=True)
            if member.issym() or member.islnk():
                output.write_bytes(member.linkname.encode("utf-8"))
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                continue
            output.write_bytes(extracted.read())


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
        "To manifest: `source-tree:framework/rule-registry.json`",
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


def release_checkpoint(version: str) -> ReleaseBaseline | None:
    path = RELEASE_BASELINE_DIR / f"{version}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid release checkpoint {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"release checkpoint {path.relative_to(ROOT)} must be an object")
    required = {
        "schema_version": 1,
        "baseline_kind": "source-release-checkpoint",
        "framework_version": version,
        "publication_status": "untagged-release-checkpoint",
        "migration_report": f"docs/releases/{version}-migration.md",
    }
    for field, expected in required.items():
        if data.get(field) != expected:
            raise RuntimeError(
                f"release checkpoint {path.relative_to(ROOT)} requires "
                f"{field}={expected!r}"
            )
    commit = data.get("source_commit")
    digest = data.get("contract_sha256")
    adapter = data.get("adapter_schema_version")
    template = data.get("template_version")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise RuntimeError(f"release checkpoint {path.relative_to(ROOT)} has invalid source_commit")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RuntimeError(f"release checkpoint {path.relative_to(ROOT)} has invalid contract_sha256")
    if not isinstance(adapter, str) or not adapter.isdigit():
        raise RuntimeError(f"release checkpoint {path.relative_to(ROOT)} has invalid adapter schema version")
    if not isinstance(template, str) or not template.isdigit():
        raise RuntimeError(f"release checkpoint {path.relative_to(ROOT)} has invalid template version")
    require_git_text("rev-parse", "--verify", f"{commit}^{{commit}}")
    ancestry = git("merge-base", "--is-ancestor", commit, "HEAD")
    if ancestry.returncode != 0:
        raise RuntimeError(
            f"release checkpoint {path.relative_to(ROOT)} source_commit is not an ancestor of HEAD"
        )
    committed_values = {
        "framework_version": read_at(commit, "VERSION"),
        "adapter_schema_version": read_at(commit, "ADAPTER_SCHEMA_VERSION"),
        "template_version": read_at(commit, "TEMPLATE_VERSION"),
    }
    for field, actual in committed_values.items():
        if data.get(field) != actual:
            raise RuntimeError(
                f"release checkpoint {path.relative_to(ROOT)} {field} differs from source_commit"
            )
    report_path = ROOT / data["migration_report"]
    if not report_path.is_file():
        raise RuntimeError(
            f"release checkpoint {path.relative_to(ROOT)} migration report is missing"
        )
    report = report_path.read_text(encoding="utf-8")
    report_bindings = [
        f"To framework version: `{version}`",
        f"To adapter schema version: `{adapter}`",
        f"To template version: `{template}`",
        f"To contract SHA-256: `{digest}`",
    ]
    missing = [item for item in report_bindings if item not in report]
    if missing:
        raise RuntimeError(
            f"release checkpoint {path.relative_to(ROOT)} migration report lacks "
            + ", ".join(missing)
        )
    return ReleaseBaseline(
        ref=commit,
        label=f"release-checkpoint:{version}",
        version=version,
        kind="checkpoint",
        expected_digest=digest,
    )


def nearest_release_baseline(current_version: str) -> tuple[ReleaseBaseline, list[str]]:
    prior_versions = prior_changelog_versions(current_version)
    for index, version in enumerate(prior_versions):
        tag = f"v{version}"
        result = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
        if result.returncode == 0:
            baseline = ReleaseBaseline(tag, tag, version, "tag")
        else:
            baseline = release_checkpoint(version)
            if baseline is None:
                continue
        intervening = prior_versions[:index]
        missing_reports = [
            item
            for item in intervening
            if not (ROOT / "docs" / "releases" / f"{item}-migration.md").is_file()
        ]
        if missing_reports:
            raise RuntimeError(
                "release history has versions without migration evidence: "
                + ", ".join(missing_reports)
            )
        return baseline, intervening
    raise RuntimeError(
        "release mode requires a reachable prior release tag or reviewed source "
        "release checkpoint; fetch history or repair the release baseline"
    )


def resolve_baseline(mode: str, from_ref: str | None) -> ReleaseBaseline:
    if mode == "change":
        if not from_ref:
            raise RuntimeError("change mode requires --from-ref")
        require_git_text("rev-parse", "--verify", f"{from_ref}^{{commit}}")
        return ReleaseBaseline(from_ref, from_ref, "change-base", "explicit")

    current_version = read_current("VERSION")
    baseline, _intervening = nearest_release_baseline(current_version)
    if from_ref and from_ref not in {baseline.ref, baseline.label}:
        raise RuntimeError(
            f"release mode baseline must be the nearest reviewed prior release "
            f"baseline {baseline.label}, "
            f"not {from_ref}"
        )
    return baseline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare source contracts with an explicit change or release baseline."
    )
    parser.add_argument(
        "--mode",
        choices=["change", "release"],
        required=True,
        help="Use an explicit Git base ref for changes or a reviewed prior release baseline.",
    )
    parser.add_argument(
        "--from-ref",
        help="Required in change mode; optional tag, checkpoint label, or commit assertion in release mode.",
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
        paths = changed_paths(baseline.ref)
        framework_changed = any(
            path.startswith("framework/") or path.startswith("schemas/")
            for path in paths
        )
        templates_changed = any(path.startswith("templates/target/") for path in paths)
        schema_changed = bool(paths & SCHEMA_CONTRACT_PATHS)

        from_version = read_at(baseline.ref, "VERSION")
        from_adapter = read_at(baseline.ref, "ADAPTER_SCHEMA_VERSION")
        from_template = read_at(baseline.ref, "TEMPLATE_VERSION")
        to_version = read_current("VERSION")
        to_adapter = read_current("ADAPTER_SCHEMA_VERSION")
        to_template = read_current("TEMPLATE_VERSION")

        if framework_changed and to_version == from_version:
            failures.append(
                f"framework changed since {baseline.label} but VERSION remains {to_version}"
            )
        if schema_changed and int(to_adapter) <= int(from_adapter):
            failures.append(
                f"adapter schema contracts changed since {baseline.label} but "
                f"ADAPTER_SCHEMA_VERSION did not increase above {from_adapter}"
            )
        if templates_changed and int(to_template) <= int(from_template):
            failures.append(
                f"target templates changed since {baseline.label} but TEMPLATE_VERSION "
                f"did not increase above {from_template}"
            )

        with tempfile.TemporaryDirectory(prefix="alatyr-release-baseline-") as directory:
            previous = Path(directory)
            materialize(baseline.ref, "framework", previous)
            materialize(baseline.ref, "schemas", previous)
            materialize(baseline.ref, "templates/target", previous)
            for filename in CONTRACT_VERSION_FILES:
                output = previous / filename
                output.write_text(read_at(baseline.ref, filename) + "\n", encoding="utf-8")
            from_digest = contract_digest(previous)
            if baseline.expected_digest and from_digest != baseline.expected_digest:
                failures.append(
                    f"{baseline.label} contract digest differs from its reviewed checkpoint"
                )
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
                "--from-source-label",
                baseline.label,
                "--to-source-label",
                "source-tree",
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
                            baseline=baseline.label,
                            from_version=from_version,
                            to_version=to_version,
                            from_adapter=from_adapter,
                            to_adapter=to_adapter,
                            from_template=from_template,
                            to_template=to_template,
                            from_digest=from_digest,
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
        f"OK: {args.mode} drift against {baseline.label}; framework_changed={framework_changed} "
        f"schema_changed={schema_changed} templates_changed={templates_changed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
