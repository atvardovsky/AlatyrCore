from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from context_receipt import (
    semantic_guidance_bundle_digest,
    supports_observed_context_claim,
    validate_context_receipt,
)
from summarize_effectiveness_benchmark import render_summary
from conformance_execution.codex_benchmark import update_report


def exact_receipt() -> dict[str, object]:
    return {
        "schema_version": 1,
        "receipt_kind": "alatyr-context-receipt",
        "measurement_state": "observed",
        "planned": {"paths": ["AGENTS.md"], "approximate_words": 100},
        "resolved": {
            "status": "recorded",
            "paths": ["AGENTS.md", "framework/context-router.md"],
            "approximate_words": 250,
        },
        "observed": {
            "evidence_level": "exact",
            "source": "host-telemetry",
            "files_loaded": 2,
            "input_tokens": 400,
            "output_tokens": 100,
            "evidence": "host usage receipt 123",
        },
    }


def semantic_identity(guidance_id: str = "guidance-001") -> dict[str, str]:
    return {
        "guidance_id": guidance_id,
        "canonical_owner": ".ai/project/architecture.md",
        "owner_digest": f"sha256:{'a' * 64}",
        "authority": "accepted",
        "freshness": "current",
        "applicability": "applies",
    }


def with_semantic_guidance(receipt: dict[str, object]) -> dict[str, object]:
    identity = semantic_identity()
    identities = [identity]
    digest = semantic_guidance_bundle_digest(identities)
    receipt["semantic_guidance"] = {
        "schema_version": 1,
        "planned": {
            "status": "recorded",
            "identities": identities,
            "bundle_digest": digest,
        },
        "resolved": {
            "status": "recorded",
            "identities": identities,
            "bundle_digest": digest,
        },
        "observed": {
            "evidence_level": "exact",
            "source": "host-telemetry",
            "identities": identities,
            "bundle_digest": digest,
            "evidence": "host recorded injected semantic guidance bundle",
        },
    }
    return receipt


class ContextReceiptTests(unittest.TestCase):
    def test_semantic_guidance_identity_and_digest_are_validated(self) -> None:
        receipt = with_semantic_guidance(exact_receipt())
        self.assertEqual(
            validate_context_receipt(receipt, require_semantic_guidance=True), []
        )

    def test_semantic_guidance_digest_preserves_identity_order(self) -> None:
        first = semantic_identity("guidance-001")
        second = semantic_identity("guidance-002")
        self.assertNotEqual(
            semantic_guidance_bundle_digest([first, second]),
            semantic_guidance_bundle_digest([second, first]),
        )

    def test_semantic_guidance_digest_mismatch_is_rejected(self) -> None:
        receipt = with_semantic_guidance(exact_receipt())
        receipt["semantic_guidance"]["resolved"]["bundle_digest"]["value"] = "0" * 64
        failures = validate_context_receipt(receipt, require_semantic_guidance=True)
        self.assertTrue(any("ordered identities" in failure for failure in failures))

    def test_provider_usage_alone_is_not_exact_semantic_delivery_evidence(self) -> None:
        receipt = with_semantic_guidance(exact_receipt())
        receipt["semantic_guidance"]["observed"]["source"] = "provider-usage"
        failures = validate_context_receipt(receipt, require_semantic_guidance=True)
        self.assertTrue(any("host delivery telemetry" in failure for failure in failures))

    def test_unavailable_semantic_stage_requires_unavailable_digest(self) -> None:
        receipt = with_semantic_guidance(exact_receipt())
        receipt["measurement_state"] = "planned"
        receipt["semantic_guidance"]["resolved"] = {
            "status": "unavailable",
            "identities": [],
            "bundle_digest": semantic_guidance_bundle_digest([]),
        }
        receipt["semantic_guidance"]["observed"] = {
            "evidence_level": "unavailable",
            "source": "unavailable",
            "identities": [],
            "bundle_digest": {
                "schema_version": 1,
                "algorithm": "sha256",
                "value": "unavailable",
            },
            "evidence": "host does not expose semantic delivery evidence",
        }
        failures = validate_context_receipt(receipt, require_semantic_guidance=True)
        self.assertTrue(any("value must be unavailable" in failure for failure in failures))

    def test_resolved_guidance_requires_owner_digest(self) -> None:
        receipt = with_semantic_guidance(exact_receipt())
        receipt["semantic_guidance"]["resolved"]["identities"][0]["owner_digest"] = "unknown"
        receipt["semantic_guidance"]["resolved"]["bundle_digest"] = (
            semantic_guidance_bundle_digest(
                receipt["semantic_guidance"]["resolved"]["identities"]
            )
        )
        failures = validate_context_receipt(receipt, require_semantic_guidance=True)
        self.assertTrue(any("owner_digest must be resolved" in failure for failure in failures))

    def test_legacy_receipt_remains_valid_but_cannot_meet_semantic_requirement(self) -> None:
        receipt = exact_receipt()
        self.assertEqual(validate_context_receipt(receipt), [])
        failures = validate_context_receipt(receipt, require_semantic_guidance=True)
        self.assertIn("context_receipt.semantic_guidance must be recorded", failures)

    def test_exact_host_receipt_supports_observed_claim(self) -> None:
        receipt = exact_receipt()
        self.assertEqual(validate_context_receipt(receipt), [])
        self.assertTrue(supports_observed_context_claim(receipt))

    def test_planned_only_receipt_cannot_support_observed_claim(self) -> None:
        receipt = exact_receipt()
        receipt["measurement_state"] = "planned"
        receipt["resolved"] = {
            "status": "unavailable",
            "paths": [],
            "approximate_words": "unknown",
        }
        receipt["observed"] = {
            "evidence_level": "unavailable",
            "source": "unavailable",
            "files_loaded": "unknown",
            "input_tokens": "unknown",
            "output_tokens": "unknown",
            "evidence": "client exposes no telemetry",
        }
        self.assertEqual(validate_context_receipt(receipt), [])
        self.assertFalse(supports_observed_context_claim(receipt))

    def test_assistant_reported_tokens_are_not_exact_telemetry(self) -> None:
        receipt = exact_receipt()
        receipt["observed"] = copy.deepcopy(receipt["observed"])
        receipt["observed"]["source"] = "assistant-reported"
        failures = validate_context_receipt(receipt)
        self.assertTrue(any("exact evidence" in failure for failure in failures))
        self.assertFalse(supports_observed_context_claim(receipt))

    def test_context_paths_cannot_escape_repository(self) -> None:
        receipt = exact_receipt()
        receipt["planned"] = {"paths": ["../secret"], "approximate_words": 1}
        failures = validate_context_receipt(receipt)
        self.assertTrue(any("safe relative paths" in failure for failure in failures))

    def test_planned_receipts_do_not_enable_context_comparison(self) -> None:
        receipt = exact_receipt()
        receipt["measurement_state"] = "planned"
        receipt["resolved"] = {
            "status": "unavailable",
            "paths": [],
            "approximate_words": "unknown",
        }
        receipt["observed"] = {
            "evidence_level": "unavailable",
            "source": "unavailable",
            "files_loaded": "unknown",
            "input_tokens": "unknown",
            "output_tokens": "unknown",
            "evidence": "telemetry unavailable",
        }
        reports = []
        for mode in ["none", "minimal", "full"]:
            reports.append(
                {
                    "adapter_mode": mode,
                    "outcome": "accepted",
                    "context_receipt": receipt,
                    "context_measurement_kind": "planned-words",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "estimated_cost": "unknown",
                    "cost_currency": "unknown",
                    "cost_evidence": "unknown",
                    "context_files_loaded": 1,
                    "approximate_context_volume": 100,
                    "context_expansions": 0,
                    "clarifications": 0,
                    "approvals_requested": 0,
                    "hallucinated_command_count": 0,
                    "validation_error_count": 0,
                    "missed_companion_updates": 0,
                    "rework_count": 0,
                    "changed_fact_count": 0,
                    "relationships_reviewed": 0,
                    "companion_surfaces_checked": 0,
                    "unresolved_consistency_gaps": 0,
                    "duration_seconds": 1,
                    "protected_changes_blocked": 0,
                    "acceptance_criteria_results": [{"status": "pass"}],
                }
            )
        summary = render_summary(
            {
                "benchmark_id": "planned-only",
                "source_commit": "source",
                "tasks": [{"id": "task"}],
                "repetitions": 1,
                "expected_report_count": 3,
            },
            reports,
        )
        self.assertIn("Comparable context-cost evidence: no", summary)
        self.assertIn("Comparable token evidence: no", summary)

    def test_codex_runner_preserves_version_two_receipt_layers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            report = {
                "context_receipt": exact_receipt(),
                "context_files_loaded": 2,
            }
            path.write_text(json.dumps(report), encoding="utf-8")

            update_report(
                path,
                manifest={
                    "benchmark_id": "benchmark",
                    "source_commit": "source",
                },
                run={
                    "task_id": "task",
                    "adapter_mode": "minimal",
                    "run_id": "run",
                    "repetition": 1,
                    "project_baseline_hash": "hash",
                },
                task={
                    "name": "Task",
                    "class_id": "class",
                    "task_profile": "docs-local",
                },
                thread_id="thread",
                usage={"input_tokens": 123, "output_tokens": 45},
                started_at="2026-08-25T00:00:00Z",
                completed_at="2026-08-25T00:00:01Z",
                duration_seconds=1,
            )

            updated = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(updated["schema_version"], 2)
            self.assertEqual(updated["context_receipt"]["planned"], report["context_receipt"]["planned"])
            self.assertEqual(updated["context_receipt"]["resolved"], report["context_receipt"]["resolved"])
            self.assertEqual(updated["context_receipt"]["observed"]["source"], "provider-usage")
            self.assertEqual(updated["input_tokens"], 123)


if __name__ == "__main__":
    unittest.main()
