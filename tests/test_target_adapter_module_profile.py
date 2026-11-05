from __future__ import annotations

import sys
import unittest
import json
import subprocess
import tempfile
import contextlib
import io
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.module_profile import (  # noqa: E402
    parse_module_profile,
    parse_module_profile_state,
    project_manifest_state, STATE_START, STATE_END,
)


class TargetAdapterModuleProfileTests(unittest.TestCase):
    def projection_text(self):
        return ("# Target rationale\nKeep this decision.\n" + STATE_START
                + "\nSelected modules from manifest: `none`\nStaged modules from manifest: `none`\nEnabled modules from manifest: `none`\n" + STATE_END
                + "\nModule: `diagrams`\nState: disabled\nReason: preserve this rationale\n"
                + "\nModule: `extensions`\nState: deferred\nReason: target decision\n")

    def test_projection_updates_activation_and_preserves_authored_content(self):
        text = self.projection_text()
        modules = {"selected": ["diagrams"], "staged": [], "enabled": ["diagrams"]}
        expected = project_manifest_state(text, modules)
        self.assertIn("State: `enabled`", expected)
        self.assertIn("Enabled modules from manifest: `diagrams`", expected)
        self.assertIn("Reason: preserve this rationale", expected)
        self.assertIn("State: deferred\nReason: target decision", expected)
        self.assertTrue(expected.startswith("# Target rationale\nKeep this decision.\n"))
        self.assertEqual(project_manifest_state(expected, modules), expected)
        windows = project_manifest_state(text.replace("\n", "\r\n"), modules)
        self.assertEqual(windows.replace("\r\n", "\n"), expected)
        self.assertNotIn("\n", windows.replace("\r\n", ""))

    def test_projection_is_opt_in_and_cannot_infer_disablement(self):
        self.assertEqual(project_manifest_state("Legacy target decisions", {}), "Legacy target decisions")
        text = self.projection_text().replace("State: disabled", "State: enabled")
        with self.assertRaisesRegex(ValueError, "inactive disposition"):
            project_manifest_state(text, {"selected": [], "staged": [], "enabled": []})

    def test_projection_rejects_malformed_missing_and_overlapping_bindings(self):
        valid = {"selected": ["diagrams"], "staged": [], "enabled": ["diagrams"]}
        for value in (None, True, 1, "diagrams", {}, [None], [{}], [[]], [True], ["diagrams", "diagrams"], ["bad\nname"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                project_manifest_state(self.projection_text(), dict(valid, enabled=value))
        for text in (self.projection_text().replace(STATE_END, ""), self.projection_text() + STATE_START,
                     STATE_END + STATE_START, self.projection_text() + "\nModule: `diagrams`\nState: enabled\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                project_manifest_state(text, valid)
        with self.assertRaisesRegex(ValueError, "simultaneously"):
            project_manifest_state(self.projection_text(), dict(valid, staged=["diagrams"]))
        with self.assertRaisesRegex(ValueError, "explicit profile state"):
            project_manifest_state(self.projection_text(), dict(valid, enabled=["missing"]))

    def test_projection_cli_check_is_read_only_and_public_validation_detects_drift(self):
        from check_change_packages import changed_index_validator
        from target_validation_support import parse_manifest
        from target_support_outputs import step_outputs
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir()
            manifest.write_text("modules:\n  selected: [diagrams]\n  staged: []\n  enabled: [diagrams]\n", encoding="utf-8")
            path = target / ".ai/assistant/module-profile.md"
            path.parent.mkdir()
            path.write_text(self.projection_text(), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/render_module_profile.py"), "--target", str(target)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse((target / ".ai/.runtime").exists())
            validator = changed_index_validator(target)
            validator.capability_modules = {"diagrams": {}}
            validator.check_module_profile_sync(parse_manifest(manifest))
            self.assertIn("MODULE_PROFILE_PROJECTION", {row.code for row in validator.findings})
            desired = step_outputs("module-profile", target)[path]
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/render_module_profile.py"), "--target", str(target), "--write"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_bytes(), desired)
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/render_module_profile.py"), "--target", str(target)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            validator = changed_index_validator(target)
            validator.capability_modules = {"diagrams": {}}
            validator.check_module_profile_sync(parse_manifest(manifest))
            self.assertNotIn("MODULE_PROFILE_PROJECTION", {row.code for row in validator.findings})

    def test_ambiguous_state_and_marker_content_never_consume_authored_decisions(self):
        from check_change_packages import changed_index_validator
        from target_validation_support import parse_manifest
        variants = [
            self.projection_text().replace("State: disabled", "State:\nReason: MUST SURVIVE"),
            self.projection_text().replace("State: disabled", "State: disabled\nState: deferred"),
            self.projection_text().replace("State: disabled", "State: unknown-state"),
            self.projection_text().replace(STATE_END, "Module: `retained`\nState: deferred\nReason: MUST SURVIVE\n" + STATE_END),
            self.projection_text().replace(STATE_END, "Reason: MUST SURVIVE\n" + STATE_END),
        ]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir()
            manifest.write_text("modules:\n  selected: [diagrams]\n  staged: []\n  enabled: [diagrams]\n", encoding="utf-8")
            path = target / ".ai/assistant/module-profile.md"
            path.parent.mkdir()
            for text in variants:
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    before = path.read_bytes()
                    with self.assertRaises(ValueError):
                        project_manifest_state(text, {"selected": ["diagrams"], "staged": [], "enabled": ["diagrams"]})
                    validator = changed_index_validator(target)
                    validator.capability_modules = {"diagrams": {}}
                    validator.check_module_profile_sync(parse_manifest(manifest))
                    self.assertIn("MODULE_PROFILE_PROJECTION", {row.code for row in validator.findings})
                    self.assertEqual(path.read_bytes(), before)

    def test_manifest_mutation_between_planning_and_write_rejects_without_profile_change(self):
        import render_module_profile as renderer
        from finalize_target_support import Step, execute_write_steps
        from target_adapter_validation import module_profile
        from target_support_outputs import step_outputs
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir()
            source = "modules:\n  selected: [diagrams]\n  staged: []\n  enabled: [diagrams]\n"
            manifest.write_text(source, encoding="utf-8")
            path = target / ".ai/assistant/module-profile.md"
            path.parent.mkdir()
            path.write_text(self.projection_text(), encoding="utf-8")
            before = path.read_bytes()
            original = module_profile.state_projection
            def changed(*args, **kwargs):
                result = original(*args, **kwargs)
                manifest.write_text(source.replace("staged: []", "staged: [diagrams]").replace("enabled: [diagrams]", "enabled: []"), encoding="utf-8")
                return result
            with patch.object(renderer, "state_projection", side_effect=changed), patch("sys.argv", ["render_module_profile.py", "--target", str(target), "--write"]), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(renderer.main(), 2)
            self.assertEqual(path.read_bytes(), before)
            manifest.write_text(source, encoding="utf-8")
            with patch.object(module_profile, "state_projection", side_effect=changed), contextlib.redirect_stderr(io.StringIO()):
                result, failed, conflicts = execute_write_steps(target, [Step("module-profile", "unused", ())])
            self.assertNotEqual(result, 0)
            self.assertEqual(failed, "module-profile")
            self.assertEqual(conflicts, [])
            self.assertEqual(path.read_bytes(), before)

    def test_transaction_failure_restores_module_profile_exactly(self):
        from finalize_target_support import Step, execute_write_steps
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = target / ".ai/alatyr.yaml"
            manifest.parent.mkdir()
            manifest.write_text("modules:\n  selected: [diagrams]\n  staged: []\n  enabled: [diagrams]\n", encoding="utf-8")
            path = target / ".ai/assistant/module-profile.md"
            path.parent.mkdir()
            path.write_text(self.projection_text(), encoding="utf-8")
            before = path.read_bytes()
            calls = []
            def failed(command, **kwargs):
                calls.append(command)
                self.assertNotEqual(path.read_bytes(), before)
                return SimpleNamespace(returncode=1)
            code, step, conflicts = execute_write_steps(target, [Step("module-profile", "unused", ()), Step("canonical-validation", "unused", ())], runner=failed)
            self.assertEqual((code, step, conflicts), (1, "canonical-validation", []))
            self.assertEqual(path.read_bytes(), before)
            self.assertIn("-B", calls[0])

    def test_parse_all_preserves_duplicate_declarations(self) -> None:
        states = parse_module_profile(
            "Module: `diagrams`\nState: enabled\n\n"
            "Module: `diagrams`\nState: deferred\n\n"
            "Module: `code-documentation`\n"
        )

        self.assertEqual(
            [state.state for state in states["diagrams"]],
            ["enabled", "deferred"],
        )
        self.assertIsNone(states["code-documentation"][0].state)

    def test_parse_enabled_module_state(self) -> None:
        text = """
Module: `code-documentation`
State: `enabled`

Module: `project-vocabulary`
State: disabled
"""

        state = parse_module_profile_state(text, "code-documentation")

        self.assertTrue(state.declared)
        self.assertTrue(state.has_parseable_state)
        self.assertEqual(state.state, "enabled")
        self.assertTrue(state.validation_enabled)

    def test_disabled_module_is_declared_but_not_validation_enabled(self) -> None:
        state = parse_module_profile_state(
            "Module: `project-vocabulary`\nState: disabled\n",
            "project-vocabulary",
        )

        self.assertTrue(state.declared)
        self.assertEqual(state.state, "disabled")
        self.assertFalse(state.validation_enabled)

    def test_missing_module_and_missing_state_are_distinct(self) -> None:
        missing = parse_module_profile_state("", "diagrams")
        missing_state = parse_module_profile_state("Module: `diagrams`\n", "diagrams")

        self.assertFalse(missing.declared)
        self.assertFalse(missing.has_parseable_state)
        self.assertTrue(missing_state.declared)
        self.assertFalse(missing_state.has_parseable_state)

    def test_module_id_is_matched_literally(self) -> None:
        text = "Module: `test-first-development+extra`\nState: enabled\n"

        self.assertFalse(
            parse_module_profile_state(text, "test-first-development").declared
        )
        self.assertTrue(
            parse_module_profile_state(
                text, "test-first-development+extra"
            ).validation_enabled
        )


if __name__ == "__main__":
    unittest.main()
