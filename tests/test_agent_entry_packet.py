from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agent_entry_packet import build_agent_entry_packet  # noqa: E402


class AgentEntryPacketTests(unittest.TestCase):
    def base_inputs(self) -> dict[str, str]:
        manifest = """\
schema_version: 38
framework:
  version: 0.1.0-alpha.42
  template_version: 40
  pack: kernel
installation:
  support_profile: kernel
  state: accepted
modules:
  enabled: []
"""
        router = {
            "preloaded_context": ["AGENTS.md"],
            "bootstrap_context": [".ai/assistant/bootstrap-index.json"],
            "context_budgets": {
                "bootstrap": {"max_files": 2, "max_words": 1800},
                "profile_default": {"max_files": 12, "max_total_words": 8000},
                "on_exceed": "record expansion",
            },
            "profile_index": {
                "code-local": {
                    "use_when": ["code"],
                    "descriptor": ".ai/assistant/context/profiles/code-local.json",
                    "operation_candidates": ["logical-integrity-review"],
                }
            },
            "operation_routing": {
                "index": ".ai/assistant/operation-index.json",
                "catalog": ".ai/assistant/operation-catalog.json",
                "fallback_operation": "help",
                "load_index_when": ["exact operation ID"],
                "load_catalog_when": ["ambiguity"],
            },
        }
        gates = {
            "gates": {
                "core": {"path": ".ai/assistant/gates/core.md"},
                "final-evidence": {"path": ".ai/assistant/gates/final-evidence.md"},
            },
            "profile_defaults": {"code-local": ["core", "final-evidence"]},
        }
        authorization = {
            "default_phase": "inspect",
            "phases": ["inspect", "modify", "commit", "publish", "live-external"],
        }
        support_policy = {
            "schema_version": 1,
            "policy_kind": "target-support-policy",
            "managed_roots": [".ai"],
            "optional_entrypoints": ["AGENTS.md"],
            "exclusions": [],
            "classifications": [],
        }
        task_decomposition = {
            "schema_version": 1,
            "policy_kind": "target-task-decomposition-policy",
            "plan_template": ".ai/assistant/templates/task-decomposition.md",
            "default_behavior": "decompose every non-trivial request",
            "small_task_behavior": "one local task",
            "levels": [
                {"id": "L0", "worker_roles": []},
                {"id": "L1", "worker_roles": ["explorer"]},
                {"id": "L2", "worker_roles": ["documentation-worker"]},
                {"id": "L3", "worker_roles": ["test-runner"]},
                {"id": "L4", "worker_roles": ["implementer"]},
                {"id": "L5", "worker_roles": ["reviewer"]},
                {"id": "L6", "worker_roles": []},
                {"id": "L7", "worker_roles": []},
            ],
            "executor_selection": {
                "default": "primary",
                "selection_order": ["primary first"],
                "fallback": "primary execution",
            },
        }
        return {
            "manifest": manifest,
            "router": json.dumps(router),
            "gates": json.dumps(gates),
            "authorization": json.dumps(authorization),
            "support_policy": json.dumps(support_policy),
            "task_decomposition": json.dumps(task_decomposition),
        }

    def test_packet_records_profile_gates_and_actions(self) -> None:
        inputs = self.base_inputs()
        packet = build_agent_entry_packet(
            inputs["manifest"],
            inputs["router"],
            inputs["gates"],
            inputs["authorization"],
            inputs["support_policy"],
            inputs["task_decomposition"],
            operation_index_text=json.dumps(
                {
                    "operations": {
                        "logical-integrity-review": [
                            "core-profile",
                            ".ai/assistant/flows/logical-integrity-review.flow.md",
                            "read-only",
                            "code-and-tests",
                        ]
                    }
                }
            ),
        )

        self.assertEqual(packet["schema_version"], 3)
        self.assertEqual(
            packet["routing_sources"]["installed_profile_routes"],
            ".ai/assistant/bootstrap-index.json",
        )
        self.assertEqual(
            packet["operation_routing"]["index"],
            ".ai/assistant/operation-index.json",
        )
        self.assertNotIn("profile_routes", packet)
        self.assertNotIn("allowed_action_modes", packet["authorization"])
        self.assertIn(
            "tools/alatyr.py support-delta",
            packet["support_delta_first"]["support_delta_tool"],
        )
        self.assertIn(
            "tools/alatyr.py approval-check",
            packet["support_delta_first"]["approval_scope_check_tool"],
        )
        self.assertIn(
            "--approval-record <target-approval-json>",
            packet["support_delta_first"]["approval_scope_check_tool"],
        )
        decomposition = packet["task_decomposition"]
        self.assertEqual(
            decomposition["policy"],
            ".ai/assistant/task-decomposition.json",
        )
        self.assertEqual(
            decomposition["plan_template"],
            ".ai/assistant/templates/task-decomposition.md",
        )
        self.assertEqual(
            decomposition["level_range"],
            "L0-L7",
        )
        self.assertEqual(decomposition["executor_default"], "primary")
        self.assertIn("L6", decomposition["non_delegable_levels"])
        self.assertIn("L7", decomposition["non_delegable_levels"])

    def test_packet_omits_operation_routes_when_index_is_absent(self) -> None:
        inputs = self.base_inputs()
        packet = build_agent_entry_packet(
            inputs["manifest"],
            inputs["router"],
            inputs["gates"],
            inputs["authorization"],
            inputs["support_policy"],
            inputs["task_decomposition"],
        )

        self.assertNotIn("operation_routes", packet["operation_routing"])


if __name__ == "__main__":
    unittest.main()
