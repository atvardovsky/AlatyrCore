from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

REVISION = "a" * 40

from target_adapter_validation.runtime_observation import runtime_observation_failures  # noqa: E402
from target_adapter_validation.capability import CapabilityValidationContext  # noqa: E402
from target_adapter_validation.context import TargetRepositoryView  # noqa: E402
from target_adapter_validation.modules import dispatch_capability_checks  # noqa: E402
from validate_target_adapter import Validator  # noqa: E402


def valid_record() -> dict:
    return {
        "schema_version": 1,
        "record_kind": "alatyr-runtime-observation",
        "observation_id": "obs-1",
        "operation_id": "op-1",
        "repository_revision": REVISION,
        "window": {
            "started_at": "2026-10-06T10:00:00+00:00",
            "ended_at": "2026-10-06T10:05:00+00:00",
            "complete": True,
        },
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
            "result_revision": REVISION,
            "adapter_validation_request": "required-current-run",
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
            "adapter_validation_request": "not-requested",
            "evidence_fresh": False,
        }
        failures = runtime_observation_failures(record)
        self.assertEqual(sum("post-result" in item for item in failures), 3)

    def test_missing_revisions_and_window_bounds_fail(self) -> None:
        record = valid_record()
        record.pop("repository_revision")
        record["post_result_validation"].pop("result_revision")
        record["window"] = {"complete": True}
        failures = runtime_observation_failures(record)
        self.assertTrue(any("repository_revision" in item for item in failures))
        self.assertTrue(any("post-result revision" in item for item in failures))
        self.assertTrue(any("window.started_at" in item for item in failures))
        self.assertTrue(any("window.ended_at" in item for item in failures))

    def test_reversed_window_fails(self) -> None:
        record = valid_record()
        record["window"]["started_at"] = "2026-10-06T10:06:00+00:00"
        self.assertTrue(any("must not precede" in item for item in runtime_observation_failures(record)))

    def test_malformed_count_and_references_return_failures(self) -> None:
        record = valid_record()
        record["events"][0]["observed_count"] = "invalid"
        record["claims"][0]["required_event_ids"] = [{}]
        failures = runtime_observation_failures(record)
        self.assertTrue(any("observed_count" in item for item in failures))
        self.assertTrue(any("resolved strings" in item for item in failures))

    def test_zero_is_valid_boundary_for_forbidden_event(self) -> None:
        record = copy.deepcopy(valid_record())
        self.assertFalse(any("forbidden event" in item for item in runtime_observation_failures(record)))


class FindingSink:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []

    def error(self, code: str, message: str, path: str | None = None) -> None:
        self.items.append(("error", code, message))

    def warn(self, code: str, message: str, path: str | None = None) -> None:
        self.items.append(("warning", code, message))

    def info(self, code: str, message: str, path: str | None = None) -> None:
        self.items.append(("info", code, message))


class RuntimeObservationDispatchTests(unittest.TestCase):
    def build_context(
        self, root: Path, sink: FindingSink, git: object | None = None
    ) -> CapabilityValidationContext:
        filesystem = TargetRepositoryView(root)
        if git is None:
            git = type(
                "Git",
                (),
                {
                    "head_revision": lambda self: REVISION,
                    "resolve_ref": lambda self, value: value if isinstance(value, str) else None,
                    "is_ancestor": lambda self, base, head: base == head,
                    "changed_files": lambda self, base: [],
                    "range_changed_files": lambda self, base, head: [],
                },
            )()
        return CapabilityValidationContext(
            filesystem=filesystem,
            git=git,  # type: ignore[arg-type]
            findings=sink,
            allow_placeholders=False,
            resolve_target_path=lambda value: root / value,
            read_target_text=lambda path: path.read_text(encoding="utf-8"),
            load_target_json_object=lambda path, _prefix: json.loads(path.read_text(encoding="utf-8")),
            check_target_reference=lambda *_args: None,
            check_action_modes=lambda *_args: None,
            relative_target_path=lambda path: path.relative_to(root).as_posix(),
            module_enabled=lambda *_args: True,
        )

    def build_target(self, root: Path, *, required: bool, record: dict | None) -> None:
        files = {
            ".ai/project/runtime-observation-policy.json": {
                "schema_version": 1,
                "policy_kind": "target-runtime-observation-policy",
                "state": "enabled",
                "owner": "platform-team",
                "last_reviewed": "2026-10-06",
                "evidence_revision": REVISION,
                "collection": {
                    "commands": ["collect-runtime-summary"],
                    "sources": ["runtime-event-stream"],
                    "default_window": "five minutes",
                    "max_compact_events": 20,
                    "max_samples_per_event": 2,
                    "raw_evidence_loading": "on-failure-or-explicit-review",
                },
                "event_catalog": [
                    {
                        "id": "runtime-ready",
                        "meaning": "runtime reached ready state",
                        "default_classification": "expected",
                        "owner": "platform-team",
                    },
                    {
                        "id": "terminal-error",
                        "meaning": "runtime emitted terminal error",
                        "default_classification": "forbidden",
                        "owner": "platform-team",
                    },
                ],
                "redaction_policy": "remove secrets",
                "retention_policy": "target policy",
                "live_access_requires_approval": True,
            },
        }
        for relpath, data in files.items():
            path = root / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
        for relpath in [
            ".ai/project/runtime-observations/records/README.md",
            ".ai/assistant/flows/runtime-observation.flow.md",
            ".ai/assistant/gates/runtime-observation.md",
            ".ai/assistant/templates/runtime-observation-record.json",
            ".ai/framework/runtime-observation.md",
        ]:
            path = root / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        record_relpath = ".ai/project/runtime-observations/records/current.json"
        record_digest = None
        if record is not None:
            path = root / record_relpath
            rendered = json.dumps(record)
            path.write_text(rendered, encoding="utf-8")
            record_digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        index = {
            "schema_version": 1,
            "index_kind": "target-runtime-observation-index",
            "required_for_current_change": required,
            "current_operation_id": "op-1" if record is not None else "none",
            "current_records": [
                {
                    "operation_id": "op-1",
                    "record_path": record_relpath,
                    "sha256": record_digest,
                }
            ] if record is not None else [],
        }
        path = root / ".ai/project/runtime-observations/index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(index), encoding="utf-8")

    def test_registered_dispatch_rejects_invalid_selected_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = valid_record()
            record["events"][1]["observed_count"] = 1
            record["post_result_validation"]["evidence_fresh"] = False
            self.build_target(root, required=True, record=record)
            sink = FindingSink()
            context = self.build_context(root, sink)

            class Validator:
                def capability_validation_context(self) -> CapabilityValidationContext:
                    return context

            dispatch_capability_checks(Validator(), ["runtime-observation"], None)
        codes = [code for level, code, _message in sink.items if level == "error"]
        self.assertIn("RUNTIME_OBSERVATION_RECORD_INVALID", codes)

    def test_registered_dispatch_rejects_required_missing_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_target(root, required=True, record=None)
            sink = FindingSink()
            context = self.build_context(root, sink)

            class Validator:
                def capability_validation_context(self) -> CapabilityValidationContext:
                    return context

            dispatch_capability_checks(Validator(), ["runtime-observation"], None)
        self.assertIn(
            "RUNTIME_OBSERVATION_REQUIRED_MISSING",
            [code for level, code, _message in sink.items if level == "error"],
        )

    def test_registered_dispatch_accepts_valid_selected_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_target(root, required=True, record=valid_record())
            sink = FindingSink()
            context = self.build_context(root, sink)

            class Validator:
                def capability_validation_context(self) -> CapabilityValidationContext:
                    return context

            dispatch_capability_checks(Validator(), ["runtime-observation"], None)
        self.assertEqual(
            [item for item in sink.items if item[0] == "error"],
            [],
        )

    def test_registered_dispatch_binds_digest_catalog_and_head(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = valid_record()
            record["repository_revision"] = "b" * 40
            record["post_result_validation"]["result_revision"] = "b" * 40
            record["events"][0]["id"] = "not-in-policy"
            self.build_target(root, required=True, record=record)
            index_path = root / ".ai/project/runtime-observations/index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["current_records"][0]["sha256"] = "0" * 64
            index_path.write_text(json.dumps(index), encoding="utf-8")
            sink = FindingSink()
            context = self.build_context(root, sink)

            class Validator:
                def capability_validation_context(self) -> CapabilityValidationContext:
                    return context

            dispatch_capability_checks(Validator(), ["runtime-observation"], None)
        codes = [code for level, code, _message in sink.items if level == "error"]
        self.assertIn("RUNTIME_RECORD_DIGEST_MISMATCH", codes)
        self.assertIn("RUNTIME_RECORD_REVISION_STALE", codes)
        self.assertIn("RUNTIME_OBSERVATION_RECORD_INVALID", codes)

    def test_changed_scope_selects_concrete_runtime_record_path(self) -> None:
        validator = Validator.__new__(Validator)
        validator.validation_scope = "changed"
        validator.diff_ref = "HEAD"
        validator.capability_modules = {
            "runtime-observation": {
                "module_kind": "governance-support",
                "target_files": [],
                "change_path_prefixes": [
                    ".ai/project/runtime-observations/records/"
                ],
                "requires": [],
            }
        }
        validator.git = type(
            "Git",
            (),
            {
                "changed_files": lambda self, _ref: [
                    ".ai/project/runtime-observations/records/current.json"
                ]
            },
        )()
        validator.info = lambda *_args: None
        self.assertEqual(
            validator.changed_scope_modules({"runtime-observation"}),
            {"runtime-observation"},
        )

    def test_revision_binding_allows_only_evidence_delta(self) -> None:
        for changed_paths, expect_stale in [
            ([".ai/project/runtime-observations/index.json"], False),
            (["src/runtime.py"], True),
        ]:
            with self.subTest(changed_paths=changed_paths):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    record = valid_record()
                    base_revision = "b" * 40
                    head_revision = "c" * 40
                    record["repository_revision"] = base_revision
                    record["post_result_validation"]["result_revision"] = base_revision
                    self.build_target(root, required=True, record=record)
                    sink = FindingSink()
                    git = type(
                        "Git",
                        (),
                        {
                            "head_revision": lambda self: head_revision,
                            "resolve_ref": lambda self, value: value,
                            "is_ancestor": lambda self, base, head: True,
                            "changed_files": lambda self, base: changed_paths,
                            "range_changed_files": lambda self, base, head: changed_paths,
                        },
                    )()
                    context = self.build_context(root, sink, git)

                    class Validator:
                        def capability_validation_context(self) -> CapabilityValidationContext:
                            return context

                    dispatch_capability_checks(
                        Validator(), ["runtime-observation"], None
                    )
                stale = any(
                    code == "RUNTIME_RECORD_REVISION_STALE"
                    for level, code, _message in sink.items
                    if level == "error"
                )
                self.assertEqual(stale, expect_stale)

    def test_mutable_revision_ref_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = valid_record()
            record["repository_revision"] = "HEAD"
            record["post_result_validation"]["result_revision"] = "HEAD"
            self.build_target(root, required=True, record=record)
            sink = FindingSink()
            git = type(
                "Git",
                (),
                {
                    "head_revision": lambda self: REVISION,
                    "resolve_ref": lambda self, value: REVISION,
                    "is_ancestor": lambda self, base, head: True,
                    "changed_files": lambda self, base: [],
                    "range_changed_files": lambda self, base, head: [],
                },
            )()
            context = self.build_context(root, sink, git)

            class Validator:
                def capability_validation_context(self) -> CapabilityValidationContext:
                    return context

            dispatch_capability_checks(Validator(), ["runtime-observation"], None)
        codes = [code for level, code, _message in sink.items if level == "error"]
        self.assertIn("RUNTIME_RECORD_REVISION_UNVERIFIED", codes)
        self.assertIn("RUNTIME_OBSERVATION_RECORD_INVALID", codes)


if __name__ == "__main__":
    unittest.main()
