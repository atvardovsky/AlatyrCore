from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_target_adapter import missing_bridge_references  # noqa: E402


class BridgeReferenceTests(unittest.TestCase):
    def test_missing_cost_discipline_reference_is_detected(self) -> None:
        text = "Default: `.ai/project/implementation-workflow.md#default-execution-cost-discipline`.\n"
        self.assertEqual(
            missing_bridge_references(text, lambda value: False),
            [".ai/project/implementation-workflow.md"],
        )

    def test_existing_files_directories_and_anchors_resolve(self) -> None:
        text = (
            "Load `.ai/assistant/bootstrap-index.json`, `.ai/README.md#bootstrap`, "
            "and `.ai/framework/`.\n"
        )
        existing = {
            ".ai/assistant/bootstrap-index.json",
            ".ai/README.md",
            ".ai/framework",
        }
        self.assertEqual(
            missing_bridge_references(text, lambda value: value in existing),
            [],
        )

    def test_globs_placeholders_urls_and_duplicates_are_not_reported(self) -> None:
        text = (
            "Use `.ai/project/**/*.md`, `.ai/{CONTOUR}/README.md`, "
            "`.ai/framework/*.md`, and `.ai/project/implementation-workflow.md`. "
            "Repeat `.ai/project/implementation-workflow.md`.\n"
        )
        self.assertEqual(
            missing_bridge_references(text, lambda value: False),
            [".ai/project/implementation-workflow.md"],
        )

    def test_trailing_punctuation_and_slashes_are_normalized(self) -> None:
        text = "Use `.ai/project/implementation-workflow.md`, and `.ai/framework/`.\n"
        seen: list[str] = []

        def exists(value: str) -> bool:
            seen.append(value)
            return True

        self.assertEqual(missing_bridge_references(text, exists), [])
        self.assertCountEqual(
            seen,
            [".ai/project/implementation-workflow.md", ".ai/framework"],
        )


if __name__ == "__main__":
    unittest.main()
