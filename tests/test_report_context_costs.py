from __future__ import annotations

import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_context_costs import build_installed_report, installed_path, presence_references, build_report, measure_cost_scenarios  # noqa: E402


class InstalledContextCostPathTests(unittest.TestCase):
    def test_activated_consistency_conditionals_are_in_task_and_total_costs(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            for name, text in (("a", "one"), ("b", "two words")):
                path = target / ".ai/project" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            scenarios = {"scenarios": {"active": {"profile": "docs-local", "consistency_routing": True,
                         "activated_conditional_context": [".ai/project/b", ".ai/project/b"]}}}
            profiles = {"docs-local": (None, {"required_context": [".ai/project/a"]})}
            consistency = {"conditional_context": [{"path": ".ai/project/b", "when": "explicit fixture"}]}
            with patch("report_context_costs.TARGET", target), patch("report_context_costs.source_path", side_effect=lambda p: target / p), patch(
                "report_context_costs.descriptor", return_value=(None, scenarios)
            ):
                result = measure_cost_scenarios({}, profiles, {}, {}, None, consistency)["active"]
                self.assertEqual(result["words"], 3)
                self.assertEqual(result["end_to_end"]["words"], 3)
                self.assertEqual(result["activated_conditional_context"], [".ai/project/b"])
                scenarios["scenarios"]["active"]["activated_conditional_context"] = [".ai/project/unknown"]
                with self.assertRaisesRegex(ValueError, "unknown conditional"):
                    measure_cost_scenarios({}, profiles, {}, {}, None, consistency)
    def test_presence_accounting_uses_canonical_enabled_disabled_and_legacy_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(presence_references(root), [])
            path = root / ".ai/assistant/policies/session-continuity.json"
            path.parent.mkdir(parents=True)
            policy = __import__("json").loads((ROOT / "templates/target" / path.relative_to(root)).read_text())
            path.write_text(__import__("json").dumps(policy))
            self.assertIn(policy["presence"]["flow"], presence_references(root))
            self.assertEqual(presence_references(root, worker=True), [])
            policy["presence"]["enabled"] = False
            path.write_text(__import__("json").dumps(policy))
            self.assertEqual(presence_references(root), [".ai/assistant/policies/session-continuity.json"])

    def test_operational_scenarios_include_presence_without_claiming_billed_tokens(self):
        report = build_report()
        self.assertGreater(report["operational_entry"]["words"], report["first_use"]["words"])
        for scenario in report["cost_scenarios"].values():
            self.assertIn(".ai/assistant/flows/session-presence.flow.md", scenario["end_to_end"]["resolved_paths"])
            self.assertIs(scenario["runtime_output_measured"], False)

    def test_installed_path_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()

            self.assertIsNone(installed_path(target, "../outside.txt"))
            self.assertIsNone(installed_path(target, ".ai/../../outside.txt"))

    def test_installed_path_rejects_invalid_portable_spellings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            self.assertIsNone(installed_path(target, ""))
            self.assertIsNone(installed_path(target, r".ai\assistant\router.json"))
            self.assertIsNone(installed_path(target, "C:relative\\router.json"))

    def test_installed_path_rejects_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            self.assertIsNone(installed_path(target, str(target / "AGENTS.md")))
            self.assertIsNone(installed_path(target, r"C:\outside\AGENTS.md"))
            self.assertIsNone(installed_path(target, r"\\server\share\AGENTS.md"))

    def test_installed_path_accepts_target_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)

            self.assertEqual(
                installed_path(target, ".ai/assistant/context-router.json"),
                (target / ".ai/assistant/context-router.json").resolve(),
            )
            self.assertEqual(
                installed_path(target, "AGENTS.md"),
                (target / "AGENTS.md").resolve(),
            )

    def test_installed_path_rejects_symlink_escape_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            link = target / "linked-outside.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            self.assertIsNone(installed_path(target, "linked-outside.txt"))

    def test_installed_report_rejects_symlinked_router_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            router_dir = target / ".ai" / "assistant"
            router_dir.mkdir(parents=True)
            outside = root / "outside-router.json"
            outside.write_text("{}\n", encoding="utf-8")
            try:
                (router_dir / "context-router.json").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "outside target root"):
                build_installed_report(target)


if __name__ == "__main__":
    unittest.main()
