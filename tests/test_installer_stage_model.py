from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from installer_stage_model import (  # noqa: E402
    load_installer_stage_plan,
    stage_checkpoint_identity,
)


class InstallerStageModelTests(unittest.TestCase):
    def test_source_router_has_closed_ordered_stage_model(self) -> None:
        plan = load_installer_stage_plan(ROOT / "installer/context-router.json")

        self.assertEqual(
            [stage.stage_id for stage in plan.stages],
            [
                "discovery",
                "scope-selection",
                "plan-and-approval",
                "adaptation",
                "validation",
                "handoff",
            ],
        )
        self.assertEqual(
            [stage.stage_id for stage in plan.through("adaptation")],
            ["discovery", "scope-selection", "plan-and-approval", "adaptation"],
        )

    def test_checkpoint_binds_required_inputs_and_denies_authority(self) -> None:
        plan = load_installer_stage_plan(ROOT / "installer/context-router.json")

        checkpoint = stage_checkpoint_identity(
            plan, "scope-selection", source_root=ROOT
        )

        self.assertEqual(checkpoint["completed_stage"], "scope-selection")
        self.assertIn("INSTALL.md", checkpoint["required_input_digests"])
        self.assertIn("never approval", checkpoint["authority"])

    def test_rejects_dependency_on_a_later_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "router.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "router_kind": "alatyr-installation-context-router",
                        "routing_order": ["first", "second"],
                        "stages": {
                            "first": {
                                "required_context": ["one"],
                                "depends_on": ["second"],
                                "prohibited_actions": ["write"],
                            },
                            "second": {
                                "required_context": ["two"],
                                "prohibited_actions": ["write"],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "later or unknown"):
                load_installer_stage_plan(path)


if __name__ == "__main__":
    unittest.main()
