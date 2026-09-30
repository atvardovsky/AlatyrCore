from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.harness_scenarios.common import validator  # noqa: E402
from target_adapter_validation.task_decomposition import (  # noqa: E402
    validate_task_decomposition,
)


REQUIRED_PATHS = (
    ".ai/framework/task-decomposition.md",
    ".ai/assistant/task-decomposition.json",
    ".ai/assistant/context-router.json",
    ".ai/assistant/templates/task-decomposition.md",
    ".ai/assistant/templates/operation-request.md",
    ".ai/assistant/templates/operation-completion-evidence.json",
    ".ai/assistant/flows/operation-routing.flow.md",
)


class TaskDecompositionValidatorTests(unittest.TestCase):
    def make_target(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        source_root = ROOT / "templates/target"
        for relpath in REQUIRED_PATHS:
            source = (
                ROOT / "framework/task-decomposition.md"
                if relpath == ".ai/framework/task-decomposition.md"
                else source_root / relpath
            )
            destination = target / relpath
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        return target

    def findings(self, target: Path) -> set[str]:
        checked = validator(target)
        validate_task_decomposition(checked, None)
        return {finding.code for finding in checked.findings}

    def test_completion_evidence_requires_project_contour_sync(self) -> None:
        target = self.make_target()
        completion_path = (
            target / ".ai/assistant/templates/operation-completion-evidence.json"
        )
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        del completion["consistency"]["project_contour_sync"]
        completion_path.write_text(
            json.dumps(completion, indent=2) + "\n",
            encoding="utf-8",
        )

        self.assertIn(
            "TASK_DECOMPOSITION_COMPLETION_EVIDENCE",
            self.findings(target),
        )


if __name__ == "__main__":
    unittest.main()
