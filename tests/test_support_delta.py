from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from report_support_delta import build_report  # noqa: E402
from support_state import build_support_state  # noqa: E402


def policy() -> dict[str, object]:
    return {
        "schema_version": 1,
        "policy_kind": "target-support-policy",
        "managed_roots": [".ai"],
        "optional_entrypoints": ["AGENTS.md"],
        "exclusions": [
            {"pattern": ".ai/support-state.json", "reason": "self exclusion"}
        ],
        "classifications": [
            {
                "id": "adapter",
                "classification": "exact-contract",
                "patterns": [".ai/**", "AGENTS.md"],
            }
        ],
    }


class SupportDeltaTests(unittest.TestCase):
    def make_target(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / ".ai/project").mkdir(parents=True)
        (root / ".ai/project/support-policy.json").write_text(
            json.dumps(policy(), indent=2) + "\n",
            encoding="utf-8",
        )
        (root / ".ai/project/rule.md").write_text("rule\n", encoding="utf-8")
        (root / "AGENTS.md").write_text("agent\n", encoding="utf-8")
        state = build_support_state(root)
        (root / ".ai/support-state.json").write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=root,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
        return root

    def test_report_separates_support_and_product_paths(self) -> None:
        target = self.make_target()
        (target / ".ai/project/rule.md").write_text("changed\n", encoding="utf-8")
        (target / "src").mkdir()
        (target / "src/example.py").write_text("print('x')\n", encoding="utf-8")

        report = build_report(target, "HEAD")

        self.assertEqual(report["report_kind"], "target-support-delta")
        self.assertFalse(report["support_state_current"])
        self.assertRegex(report["delta_digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertIn(".ai/project/rule.md", report["changed_support_paths"])
        self.assertIn("src/example.py", report["changed_product_paths"])
        self.assertEqual(report["changed_path_summary"]["support_count"], 1)
        self.assertEqual(report["changed_path_summary"]["product_count"], 1)
        self.assertRegex(
            report["changed_path_summary"]["digest"], r"^sha256:[0-9a-f]{64}$"
        )
        self.assertEqual(
            report["changed_support_groups"],
            {"project": [".ai/project/rule.md"]},
        )
        self.assertIn(".ai/project/context-index.json", report["candidate_owner_context"])
        self.assertIn("semantic correctness", report["reasoning_boundary"])

    def test_report_uses_target_relative_git_paths_for_subdirectory_adapter(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        repo = Path(directory.name)
        target = repo / "templates" / "target"
        (target / ".ai/project").mkdir(parents=True)
        (target / ".ai/project/support-policy.json").write_text(
            json.dumps(policy(), indent=2) + "\n",
            encoding="utf-8",
        )
        (target / ".ai/project/rule.md").write_text("rule\n", encoding="utf-8")
        (target / "AGENTS.md").write_text("target agent\n", encoding="utf-8")
        (repo / "AGENTS.md").write_text("source agent\n", encoding="utf-8")
        state = build_support_state(target)
        (target / ".ai/support-state.json").write_text(
            json.dumps(state, indent=2) + "\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)

        (repo / "AGENTS.md").write_text("source changed\n", encoding="utf-8")
        (target / ".ai/project/rule.md").write_text("target changed\n", encoding="utf-8")
        (target / "src").mkdir()
        (target / "src/example.py").write_text("print('target')\n", encoding="utf-8")

        report = build_report(target, "HEAD")

        self.assertIn(".ai/project/rule.md", report["changed_support_paths"])
        self.assertIn("src/example.py", report["changed_product_paths"])
        self.assertNotIn(
            "templates/target/.ai/project/rule.md",
            report["changed_product_paths"],
        )
        self.assertNotIn("templates/target/AGENTS.md", report["changed_product_paths"])
        self.assertNotIn("AGENTS.md", report["changed_product_paths"])


if __name__ == "__main__":
    unittest.main()
