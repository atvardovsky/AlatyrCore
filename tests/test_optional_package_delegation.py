from __future__ import annotations

import contextlib
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from composition_model import CompositionRequest, resolve_composition  # noqa: E402
from target_adapter_validation.harness_scenarios.common import parse_manifest, validator  # noqa: E402
from target_adapter_validation.current_change import change_packages_enabled  # noqa: E402
from target_adapter_validation.validation_contract import (  # noqa: E402
    CONTRACT_PATH,
    DELEGATE_PATH,
    validate_validation_contract,
)


delegate = runpy.run_path(str(ROOT / "templates/target" / DELEGATE_PATH))
PACKAGE_REQUIREMENTS = {"PACKAGE_INDEX_REQUIRED", "PACKAGE_SELECTION_REQUIRED"}


class OptionalPackageDelegationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name)
        self.manifest = self.target / ".ai/alatyr.yaml"
        self.manifest.parent.mkdir()
        framework = self.target / ".ai/framework"
        framework.mkdir()
        shutil.copyfile(ROOT / "framework/capabilities.json", framework / "capabilities.json")

    def arguments(self, *extra: str):
        with contextlib.redirect_stderr(io.StringIO()):
            return delegate["build_parser"]().parse_args([
                "validate-current", "--target", str(self.target),
                "--diff-ref", "HEAD", "--approval-record", "approval.json", *extra,
            ])

    def set_module(
        self, state: str | None, *, enabled: bool = False, support_profile: str = "core"
    ) -> None:
        selection = "[change-packages]" if state is not None or enabled else "[]"
        self.manifest.write_text(
            f"installation:\n  support_profile: {support_profile}\n"
            f"modules:\n  selected: {selection}\n  staged: []\n"
            f"  enabled: {'[change-packages]' if enabled else '[]'}\n",
            encoding="utf-8",
        )
        profile = self.target / ".ai/assistant/module-profile.md"
        if state is not None:
            profile.parent.mkdir(parents=True, exist_ok=True)
            profile.write_text(
                f"Module: `change-packages`\nState: `{state}`\n", encoding="utf-8"
            )
        else:
            profile.unlink(missing_ok=True)

    def check_current(self, packages: list[Path] | None = None):
        checked = validator(self.target, validation_phase="acceptance")
        checked.diff_ref = "HEAD"
        checked.change_packages = [self.target / path for path in packages or []]
        checked.run()
        errors = {finding.code for finding in checked.findings if finding.level == "error"}
        return checked, errors

    def test_parser_omits_optional_package_but_keeps_actual_required_options(self) -> None:
        self.assertEqual(self.arguments().change_package, [])
        for omitted in ("--diff-ref", "--approval-record"):
            arguments = ["validate-current", "--diff-ref", "HEAD", "--approval-record", "approval.json"]
            position = arguments.index(omitted)
            del arguments[position:position + 2]
            with self.subTest(omitted=omitted), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    delegate["build_parser"]().parse_args(arguments)

    def test_forwarding_leaves_optional_policy_to_canonical_validator(self) -> None:
        command = delegate["canonical_arguments"](self.arguments(), self.target, ROOT)
        self.assertIn("--enforce-approval-scope", command)
        self.assertNotIn("--enforce-change-package", command)
        self.assertNotIn("--change-package", command)
        selected = delegate["canonical_arguments"](
            self.arguments("--change-package", "packages/one.json"), self.target, ROOT
        )
        self.assertEqual(selected[selected.index("--change-package") + 1], "packages/one.json")
        self.assertIn("--enforce-change-package", selected)

    def test_shipped_metadata_is_conditional_for_enabled_and_disabled_targets(self) -> None:
        for path in (DELEGATE_PATH, CONTRACT_PATH):
            destination = self.target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "templates/target" / path, destination)
        contract_path = self.target / CONTRACT_PATH
        original = contract_path.read_bytes()
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.set_module("enabled" if enabled else "disabled", enabled=enabled)
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    contract["entrypoints"]["current-change"]["canonical_delegate"]["requires_change_packages"],
                    "when-enabled",
                )
                self.assertEqual(change_packages_enabled(self.target), enabled)
                checked = validator(self.target)
                validate_validation_contract(checked, parse_manifest(self.manifest))
                self.assertEqual([finding for finding in checked.findings if finding.level == "error"], [])
                self.assertEqual(contract_path.read_bytes(), original)

    def test_historical_index_forwarding_is_limited_to_supported_operations(self) -> None:
        for operation in ("validate-current", "archive-audit"):
            arguments = [operation, "--historical-evidence-index", "evidence/history.json"]
            if operation == "validate-current":
                arguments += ["--diff-ref", "HEAD", "--approval-record", "approval.json"]
            parsed = delegate["build_parser"]().parse_args(arguments)
            self.assertEqual(parsed.historical_evidence_index, Path("evidence/history.json"))
            command = delegate["canonical_arguments"](parsed, self.target, ROOT)
            self.assertEqual(command.count("--historical-evidence-index"), 1)
            self.assertEqual(Path(command[command.index("--historical-evidence-index") + 1]), Path("evidence/history.json"))
            self.assertNotIn("--historical-evidence-index", delegate["canonical_arguments"](
                delegate["build_parser"]().parse_args(
                    ["archive-audit"] if operation == "archive-audit" else [
                        "validate-current", "--diff-ref", "HEAD", "--approval-record", "approval.json"
                    ]
                ), self.target, ROOT,
            ))
        for operation in ("status", "doctor"):
            with self.subTest(operation=operation), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    delegate["build_parser"]().parse_args([
                        operation, "--historical-evidence-index", "evidence/history.json"
                    ])
        parsed = delegate["build_parser"]().parse_args(["finalize-support", "--historical-evidence-index", "evidence/history.json"])
        command = delegate["canonical_arguments"](parsed, self.target, ROOT)
        self.assertEqual(Path(command[command.index("--historical-evidence-index") + 1]), Path("evidence/history.json"))

    def test_optional_package_omission_preserves_task_binding(self) -> None:
        parsed = self.arguments(
            "--task-id", "TASK-OPTIONAL", "--task-class", "standard-task",
            "--require-task-acceptance", "--problem-model", "models/task.json",
        )
        command = delegate["canonical_arguments"](parsed, self.target, ROOT)
        for option, value in (
            ("--task-id", "TASK-OPTIONAL"), ("--task-class", "standard-task"),
            ("--problem-model", "models/task.json"),
        ):
            self.assertEqual(command[command.index(option) + 1], value)
        self.assertIn("--require-task-acceptance", command)
        self.assertIn("--enforce-approval-scope", command)
        self.assertNotIn("--change-package", command)

    def test_default_profiles_do_not_implicitly_select_packages(self) -> None:
        for profile in ("kernel", "core", "standard", "full"):
            with self.subTest(profile=profile):
                composition = resolve_composition(CompositionRequest(profile))
                self.assertEqual(composition.requested_capabilities, ())
                self.assertNotIn("change-packages", composition.staged_capabilities)
                self.assertNotIn("change-packages", composition.enabled_capabilities)

    def test_disabled_modules_do_not_enforce_packages(self) -> None:
        for state in (None, "disabled", "deferred", "not-applicable"):
            with self.subTest(state=state):
                self.set_module(state)
                checked, errors = self.check_current()
                self.assertFalse(checked.enforce_change_package)
                self.assertFalse(change_packages_enabled(self.target))
                self.assertFalse(errors & PACKAGE_REQUIREMENTS)

    def test_enabled_modules_require_packages_and_reject_invalid_selections(self) -> None:
        for state in ("enabled", "required"):
            for packages in ([], [Path("missing.json")]):
                with self.subTest(state=state, packages=packages):
                    self.set_module(state, enabled=True)
                    checked, errors = self.check_current(packages)
                    self.assertTrue(checked.enforce_change_package)
                    self.assertTrue(change_packages_enabled(self.target))
                    self.assertIn("PACKAGE_INDEX_REQUIRED", errors)
                    self.assertIn("PACKAGE_MISSING" if packages else "PACKAGE_SELECTION_REQUIRED", errors)

    def test_enabled_modules_reject_malformed_selected_package(self) -> None:
        self.set_module("enabled", enabled=True)
        (self.target / "malformed.json").write_text("{invalid", encoding="utf-8")
        checked, errors = self.check_current([Path("malformed.json")])
        self.assertTrue(checked.enforce_change_package)
        self.assertIn("PACKAGE_INVALID_JSON", errors)

    def test_malformed_enablement_is_not_accepted_as_disabled(self) -> None:
        for declaration, expected in (
            ("  enabled: true\n", "MANIFEST_SCHEMA"),
            ("  enabled: [change-packages]\n  enabled: []\n", "MANIFEST_PARSE"),
        ):
            with self.subTest(declaration=declaration):
                self.manifest.write_text("modules:\n  selected: []\n" + declaration, encoding="utf-8")
                _, errors = self.check_current()
                self.assertIn(expected, errors)

    def test_ambiguous_enabled_state_cannot_disable_canonical_gates(self) -> None:
        for state, enabled, expected in (
            ("disabled", True, "MODULE_PROFILE_STATE_DRIFT"),
            ("enabled", False, "MODULE_MANIFEST_ENABLED_MISSING"),
            (None, True, "MODULE_PROFILE_ENABLED_MISSING"),
        ):
            with self.subTest(state=state, enabled=enabled):
                self.set_module(state, enabled=enabled)
                checked, errors = self.check_current()
                self.assertTrue(checked.enforce_change_package)
                self.assertTrue(change_packages_enabled(self.target))
                self.assertIn(expected, errors)
                self.assertTrue(errors & PACKAGE_REQUIREMENTS)

    def test_public_delegate_dispatch_without_contract_metadata_rewrites(self) -> None:
        for path in (DELEGATE_PATH, CONTRACT_PATH):
            destination = self.target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "templates/target" / path, destination)
        original_contract = (self.target / CONTRACT_PATH).read_bytes()
        environment = {key: value for key, value in os.environ.items() if key != "ALATYR_CORE"}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        (self.target / "malformed.json").write_text("{invalid", encoding="utf-8")
        for support_profile, enabled, explicit_package in (
            ("kernel", False, False), ("core", False, False),
            ("core", True, False), ("core", False, True),
        ):
            with self.subTest(profile=support_profile, enabled=enabled, explicit_package=explicit_package):
                self.set_module(
                    "enabled" if enabled else "disabled", enabled=enabled,
                    support_profile=support_profile,
                )
                result = subprocess.run([
                    sys.executable, str(self.target / DELEGATE_PATH), "validate-current",
                    "--target", str(self.target), "--framework-source", str(ROOT),
                    "--diff-ref", "HEAD", "--approval-record", "approval.json",
                    *(["--change-package", "malformed.json"] if explicit_package else []),
                ], cwd=self.target, env=environment, capture_output=True, text=True, check=False)
                output = result.stdout + result.stderr
                self.assertNotIn("the following arguments are required: --change-package", output)
                self.assertIn("VALIDATION_CONTRACT_CHECKED", output)
                self.assertNotIn("VALIDATION_CONTRACT_DELEGATE_DRIFT", output)
                self.assertEqual("PACKAGE_SELECTION_REQUIRED" in output, enabled)
                self.assertEqual("PACKAGE_INDEX_REQUIRED" in output, enabled or explicit_package)
                if explicit_package:
                    self.assertRegex(output, r"(?i)error[^\n]*PACKAGE_INVALID_JSON")
                self.assertFalse((self.target / ".ai/assistant/change-packages").exists())
                # These deliberately incomplete targets must not claim acceptance.
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((self.target / CONTRACT_PATH).read_bytes(), original_contract)


if __name__ == "__main__":
    unittest.main()
