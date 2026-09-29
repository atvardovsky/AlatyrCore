from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from suggest_project_knowledge import suggestions  # noqa: E402


class ProjectKnowledgeSuggestionTests(unittest.TestCase):
    def test_helper_supports_package_style_import(self) -> None:
        result = subprocess.run(
            [sys.executable, "-c", "from tools.suggest_project_knowledge import suggestions"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def suggestions_for(self, records: list[dict[str, object]]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            package_index = target / ".ai/assistant/change-packages/index.json"
            knowledge_index = target / ".ai/project/knowledge/index.json"
            package_index.parent.mkdir(parents=True)
            knowledge_index.parent.mkdir(parents=True)
            package_index.write_text(
                json.dumps({"records": records}),
                encoding="utf-8",
            )
            knowledge_index.write_text(
                json.dumps({"promotion_records": []}), encoding="utf-8"
            )
            return suggestions(target)

    def test_repeated_completed_area_is_suggested_without_promotion(self) -> None:
        report = self.suggestions_for(
            [
                {
                    "package_id": "A",
                    "status": "validated",
                    "project_areas": ["billing"],
                    "canonical_owners": ["docs/billing.md"],
                },
                {
                    "package_id": "B",
                    "status": "complete",
                    "project_areas": ["billing"],
                    "canonical_owners": ["docs/billing.md"],
                },
            ]
        )

        self.assertEqual(len(report["candidates"]), 2)
        self.assertEqual(report["validated_or_completed_packages_considered"], 2)
        self.assertFalse(report["automatic_promotion_performed"])

    def test_nonterminal_and_substring_statuses_are_not_candidates(self) -> None:
        rejected_statuses = [
            "proposed",
            "approved",
            "implementing",
            "blocked",
            "incomplete",
            "unvalidated",
            "not completed",
            "published",
            "deployed",
        ]
        report = self.suggestions_for(
            [
                {
                    "package_id": f"P{index}",
                    "status": status,
                    "project_areas": ["billing"],
                    "canonical_owners": ["docs/billing.md"],
                }
                for index, status in enumerate(rejected_statuses)
            ]
        )

        self.assertEqual(report["validated_or_completed_packages_considered"], 0)
        self.assertEqual(report["candidates"], [])
