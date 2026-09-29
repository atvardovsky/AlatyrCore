from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from suggest_project_knowledge import suggestions  # noqa: E402


class ProjectKnowledgeSuggestionTests(unittest.TestCase):
    def test_repeated_completed_area_is_suggested_without_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            package_index = target / ".ai/assistant/change-packages/index.json"
            knowledge_index = target / ".ai/project/knowledge/index.json"
            package_index.parent.mkdir(parents=True)
            knowledge_index.parent.mkdir(parents=True)
            package_index.write_text(
                json.dumps(
                    {
                        "records": [
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
                    }
                ),
                encoding="utf-8",
            )
            knowledge_index.write_text(
                json.dumps({"promotion_records": []}), encoding="utf-8"
            )

            report = suggestions(target)

        self.assertEqual(len(report["candidates"]), 2)
        self.assertFalse(report["automatic_promotion_performed"])
