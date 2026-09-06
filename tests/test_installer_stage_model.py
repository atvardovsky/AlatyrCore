from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from installer_stage_model import (  # noqa: E402
    MINIMUM_CONTEXT_HEADROOM_RATIO,
    deterministic_word_count,
    load_installer_stage_plan,
    stage_checkpoint_identity,
    validate_required_context_budgets,
    verify_stage_checkpoint,
)


def digest_map(contract_ids: tuple[str, ...], character: str) -> dict[str, str]:
    return {contract_id: "sha256:" + character * 64 for contract_id in contract_ids}


class InstallerStageModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = load_installer_stage_plan(
            ROOT / "installer/context-router.json", source_root=ROOT
        )

    def checkpoint_inputs(
        self, stage_id: str = "scope-selection"
    ) -> dict[str, object]:
        return {
            "source_root": ROOT,
            "target_revision": "abc123",
            "composition_digest": "sha256:" + "1" * 64,
            "output_digests": digest_map(
                self.plan.required_output_ids_through(stage_id), "2"
            ),
            "evidence_digests": digest_map(
                self.plan.required_evidence_ids_through(stage_id), "3"
            ),
        }

    def test_source_router_has_closed_ordered_stage_model(self) -> None:
        self.assertEqual(
            [stage.stage_id for stage in self.plan.stages],
            [
                "discovery",
                "scope-selection",
                "plan-and-approval",
                "adaptation",
                "validation",
                "acceptance-recording",
                "handoff",
            ],
        )
        self.assertEqual(
            [stage.stage_id for stage in self.plan.through("adaptation")],
            ["discovery", "scope-selection", "plan-and-approval", "adaptation"],
        )
        acceptance = self.plan.through("acceptance-recording")[-1]
        handoff = self.plan.through("handoff")[-1]
        self.assertEqual(acceptance.authorization_ceiling, "modify")
        self.assertEqual(acceptance.depends_on, ("validation",))
        self.assertEqual(handoff.authorization_ceiling, "inspect")
        self.assertEqual(handoff.depends_on, ("acceptance-recording",))

    def test_required_context_has_declared_headroom(self) -> None:
        usage = validate_required_context_budgets(self.plan, source_root=ROOT)

        self.assertEqual(len(usage), len(self.plan.stages))
        self.assertGreaterEqual(
            self.plan.minimum_context_headroom_ratio,
            MINIMUM_CONTEXT_HEADROOM_RATIO,
        )
        for stage in usage:
            self.assertGreaterEqual(
                stage.headroom_ratio, self.plan.minimum_context_headroom_ratio
            )

    def test_word_count_is_platform_independent(self) -> None:
        self.assertEqual(
            deterministic_word_count("alpha\r\nbeta\tgamma\n\ndelta"), 4
        )

    def test_checkpoint_binds_complete_cumulative_contract(self) -> None:
        inputs = self.checkpoint_inputs()
        checkpoint = stage_checkpoint_identity(
            self.plan, "scope-selection", **inputs
        )

        self.assertEqual(checkpoint["completed_stage"], "scope-selection")
        self.assertEqual(
            set(checkpoint["output_digests"]),
            set(self.plan.required_output_ids_through("scope-selection")),
        )
        self.assertEqual(
            set(checkpoint["evidence_digests"]),
            set(self.plan.required_evidence_ids_through("scope-selection")),
        )
        self.assertIn(
            "installer/discovery-contract.json", checkpoint["required_input_digests"]
        )
        self.assertIn("never approval", checkpoint["authority"])

    def test_checkpoint_reuse_requires_exact_current_identity(self) -> None:
        inputs = self.checkpoint_inputs()
        checkpoint = stage_checkpoint_identity(
            self.plan, "scope-selection", **inputs
        )

        current = verify_stage_checkpoint(
            checkpoint, self.plan, "scope-selection", **inputs
        )
        self.assertTrue(current.reusable)
        self.assertEqual(current.reasons, ())

        changed_inputs = dict(inputs)
        changed_inputs["target_revision"] = "def456"
        changed = verify_stage_checkpoint(
            checkpoint, self.plan, "scope-selection", **changed_inputs
        )
        self.assertFalse(changed.reusable)
        self.assertIn("target_revision", changed.reasons[0])

        tampered = dict(checkpoint)
        tampered["unexpected"] = "value"
        extra = verify_stage_checkpoint(
            tampered, self.plan, "scope-selection", **inputs
        )
        self.assertFalse(extra.reusable)
        self.assertTrue(any("unknown fields" in reason for reason in extra.reasons))

    def test_checkpoint_rejects_empty_incomplete_and_noncanonical_bindings(self) -> None:
        inputs = self.checkpoint_inputs()
        empty = dict(inputs)
        empty["output_digests"] = {}
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            stage_checkpoint_identity(self.plan, "scope-selection", **empty)

        incomplete = dict(inputs)
        incomplete_outputs = dict(inputs["output_digests"])
        incomplete_outputs.pop(next(iter(incomplete_outputs)))
        incomplete["output_digests"] = incomplete_outputs
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            stage_checkpoint_identity(self.plan, "scope-selection", **incomplete)

        malformed = dict(inputs)
        malformed_evidence = dict(inputs["evidence_digests"])
        first_id = next(iter(malformed_evidence))
        malformed_evidence[first_id] = "sha256:" + "A" * 64
        malformed["evidence_digests"] = malformed_evidence
        with self.assertRaisesRegex(ValueError, "canonical lowercase SHA-256"):
            stage_checkpoint_identity(self.plan, "scope-selection", **malformed)

    def test_rejects_dependency_on_a_later_stage(self) -> None:
        source = json.loads((ROOT / "installer/context-router.json").read_text())
        source["stages"]["discovery"]["depends_on"] = ["handoff"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "router.json"
            path.write_text(json.dumps(source), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "later or unknown"):
                load_installer_stage_plan(path)

    def test_rejects_required_context_without_minimum_headroom(self) -> None:
        source = json.loads((ROOT / "installer/context-router.json").read_text())
        source["stages"]["discovery"]["required_context"] = ["large.txt"]
        source["stages"]["discovery"]["context_budget_words"] = 10
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            router = root / "router.json"
            router.write_text(json.dumps(source), encoding="utf-8")
            (root / "large.txt").write_text("word " * 9, encoding="utf-8")
            for stage in source["stages"].values():
                for relpath in stage.get("required_context", []):
                    path = root / relpath
                    if not path.exists():
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("small context", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "minimum headroom"):
                load_installer_stage_plan(router, source_root=root)


if __name__ == "__main__":
    unittest.main()
