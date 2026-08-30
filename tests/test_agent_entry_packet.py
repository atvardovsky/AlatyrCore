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
schema_version: 36
framework:
  version: 0.1.0-alpha.39
  template_version: 37
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
        return {
            "manifest": manifest,
            "router": json.dumps(router),
            "gates": json.dumps(gates),
            "authorization": json.dumps(authorization),
            "support_policy": json.dumps(support_policy),
        }

    def test_packet_records_profile_gates_and_actions(self) -> None:
        inputs = self.base_inputs()
        packet = build_agent_entry_packet(
            inputs["manifest"],
            inputs["router"],
            inputs["gates"],
            inputs["authorization"],
            inputs["support_policy"],
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
            profile_descriptors={
                "code-local": {
                    "operation_candidates": ["logical-integrity-review"],
                    "required_context": [".ai/framework/logical-integrity.md"],
                    "approval_gates": ["protected_category_crossed"],
                    "validation": ["pytest"],
                    "final_evidence": ["validation"],
                }
            },
        )

        self.assertEqual(
            packet["profile_recommendation"]["default_install_profile"],
            "kernel",
        )
        self.assertIn("code-local", packet["profile_routes"])
        code_route = packet["profile_routes"]["code-local"]
        self.assertEqual(
            code_route["default_gate_paths"],
            [".ai/assistant/gates/core.md", ".ai/assistant/gates/final-evidence.md"],
        )
        self.assertEqual(
            code_route["required_context"],
            [".ai/framework/logical-integrity.md"],
        )
        operation = packet["operation_routing"]["operation_routes"][
            "logical-integrity-review"
        ]
        self.assertEqual(operation["allowed_actions"], ["read-only", "code-and-tests"])
        self.assertIn("read-only", packet["authorization"]["allowed_action_modes"])
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

    def test_packet_omits_operation_routes_when_index_is_absent(self) -> None:
        inputs = self.base_inputs()
        packet = build_agent_entry_packet(
            inputs["manifest"],
            inputs["router"],
            inputs["gates"],
            inputs["authorization"],
            inputs["support_policy"],
        )

        self.assertEqual(packet["operation_routing"]["operation_routes"], {})


if __name__ == "__main__":
    unittest.main()
