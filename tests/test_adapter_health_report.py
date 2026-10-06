from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_adapter_health import build_capability_advisory, render_text  # noqa: E402
from validate_target_adapter import Finding, findings_payload  # noqa: E402


class AdapterHealthReportTests(unittest.TestCase):
    def test_capability_comparison_finds_missing_and_unknown_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            for base, modules in [
                (source / "framework", {"installed": {}, "runtime-observation": {}}),
                (target / ".ai/framework", {"installed": {}}),
            ]:
                base.mkdir(parents=True)
                (base / "capabilities.json").write_text(
                    json.dumps(
                        {
                            "schema_version": 1,
                            "capability_kind": "alatyr-optional-module-catalog",
                            "surfaces": {},
                            "modules": {
                                key: {
                                    "module_kind": "governance-support",
                                    "min_framework_pack": "core",
                                    "requires": [],
                                }
                                for key in modules
                            },
                        }
                    ),
                    encoding="utf-8",
                )
            advisory = build_capability_advisory(
                target=target,
                framework_source=source,
                required_capabilities=["runtime-observation", "not-real"],
            )
        self.assertEqual(advisory["missing_from_installation"], ["runtime-observation"])
        self.assertEqual(advisory["unknown_to_source"], ["not-real"])
        self.assertTrue(advisory["blocking"])

    def test_capability_advisory_is_visible(self) -> None:
        payload = {
            "adapter_health": {"state": "attention", "repair_operations": []},
            "health_layers": {},
            "evidence": {},
            "counts": {},
            "placeholder_validation": {},
            "findings": [],
            "capability_advisory": {
                "missing_from_installation": ["runtime-observation"],
                "unknown_to_source": [],
                "available_in_source": ["runtime-observation"],
            },
        }
        text = render_text(payload)
        self.assertIn(
            "Required capabilities missing from installation: runtime-observation",
            text,
        )
        self.assertIn(
            "Capabilities available after assessment/update: runtime-observation",
            text,
        )

    def test_changed_scope_never_produces_acceptance_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
                validation_scope="changed",
            )

        self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])
        self.assertEqual(payload["adapter_health"]["state"], "unverified")
        self.assertEqual(
            payload["health_layers"]["current_change"]["state"], "not-evaluated"
        )
        self.assertIn(
            "repository worktree evidence is unavailable",
            payload["placeholder_validation"]["acceptance_blockers"],
        )

    def test_partial_archive_mode_never_produces_acceptance_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
                approval_archive_summary={"mode": "changed"},
            )

        self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])

    def test_staging_health_is_unverified_and_not_acceptance_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                validation_phase="migration-staging",
                installation_state="staged",
            )

        text = render_text(payload)

        self.assertIn("Alatyr adapter health: unverified", text)
        self.assertIn("Installation state: staged", text)
        self.assertIn(
            "Health layers: installation=staged support=unverified "
            "current_change=not-evaluated",
            text,
        )
        self.assertIn("Acceptance eligible: no", text)
        self.assertIn("Observed revision: unavailable", text)
        self.assertNotIn("None", text)
        self.assertIn("Repair operations: none", text)

    def test_blocking_findings_are_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [Finding("error", "MANIFEST_SCHEMA", "invalid manifest", ".ai/alatyr.yaml")],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        text = render_text(payload)

        self.assertIn("Alatyr adapter health: blocked", text)
        self.assertIn("Blocking findings:", text)
        self.assertIn("MANIFEST_SCHEMA: invalid manifest [.ai/alatyr.yaml]", text)
        self.assertEqual(payload["health_layers"]["installation"]["state"], "degraded")

    def test_stale_support_does_not_change_accepted_installation_layer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [
                    Finding(
                        "error",
                        "SUPPORT_STATE_STALE",
                        "support state differs",
                        ".ai/support-state.json",
                    )
                ],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        self.assertEqual(payload["health_layers"]["installation"]["state"], "accepted")
        self.assertEqual(payload["health_layers"]["support"]["state"], "blocked")
        self.assertEqual(
            payload["health_layers"]["current_change"]["state"], "not-evaluated"
        )

    def test_missing_required_contract_blocks_support_layer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [
                    Finding(
                        "error",
                        "REQUIRED_FILE_MISSING",
                        "required adapter file is missing",
                        ".ai/assistant/validation-contract.json",
                    )
                ],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        self.assertEqual(payload["health_layers"]["installation"]["state"], "accepted")
        self.assertEqual(payload["health_layers"]["support"]["state"], "blocked")

    def test_selected_change_evidence_is_reported_separately(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
                diff_ref="HEAD~1",
                approval_records_selected=1,
                change_packages_selected=1,
                approval_scope_enforced=True,
                change_package_enforced=True,
            )

        current = payload["health_layers"]["current_change"]
        self.assertEqual(current["state"], "partial")
        self.assertFalse(current["semantic_correctness_proven"])
        self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])

    def test_dirty_change_requires_diff_approval_and_package_enforcement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=target, check=True)
            subprocess.run(
                ["git", "config", "user.email", "fixture@example.invalid"],
                cwd=target,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Fixture"], cwd=target, check=True
            )
            (target / "tracked.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=target, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=target, check=True)
            (target / "tracked.txt").write_text("after\n", encoding="utf-8")

            payload = findings_payload(
                [],
                target=target,
                strict_warnings=False,
                installation_state="accepted",
            )

        self.assertFalse(payload["placeholder_validation"]["acceptance_eligible"])
        self.assertEqual(payload["evidence"]["worktree_state"], "dirty")
        self.assertIn(
            "current change has no Git diff reference",
            payload["placeholder_validation"]["acceptance_blockers"],
        )

    def test_status_mode_omits_detailed_repair_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            payload = findings_payload(
                [Finding("error", "MANIFEST_SCHEMA", "invalid manifest", ".ai/alatyr.yaml")],
                target=Path(directory),
                strict_warnings=False,
                installation_state="accepted",
            )

        text = render_text(payload, mode="status")

        self.assertIn("Alatyr adapter health: blocked", text)
        self.assertIn("Repair operations: run doctor for prioritized repair routes", text)
        self.assertIn("Finding details: run doctor for prioritized findings", text)
        self.assertNotIn("Blocking findings:", text)


if __name__ == "__main__":
    unittest.main()
