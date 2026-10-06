from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.runtime_observation import runtime_observation_failures  # noqa: E402


def valid_record() -> dict:
    return {
        "schema_version": 1,
        "record_kind": "alatyr-runtime-observation",
        "observation_id": "obs-1",
        "operation_id": "op-1",
        "repository_revision": "abc123",
        "window": {"started_at": "start", "ended_at": "end", "complete": True},
        "events": [
            {
                "id": "runtime-ready",
                "classification": "expected",
                "observed_count": 1,
                "disposition": "resolved",
                "evidence_refs": ["tmp/runtime-summary.json"],
            },
            {
                "id": "terminal-error",
                "classification": "forbidden",
                "observed_count": 0,
                "disposition": "resolved",
                "evidence_refs": ["tmp/runtime-summary.json"],
            },
        ],
        "claims": [
            {
                "id": "runtime-accepted",
                "statement": "bounded runtime acceptance passed",
                "required_event_ids": ["runtime-ready"],
                "contradiction_event_ids": ["terminal-error"],
                "status": "supported",
                "evidence": "runtime-ready=1; terminal-error=0",
            }
        ],
        "recurrence": {
            "candidate": False,
            "signals": ["none"],
            "incident_family_id": "none",
            "disposition": "not-applicable",
        },
        "post_result_validation": {
            "result_revision": "abc123",
            "adapter_validation": "passed",
            "evidence_fresh": True,
        },
        "limitations": ["bounded window only"],
    }


class RuntimeObservationTests(unittest.TestCase):
    def test_valid_record_passes(self) -> None:
        self.assertEqual(runtime_observation_failures(valid_record()), [])

    def test_incomplete_or_contradicted_claim_fails(self) -> None:
        record = valid_record()
        record["window"]["complete"] = False
        record["events"][1]["observed_count"] = 1
        failures = runtime_observation_failures(record)
        self.assertTrue(any("window" in item for item in failures))
        self.assertTrue(any("forbidden event" in item for item in failures))
        self.assertTrue(any("contradictions" in item for item in failures))

    def test_unknown_and_unresolved_events_fail(self) -> None:
        record = valid_record()
        record["events"][0]["classification"] = "unknown"
        record["events"][0]["disposition"] = "unresolved"
        self.assertTrue(any("remains unresolved" in item for item in runtime_observation_failures(record)))

    def test_recurrence_candidate_requires_lineage(self) -> None:
        record = valid_record()
        record["recurrence"] = {
            "candidate": True,
            "signals": ["runtime-contradiction"],
            "incident_family_id": "none",
            "disposition": "unresolved",
        }
        self.assertTrue(any("incident-lineage" in item for item in runtime_observation_failures(record)))

    def test_post_result_revision_and_freshness_are_bound(self) -> None:
        record = valid_record()
        record["post_result_validation"] = {
            "result_revision": "old",
            "adapter_validation": "not-run",
            "evidence_fresh": False,
        }
        failures = runtime_observation_failures(record)
        self.assertEqual(sum("post-result" in item for item in failures), 3)

    def test_zero_is_valid_boundary_for_forbidden_event(self) -> None:
        record = copy.deepcopy(valid_record())
        self.assertFalse(any("forbidden event" in item for item in runtime_observation_failures(record)))


if __name__ == "__main__":
    unittest.main()
