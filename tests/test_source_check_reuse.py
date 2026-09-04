from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from source_check_reuse import (  # noqa: E402
    REUSE_CONTRACT,
    RUN_IDENTITY_CONTRACT,
    SourceSnapshotIndex,
    canonical_digest,
    check_input_fingerprint,
    environment_fingerprint,
    reuse_decisions,
)
from source_state import SourceEntry  # noqa: E402


def check() -> dict[str, object]:
    return {
        "id": "example",
        "command": ["tools/example.py"],
        "contract_inputs": ["docs/example.md"],
        "implementation_paths": ["tools/example.py"],
    }


def run_identity(
    *,
    requested_profile: str = "full",
    effective_profile: str = "full",
    ref_oid: str = "base-oid",
    snapshot_sha256: str = "snapshot",
) -> dict[str, object]:
    return {
        "contract": RUN_IDENTITY_CONTRACT,
        "requested_profile": requested_profile,
        "effective_profile": effective_profile,
        "platform": "linux",
        "jobs": 4,
        "selected_check_ids": ["example"],
        "changed_paths": ["docs/example.md"],
        "unmatched_changed_paths": [],
        "fell_back_to_full": False,
        "escalated_from_micro": requested_profile != effective_profile,
        "micro_escalation_reasons": (
            ["path requires non-micro checks"] if requested_profile != effective_profile else []
        ),
        "check_scope": [
            {
                "id": "example",
                "selection_reasons": ["changed-path-trigger"],
                "matched_changed_paths": ["docs/example.md"],
            }
        ],
        "changed_from": {"name": "main", "commit_oid": ref_oid},
        "baseline": {"name": "main", "commit_oid": ref_oid},
        "source_commit": "head-oid",
        "source_snapshot_sha256": snapshot_sha256,
        "manifest_sha256": "manifest",
    }


def environment(*, pyyaml: str = "6.0.2") -> dict[str, object]:
    return {
        "platform": "linux",
        "platform_detail": "Linux-test",
        "python": "3.13.2 build",
        "python_executable": "/usr/bin/python3",
        "dependencies": {"jsonschema": "4.25.1", "PyYAML": pyyaml},
    }


def source() -> dict[str, object]:
    return {"manifest_sha256": "manifest"}


def fingerprint() -> dict[str, object]:
    return check_input_fingerprint(
        check(),
        {
            "docs/example.md": SourceEntry("file", 0o644, "aaa"),
            "tools/example.py": SourceEntry("file", 0o644, "bbb"),
        },
    )


def reusable_report(
    *,
    identity: dict[str, object] | None = None,
    runtime: dict[str, object] | None = None,
    status: str = "passed",
    timed_out: bool = False,
    provenance_kind: str = "executed",
    completed: bool = True,
    successful: bool = True,
    write_scope_preserved: bool = True,
) -> dict[str, object]:
    identity = identity or run_identity()
    runtime = runtime or environment()
    identity_digest = canonical_digest(identity)
    return {
        "schema_version": 3,
        "report_kind": "alatyr-source-check-run",
        "source": source(),
        "environment": runtime,
        "reuse_contract": {
            "contract": REUSE_CONTRACT,
            "completed": completed,
            "successful": successful,
            "run_identity": identity,
            "run_identity_sha256": identity_digest,
            "environment_sha256": environment_fingerprint(runtime)["sha256"],
        },
        "source_write_scope": {
            "declared": "none",
            "preserved": write_scope_preserved,
            "changes": [] if write_scope_preserved else ["modified tools/example.py"],
        },
        "checks": [
            {
                "id": "example",
                "status": status,
                "timed_out": timed_out,
                "command": [sys.executable, "tools/example.py"],
                "input_fingerprint": fingerprint(),
                "result_provenance": {
                    "kind": provenance_kind,
                    "run_identity_sha256": identity_digest,
                },
            }
        ],
    }


def decision(
    report: dict[str, object],
    *,
    identity: dict[str, object] | None = None,
    runtime: dict[str, object] | None = None,
) -> dict[str, object]:
    item = check()
    current_fingerprint = fingerprint()
    return reuse_decisions(
        selected=[item],
        previous_report=report,
        current_source=source(),
        current_environment=runtime or environment(),
        input_fingerprints={"example": current_fingerprint},
        commands_by_id={"example": [sys.executable, "tools/example.py"]},
        current_run_identity=identity or run_identity(),
    )["example"]


class SourceCheckReuseTests(unittest.TestCase):
    def test_input_fingerprint_changes_with_declared_content(self) -> None:
        first = {
            "docs/example.md": SourceEntry("file", 0o644, "aaa"),
            "tools/example.py": SourceEntry("file", 0o644, "bbb"),
            "unrelated.txt": SourceEntry("file", 0o644, "ccc"),
        }
        second = {
            **first,
            "docs/example.md": SourceEntry("file", 0o644, "changed"),
        }

        self.assertNotEqual(
            check_input_fingerprint(check(), first)["sha256"],
            check_input_fingerprint(check(), second)["sha256"],
        )

    def test_snapshot_index_is_immutable_and_reuses_pattern_matches(self) -> None:
        snapshot = {
            "docs/example.md": SourceEntry("file", 0o644, "aaa"),
            "tools/example.py": SourceEntry("file", 0o644, "bbb"),
        }
        index = SourceSnapshotIndex(snapshot)
        first = check_input_fingerprint(check(), index)
        snapshot["docs/example.md"] = SourceEntry("file", 0o644, "changed")
        second = check_input_fingerprint(check(), index)

        self.assertEqual(first, second)
        self.assertEqual(
            set(index._pattern_matches),  # pylint: disable=protected-access
            {"docs/example.md", "tools/example.py"},
        )

    def test_symlink_input_is_not_reuse_eligible(self) -> None:
        item = check()
        current_fingerprint = check_input_fingerprint(
            item,
            {
                "docs/example.md": SourceEntry("symlink", 0o777, "target"),
                "tools/example.py": SourceEntry("file", 0o644, "bbb"),
            },
        )
        decisions = reuse_decisions(
            selected=[item],
            previous_report=reusable_report(),
            current_source=source(),
            current_environment=environment(),
            input_fingerprints={"example": current_fingerprint},
            commands_by_id={"example": [sys.executable, "tools/example.py"]},
            current_run_identity=run_identity(),
        )

        self.assertFalse(decisions["example"]["reusable"])
        self.assertEqual(
            decisions["example"]["reason"],
            "current check inputs include unsupported non-file paths",
        )

    def test_matching_executed_result_is_reusable(self) -> None:
        result = decision(reusable_report())

        self.assertTrue(result["reusable"])

    def test_legacy_report_is_timing_only(self) -> None:
        report = reusable_report()
        report.pop("reuse_contract")

        result = decision(report)

        self.assertFalse(result["reusable"])
        self.assertIn("timing-only", result["reason"])

    def test_fast_result_cannot_satisfy_full_or_different_effective_profile(self) -> None:
        fast_identity = run_identity(
            requested_profile="fast", effective_profile="fast"
        )
        report = reusable_report(identity=fast_identity)

        self.assertFalse(decision(report, identity=run_identity())["reusable"])

        escalated = run_identity(
            requested_profile="micro", effective_profile="fast"
        )
        report = reusable_report(identity=escalated)
        different_effective = run_identity(
            requested_profile="micro", effective_profile="micro"
        )
        self.assertFalse(
            decision(report, identity=different_effective)["reusable"]
        )

    def test_moved_ref_oid_invalidates_reuse(self) -> None:
        report = reusable_report(identity=run_identity(ref_oid="old-oid"))

        result = decision(report, identity=run_identity(ref_oid="new-oid"))

        self.assertFalse(result["reusable"])
        self.assertIn("resolved ref identity", result["reason"])

    def test_source_snapshot_change_invalidates_reuse(self) -> None:
        report = reusable_report(
            identity=run_identity(snapshot_sha256="old-snapshot")
        )

        result = decision(
            report,
            identity=run_identity(snapshot_sha256="new-snapshot"),
        )

        self.assertFalse(result["reusable"])
        self.assertIn("execution scope", result["reason"])

    def test_dependency_change_invalidates_reuse(self) -> None:
        report = reusable_report(runtime=environment(pyyaml="6.0.1"))

        result = decision(report, runtime=environment(pyyaml="6.0.2"))

        self.assertFalse(result["reusable"])
        self.assertEqual(result["reason"], "execution environment changed")

    def test_environment_digest_must_match_report_evidence(self) -> None:
        report = reusable_report()
        report["environment"] = environment(pyyaml="modified")

        result = decision(report)

        self.assertFalse(result["reusable"])
        self.assertEqual(
            result["reason"],
            "previous execution environment evidence is inconsistent",
        )

    def test_write_scope_violation_invalidates_whole_report(self) -> None:
        report = reusable_report(write_scope_preserved=False)

        result = decision(report)

        self.assertFalse(result["reusable"])
        self.assertEqual(
            result["reason"], "previous run did not preserve source write scope"
        )

    def test_incomplete_or_unsuccessful_report_is_not_reusable(self) -> None:
        incomplete = decision(reusable_report(completed=False))
        blocked = decision(
            reusable_report(status="blocked", successful=False)
        )

        self.assertEqual(incomplete["reason"], "previous run was incomplete")
        self.assertEqual(blocked["reason"], "previous run was not successful")

        malformed = reusable_report()
        malformed["checks"] = []
        self.assertEqual(
            decision(malformed)["reason"],
            "previous run completion evidence is invalid",
        )

    def test_timed_out_result_is_not_reusable(self) -> None:
        result = decision(reusable_report(timed_out=True))

        self.assertFalse(result["reusable"])
        self.assertEqual(result["reason"], "previous run was not successful")

    def test_reused_result_cannot_be_chained(self) -> None:
        report = reusable_report(status="reused-pass", provenance_kind="reused")

        result = decision(report)

        self.assertFalse(result["reusable"])
        self.assertEqual(
            result["reason"], "previous check was not an executed pass"
        )


if __name__ == "__main__":
    unittest.main()
