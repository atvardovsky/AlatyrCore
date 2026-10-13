from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from manage_session_presence import build_parser
from session_presence_contract import (
    DEFAULT_PRESENCE, MAX_BYTES, MAX_SESSIONS, decode_json,
    encoded_registry, presence_policy, presence_route, validate_entry, validate_registry,
)


def valid_entry():
    return {"session_uid": str(uuid.uuid4()), "parent_uid": None,
            "worktree": "/project", "task": "Review contract", "scope": ["api"],
            "activity": "reviewing", "started_at": "2026-10-13T10:00:00Z",
            "updated_at": "2026-10-13T10:00:00Z", "version": 1}


class PresenceContractTests(unittest.TestCase):
    def test_default_disabled_and_explicit_policy(self):
        self.assertEqual(presence_policy({}), DEFAULT_PRESENCE)
        policy = {"presence": {**DEFAULT_PRESENCE, "enabled": True}}
        self.assertTrue(presence_route(policy)["enabled"])
        for field in DEFAULT_PRESENCE:
            for invalid in (None, [], {}, 1.5, "unknown"):
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    presence_policy({"presence": {**DEFAULT_PRESENCE, field: invalid}})
        for seconds in (60, 86400):
            self.assertEqual(presence_policy({"presence": {**DEFAULT_PRESENCE, "stale_after_seconds": seconds}})["stale_after_seconds"], seconds)
        for seconds in (True, 59, 86401):
            with self.assertRaises(ValueError):
                presence_policy({"presence": {**DEFAULT_PRESENCE, "stale_after_seconds": seconds}})

    def test_json_rejects_duplicates_nonfinite_depth_and_size(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}', b'NaN', b'Infinity', b'\xff', b'[' * 2000, b' ' * (MAX_BYTES + 1)):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                decode_json(raw)

    def test_every_entry_field_rejects_malformed_json_without_crash(self):
        valid = valid_entry()
        validate_entry(valid)
        for field in valid:
            for invalid in (None, [], {}, True, 1.5, "unknown"):
                if field == "parent_uid" and invalid is None:
                    continue
                if field in ("worktree", "task") and invalid == "unknown":
                    continue
                changed = {**valid, field: invalid}
                with self.subTest(field=field, invalid=invalid), self.assertRaises(ValueError):
                    validate_entry(changed)
        for invalid in (None, [], {}, True, 123):
            with self.assertRaises(ValueError):
                validate_entry({**valid, "scope": [invalid]})

    def test_lengths_count_and_registry_binding_boundaries(self):
        entry = valid_entry()
        validate_entry({**entry, "task": "x" * 240, "scope": [str(i) + "x" * 119 for i in range(8)]})
        for changed in ({"task": "x" * 241}, {"scope": ["x"] * 9}, {"scope": ["x", "x"]}, {"scope": ["x" * 121]}, {"worktree": "x\n"}, {"version": True}, {"schema_version": True}):
            with self.assertRaises(ValueError):
                validate_entry({**entry, **changed})
        sessions = {}
        for _ in range(MAX_SESSIONS):
            item = valid_entry()
            sessions[item["session_uid"]] = item
        registry = {"schema_version": 1, "repository_id": "repo", "sessions": sessions}
        encoded_registry(registry, "repo")
        extra = valid_entry()
        sessions[extra["session_uid"]] = extra
        with self.assertRaises(ValueError):
            validate_registry(registry, "repo")
        registry["sessions"] = {}
        for field, bad in (("schema_version", True), ("repository_id", "other"), ("sessions", [])):
            with self.assertRaises(ValueError):
                validate_registry({**registry, field: bad}, "repo")

    def test_time_order_and_uuid_rules(self):
        entry = valid_entry()
        for changed in ({"updated_at": "2026-10-12T10:00:00Z"}, {"updated_at": "2026-99-13T10:00:00Z"}, {"parent_uid": entry["session_uid"]}, {"session_uid": str(uuid.uuid1())}):
            with self.assertRaises(ValueError):
                validate_entry({**entry, **changed})

    def test_serialized_byte_ceiling_below_at_and_above(self):
        import json
        sessions = {}
        for _ in range(50):
            entry = {**valid_entry(), "worktree": "/", "task": "x", "scope": ["x"]}
            sessions[entry["session_uid"]] = entry
        registry = {"schema_version": 1, "repository_id": "repo", "sessions": sessions}
        remaining = MAX_BYTES - len(encoded_registry(registry, "repo"))
        for entry in sessions.values():
            added = min(remaining, 4095)
            entry["worktree"] += "x" * added
            remaining -= added
        self.assertEqual(remaining, 0)
        self.assertEqual(len(encoded_registry(registry, "repo")), MAX_BYTES)
        flexible = next(entry for entry in sessions.values() if len(entry["worktree"]) < 4096 and len(entry["worktree"]) > 1)
        flexible["worktree"] = flexible["worktree"][:-1]
        self.assertEqual(len(encoded_registry(registry, "repo")), MAX_BYTES - 1)
        flexible["worktree"] += "xx"
        with self.assertRaisesRegex(ValueError, "serialized bytes"):
            encoded_registry(registry, "repo")
        self.assertGreater(len(json.dumps(registry)), MAX_BYTES)

    def test_parser_exact_options_required_values_and_duplicates(self):
        parser = build_parser()
        base = ["--target", ".", "update", "--write", "--session-uid", str(uuid.uuid4()), "--expected-version", "1", "--task", "Review", "--scope", "api"]
        parsed = parser.parse_args(base)
        self.assertEqual(parsed.scope, ["api"])
        import contextlib
        import io
        for changed in (base + ["--expected-version", "2"], base + ["--expected-v", "2"], base[:-1] + ["-h"], base + ["--task=Other"], ["--target", ".", "--target=other", "status"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                parser.parse_args(changed)
            self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
