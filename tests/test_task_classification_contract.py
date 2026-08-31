from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from task_classification_contract import (  # noqa: E402
    AMBIGUITY_READ_ONLY_MARKER,
    DEFAULT_TASK_CLASS,
    SMALL_TASK_CLASS,
    SOURCE_REQUIRED_EXPANSION_TRIGGERS,
    SOURCE_SMALL_TASK_FOCUSED_CHECKS_MARKER,
    TARGET_REQUIRED_EXPANSION_TRIGGERS,
    TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS,
    TASK_CLASSES,
    TASK_CLASSIFICATION_SCHEMA_VERSION,
)


TARGET_ROUTER = ROOT / "templates/target/.ai/assistant/context-router.json"
TARGET_SMALL_TASK = (
    ROOT / "templates/target/.ai/assistant/context/task-scales/small-task.json"
)
TARGET_ENTRY_PACKET = ROOT / "templates/target/.ai/assistant/entry-packet.json"
SOURCE_ROUTER = ROOT / "tools/source_context_router.json"


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path.relative_to(ROOT)} must contain an object")
    return data


class TaskClassificationContractTests(unittest.TestCase):
    def test_target_router_uses_shared_task_classification_contract(self) -> None:
        router = load_json(TARGET_ROUTER)
        classification = router["task_classification"]
        self.assertIsInstance(classification, dict)

        assert isinstance(classification, dict)
        self.assertEqual(
            classification["schema_version"],
            TASK_CLASSIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(classification["classification_order"], TASK_CLASSES)
        self.assertEqual(classification["default_class"], DEFAULT_TASK_CLASS)
        self.assertIn(
            AMBIGUITY_READ_ONLY_MARKER,
            str(classification["ambiguity_behavior"]),
        )
        classes = classification["classes"]
        self.assertIsInstance(classes, dict)
        assert isinstance(classes, dict)
        for task_class in TASK_CLASSES:
            self.assertIn(task_class, classes)
        self.assertEqual(
            classes[SMALL_TASK_CLASS]["task_scale_overlay"],
            SMALL_TASK_CLASS,
        )
        for trigger in TARGET_REQUIRED_EXPANSION_TRIGGERS:
            self.assertIn(trigger, classification["expansion_triggers"])

    def test_target_small_task_overlay_uses_shared_expansion_triggers(self) -> None:
        overlay = load_json(TARGET_SMALL_TASK)

        self.assertEqual(overlay["schema_version"], 1)
        self.assertEqual(overlay["overlay"], SMALL_TASK_CLASS)
        for trigger in TARGET_REQUIRED_SMALL_TASK_EXPANSION_TRIGGERS:
            self.assertIn(trigger, overlay["expand_when"])

    def test_entry_packet_preserves_target_task_classification_contract(self) -> None:
        packet = load_json(TARGET_ENTRY_PACKET)
        classification = packet["task_classification"]
        self.assertIsInstance(classification, dict)

        assert isinstance(classification, dict)
        self.assertEqual(
            classification["schema_version"],
            TASK_CLASSIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(classification["classification_order"], TASK_CLASSES)
        self.assertEqual(classification["default_class"], DEFAULT_TASK_CLASS)
        self.assertIn(
            AMBIGUITY_READ_ONLY_MARKER,
            str(classification["ambiguity_behavior"]),
        )
        for trigger in TARGET_REQUIRED_EXPANSION_TRIGGERS:
            self.assertIn(trigger, classification["expansion_triggers"])

    def test_source_router_uses_shared_task_classification_contract(self) -> None:
        router = load_json(SOURCE_ROUTER)
        classification = router["task_classification"]
        self.assertIsInstance(classification, dict)

        assert isinstance(classification, dict)
        self.assertEqual(
            classification["schema_version"],
            TASK_CLASSIFICATION_SCHEMA_VERSION,
        )
        self.assertEqual(classification["classification_order"], TASK_CLASSES)
        self.assertEqual(classification["default_class"], DEFAULT_TASK_CLASS)
        self.assertIn(
            AMBIGUITY_READ_ONLY_MARKER,
            str(classification["ambiguity_behavior"]),
        )
        self.assertTrue(
            any(
                SOURCE_SMALL_TASK_FOCUSED_CHECKS_MARKER in item
                for item in classification["small_task_use_when"]
            )
        )
        for trigger in SOURCE_REQUIRED_EXPANSION_TRIGGERS:
            self.assertIn(trigger, classification["expansion_triggers"])


if __name__ == "__main__":
    unittest.main()
