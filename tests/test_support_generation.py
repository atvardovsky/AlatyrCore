from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import support_generation

from support_generation import (
    INDEX_PATH,
    REGISTRY_PATH,
    SupportGenerationError,
    build_generation_index,
    generation_plan,
    render_json,
    topological_order,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2) + "\n").encode("utf-8"))


def registry() -> dict[str, object]:
    return {
        "schema_version": 1,
        "registry_kind": "target-support-generation-registry",
        "artifacts": [
            {
                "id": "api-reference",
                "owner": "docs/api-policy.md",
                "mode": "deterministic-derived",
                "inputs": [{"path": "src/api.txt", "selector_kind": "file", "selector": "whole-file"}],
                "outputs": ["docs/api.txt"],
                "depends_on": [],
                "generator": {
                    "execution_contract": "staged-output-only",
                    "command": ["generator", "{OUTPUT_DIR}"],
                },
                "validation": ["manual review"],
                "approval_trigger": "none",
            },
            {
                "id": "public-guide",
                "owner": "docs/guide-policy.md",
                "mode": "owner-maintained",
                "inputs": [{"path": "docs/api.txt", "selector_kind": "file", "selector": "whole-file"}],
                "outputs": ["docs/guide.txt"],
                "depends_on": ["api-reference"],
                "generator": {"execution_contract": "not-executable", "command": []},
                "validation": ["owner review"],
                "approval_trigger": "none",
            },
        ],
    }


class SupportGenerationTests(unittest.TestCase):
    def make_target(self) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        write_json(target / REGISTRY_PATH, registry())
        for relpath, content in {
            "src/api.txt": "source\n",
            "docs/api.txt": "derived\n",
            "docs/guide.txt": "guide\n",
        }.items():
            path = target / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=target, check=True)
        subprocess.run(["git", "add", "."], cwd=target, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=target, check=True)
        return target

    def test_index_records_dependency_order_and_current_digests(self) -> None:
        target = self.make_target()
        index = build_generation_index(target)
        self.assertEqual(index["order"], ["api-reference", "public-guide"])
        (target / INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
        (target / INDEX_PATH).write_bytes(render_json(index).encode("utf-8"))
        plan = generation_plan(target)
        self.assertTrue(all(action["status"] == "current" for action in plan["actions"]))

    def test_input_change_marks_artifact_stale(self) -> None:
        target = self.make_target()
        index = build_generation_index(target)
        (target / INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
        (target / INDEX_PATH).write_bytes(render_json(index).encode("utf-8"))
        (target / "src/api.txt").write_bytes(b"changed\n")
        plan = generation_plan(target)
        action = next(item for item in plan["actions"] if item["id"] == "api-reference")
        self.assertEqual(action["status"], "stale")
        self.assertIn("inputs-changed", action["reasons"])

    def test_generation_index_enumerates_repository_once(self) -> None:
        target = self.make_target()
        original = support_generation._repository_paths
        with patch(
            "support_generation._repository_paths", wraps=original
        ) as repository_paths:
            build_generation_index(target)

        repository_paths.assert_called_once_with(target.resolve())

    def test_cycle_is_rejected(self) -> None:
        value = registry()
        value["artifacts"][0]["depends_on"] = ["public-guide"]
        with self.assertRaisesRegex(SupportGenerationError, "cycle"):
            topological_order(value)


if __name__ == "__main__":
    unittest.main()
