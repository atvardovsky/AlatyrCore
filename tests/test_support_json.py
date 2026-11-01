from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from support_json import (
    BYTE_REVIEW_LIMIT, COLLECTION_LIMIT, DEFAULT_VIEW_BYTES, MAX_SOURCE_BYTES,
    MAX_VIEW_BYTES, build_parser, build_view, encoded, verify_view,
)


def source_report() -> dict:
    return {
        "schema_version": 3, "report_kind": "alatyr-source-check-run", "profile": "full",
        "source": {"source_commit": "a" * 40}, "selection": {"validation_stage": "source"},
        "reuse_contract": {"completed": True, "successful": False},
        "acceptance_evidence": {"eligible": False, "reason": "run-not-successful"},
        "source_write_scope": {"preserved": True, "changes": []},
        "checks": [{"id": "good", "status": "passed", "exit_code": 0, "timed_out": False,
                    "stdout": "large irrelevant history " * 5000},
                   {"id": "bad", "status": "failed", "exit_code": 1, "timed_out": False,
                    "stderr": "actionable diagnostic"}],
    }


class SupportJsonTests(unittest.TestCase):
    def test_exact_selection_hash_and_lossless_roundtrip(self):
        data = {"items": [{"name": "one", "value": [1, True, None]}, {"name": "two"}],
                "large": "word " * 10000, "slash/key": {"~value": "non-ASCII: \u00e9"}}
        raw = encoded(data)
        pointers = ["/items/0", "/slash~1key/~0value"]
        view = build_view(raw, path="support.json", selectors=pointers)
        selected = {row["pointer"]: row["value"] for row in view["selected"]}
        self.assertEqual(selected, {pointers[0]: data["items"][0], pointers[1]: "non-ASCII: \u00e9"})
        self.assertEqual(view["source"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(view["delivery"]["bytes"], len(encoded(view)))
        self.assertGreater(100 * (1 - view["delivery"]["bytes"] / view["source"]["bytes"]), 90)
        self.assertFalse(view["acceptance_granted"])
        verify_view(raw, view, path="support.json")

    def test_no_selection_is_explicit_navigation_not_whole_source(self):
        view = build_view(encoded({"items": [1, 2]}), path="data.json")
        self.assertEqual(view["selected"], [])
        self.assertEqual(view["root_fields"][0]["items"], 2)
        self.assertFalse(view["coverage"]["whole_source_selected"])
        whole = build_view(encoded({"items": [1, 2]}), path="data.json", selectors=[""])
        self.assertTrue(whole["coverage"]["whole_source_selected"])

    def test_missing_malformed_duplicate_and_unbounded_selectors_fail(self):
        raw = encoded({"items": [1]})
        for selector in ("items", "/missing", "/items/-1", "/items/00", "/~2", "/items/1"):
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                build_view(raw, path="data.json", selectors=[selector])
        with self.assertRaisesRegex(ValueError, "unique"):
            build_view(raw, path="data.json", selectors=["/items", "/items"])
        def endless():
            for _ in range(33):
                yield "/items"
            raise AssertionError("consumed beyond selector bound")
        with self.assertRaisesRegex(ValueError, "at most 32"):
            build_view(raw, path="data.json", selectors=endless())

    def test_overlapping_pointers_are_delivered_once(self):
        view = build_view(encoded({"items": [1]}), path="x.json", selectors=["/items/0", "/items"])
        self.assertEqual([row["pointer"] for row in view["selected"]], ["/items"])

    def test_selected_values_match_full_parse_across_pointer_combinations(self):
        from itertools import combinations
        from repair_qualification import pointer_value
        data = {"a": {"b": [None, False, 0, {"x": "exact"}]}, "ab": {"b": []},
                "a/b": {"~": {}}, "": {"0": "empty key"}}
        paths = ["", "/a", "/a/b", "/a/b/0", "/a/b/1", "/a/b/2", "/a/b/3", "/a/b/3/x",
                 "/ab", "/ab/b", "/a~1b", "/a~1b/~0", "/", "//0"]
        raw = encoded(data)
        for requested in combinations(paths, 3):
            view = build_view(raw, path="x.json", selectors=requested)
            verify_view(raw, view, path="x.json")
            for pointer in requested:
                row = next(row for row in view["selected"] if row["pointer"] == pointer
                           or row["pointer"] == "" or pointer.startswith(row["pointer"] + "/"))
                suffix = pointer[len(row["pointer"]):]
                observed = row["value"] if not suffix else pointer_value(row["value"], suffix)
                expected = data if pointer == "" else pointer_value(data, pointer)
                self.assertEqual(encoded(observed), encoded(expected))

    def test_empty_unicode_and_numeric_keys_and_values_are_not_missing(self):
        data = {"": {"0": [None, False, 0, "", [], {}]}, "\u00e9": "exact"}
        view = build_view(encoded(data), path="x.json", selectors=["/", "/\u00e9"])
        self.assertEqual({row["pointer"]: row["value"] for row in view["selected"]},
                         {"/": data[""], "/\u00e9": "exact"})
        for index, value in enumerate(data[""]["0"]):
            selected = build_view(encoded(data), path="x.json", selectors=[f"//0/{index}"])
            self.assertEqual(encoded(selected["selected"][0]["value"]), encoded(value))

    def test_full_envelope_budget_below_at_above_boundary(self):
        raw = encoded({"items": ["x" * 3000]})
        view = build_view(raw, path="x.json", selectors=["/items"], max_bytes=5000)
        limit = view["delivery"]["bytes"]
        at_limit = build_view(raw, path="x.json", selectors=["/items"], max_bytes=limit)
        self.assertEqual(at_limit["delivery"]["bytes"], limit)
        build_view(raw, path="x.json", selectors=["/items"], max_bytes=limit + 1)
        with self.assertRaisesRegex(ValueError, f"requires {limit} bytes; limit is {limit - 1}"):
            build_view(raw, path="x.json", selectors=["/items"], max_bytes=limit - 1)
        for invalid in (None, True, 0, -1, MAX_VIEW_BYTES + 1, "32768", {}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                build_view(raw, path="x.json", max_bytes=invalid)

    def test_percentage_rounding_boundary_cannot_oscillate_measurement(self):
        # The previous percentage-in-envelope calculation oscillated here.
        raw = b'{"x":1}' + b" " * (1274 - 7)
        view = build_view(raw, path="x.json")
        self.assertEqual(view["delivery"]["bytes"], len(encoded(view)))
        for size in range(1200, 1350):
            raw = b'{"x":1}' + b" " * (size - 7)
            view = build_view(raw, path="x.json")
            self.assertEqual(view["delivery"]["bytes"], len(encoded(view)))

    def test_malformed_json_rejected_without_ambiguous_values(self):
        for raw in (b'[]', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'\xff', b'{'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                build_view(raw, path="x.json")
        with self.assertRaises(ValueError):
            build_view(b" " * (MAX_SOURCE_BYTES + 1), path="x.json")

    def test_numeric_selection_never_silently_rounds_or_underflows(self):
        from source_context_selection import source_json
        for number in ("0.1000000000000000000000001", "1e-400", "12345678901234567890.5"):
            raw = ('{"value":' + number + '}').encode()
            with self.subTest(number=number), self.assertRaisesRegex(ValueError, "precision loss"):
                build_view(raw, path="x.json", selectors=["/value"])
            # Existing source consumers keep their established parser policy.
            self.assertIsInstance(source_json(raw.decode())["value"], float)
        for number in ("0.1", "-0.0", "1e100", "1.2345678901234567"):
            raw = ('{"value":' + number + '}').encode()
            view = build_view(raw, path="x.json", selectors=["/value"])
            verify_view(raw, view, path="x.json")
        raw = b'{"value":1e-999999999999999999999}'
        with self.assertRaisesRegex(ValueError, "decimal representation"):
            build_view(raw, path="x.json")
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "number.json").write_bytes(raw)
            completed = subprocess.run([sys.executable, str(ROOT / "tools/alatyr.py"),
                                        "support-json", "--target", directory, "--path", "number.json"], capture_output=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(b"decimal representation", completed.stderr)
            self.assertNotIn(b"Traceback", completed.stderr)

    def test_source_and_root_field_ceiling_boundaries(self):
        for size in (MAX_SOURCE_BYTES - 1, MAX_SOURCE_BYTES, MAX_SOURCE_BYTES + 1):
            raw = b'{"text":"' + b"x" * (size - 12) + b'"}\n'
            if size <= MAX_SOURCE_BYTES:
                view = build_view(raw, path="x.json")
                self.assertEqual(view["source"]["bytes"], size)
            else:
                with self.assertRaises(ValueError):
                    build_view(raw, path="x.json")
        for count in (COLLECTION_LIMIT - 1, COLLECTION_LIMIT, COLLECTION_LIMIT + 1):
            raw = encoded({str(index): None for index in range(count)})
            if count <= COLLECTION_LIMIT:
                self.assertEqual(len(build_view(raw, path="x.json")["root_fields"]), count)
            else:
                with self.assertRaisesRegex(ValueError, "root fields"):
                    build_view(raw, path="x.json")

    def test_deep_input_and_saved_view_types_fail_explicitly(self):
        from support_json import MAX_DEPTH
        for depth in (MAX_DEPTH - 1, MAX_DEPTH, MAX_DEPTH + 1):
            data = None
            for _ in range(depth - 1):
                data = [data]
            if depth <= MAX_DEPTH:
                build_view(encoded({"x": data}), path="x.json")
            else:
                with self.assertRaisesRegex(ValueError, "nesting"):
                    build_view(encoded({"x": data}), path="x.json")
        with self.assertRaises(ValueError):
            build_view(b'{"x":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}", path="x.json")
        for view in (None, [], {}, {"requested_pointers": {}},
                     {"requested_pointers": [{}], "max_output_bytes": DEFAULT_VIEW_BYTES},
                     {"requested_pointers": [], "max_output_bytes": MAX_VIEW_BYTES + 1}):
            with self.subTest(view=view), self.assertRaises(ValueError):
                verify_view(b"{}", view, path="x.json")

    def test_layout_review_boundaries_are_proposals_not_schema_inference(self):
        for count, expected in ((COLLECTION_LIMIT - 1, "keep-cohesive"),
                                (COLLECTION_LIMIT, "keep-cohesive"),
                                (COLLECTION_LIMIT + 1, "review-collection-boundaries")):
            view = build_view(encoded({"records": [None] * count}), path="x.json")
            self.assertEqual(view["layout"]["disposition"], expected)
        for size in (BYTE_REVIEW_LIMIT - 1, BYTE_REVIEW_LIMIT, BYTE_REVIEW_LIMIT + 1):
            raw = b'{"text":"' + b"x" * (size - 12) + b'"}\n'
            self.assertEqual(len(raw), size)
            view = build_view(raw, path="x.json")
            self.assertEqual(view["layout"]["disposition"], "review-collection-boundaries" if size > BYTE_REVIEW_LIMIT else "keep-cohesive")
        for key, kind, expected in (("index_kind", "target-change-package-index", "use-existing-index"),
                                    ("state_kind", "target-support-state", "project-machine-inventory"),
                                    ("record_kind", "individual-approval", "keep-record-whole"),
                                    ("report_kind", "some-report", "project-report-details"),
                                    ("index_kind", {}, "keep-cohesive")):
            view = build_view(encoded({key: kind, "large": "x" * 70000} if isinstance(kind, str) else {key: kind}), path="x.json")
            self.assertEqual(view["layout"]["disposition"], expected)
            self.assertFalse(view["layout"]["automatic_migration_performed"])

    def test_source_report_never_hides_failed_blocked_unknown_or_malformed_rows(self):
        data = source_report()
        mutations = [data["checks"][1], {"status": "blocked"}, {"status": "unknown"},
                     {"status": {}}, {"status": "passed", "exit_code": True, "timed_out": False},
                     {"status": "passed", "exit_code": 0, "timed_out": True}, None]
        for row in mutations:
            data["checks"][1] = row
            view = build_view(encoded(data), path="report.json")
            selected = {item["pointer"]: item["value"] for item in view["selected"]}
            self.assertEqual(selected["/checks/1"], row)
            self.assertFalse(selected["/acceptance_evidence"]["eligible"])
            self.assertEqual(view["coverage"]["report_check_count"], 2)
            self.assertNotIn("/checks/0", selected)
        data["checks"][1] = {"status": "failed", "stderr": "x" * DEFAULT_VIEW_BYTES}
        with self.assertRaisesRegex(ValueError, "diagnostics were not truncated"):
            build_view(encoded(data), path="report.json")

    def test_required_sibling_diagnostics_are_bounded_before_projection(self):
        data = source_report()
        data["checks"] = [None] * 20000
        with patch("support_json._select", side_effect=AssertionError("projected an oversized view")):
            with self.assertRaisesRegex(ValueError, "diagnostics exceed"):
                build_view(encoded(data), path="report.json")
        view = build_view(encoded(data), path="report.json", selectors=["/checks"], max_bytes=MAX_VIEW_BYTES)
        self.assertEqual(next(row["value"] for row in view["selected"] if row["pointer"] == "/checks"), data["checks"])

    def test_recognized_reports_retain_extra_top_level_diagnostics(self):
        data = source_report()
        data.update({"warnings": ["blocked"], "errors": ["must remain"],
                     "coverage": {"missing": ["required"]}, "limitations": ["partial"]})
        raw = encoded(data)
        view = build_view(raw, path="report.json")
        selected = {row["pointer"]: row["value"] for row in view["selected"]}
        for key in ("warnings", "errors", "coverage", "limitations"):
            self.assertEqual(selected["/" + key], data[key])
        verify_view(raw, view, path="report.json")
        changed = copy.deepcopy(view)
        changed["selected"] = [row for row in changed["selected"] if row["pointer"] != "/warnings"]
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            verify_view(raw, changed, path="report.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "report.json").write_bytes(raw)
            command = [sys.executable, str(ROOT / "tools/alatyr.py"), "support-json", "--target", directory, "--path", "report.json"]
            result = subprocess.run(command, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn({"pointer": "/warnings", "value": ["blocked"]}, json.loads(result.stdout)["selected"])

    def test_target_report_all_diagnostics_and_limits_are_required(self):
        from validate_target_adapter import Finding, findings_payload
        with tempfile.TemporaryDirectory() as directory:
            data = findings_payload([Finding("error", "BLOCKED", "must stay visible")],
                                    target=Path(directory), strict_warnings=False)
        view = build_view(encoded(data), path="report.json", selectors=["/execution"])
        selected = {item["pointer"]: item["value"] for item in view["selected"]}
        self.assertEqual(selected["/findings"], data["findings"])
        self.assertEqual(selected["/placeholder_validation"], data["placeholder_validation"])
        self.assertEqual(selected["/evidence"], data["evidence"])
        for key in ("findings", "validation_scope", "placeholder_validation"):
            missing = dict(data)
            del missing[key]
            with self.assertRaisesRegex(ValueError, "unavailable"):
                build_view(encoded(missing), path="report.json")

    def test_unknown_reports_retain_explicit_diagnostics_without_claiming_semantics(self):
        data = {"report_kind": "other", "status": "incomplete", "errors": ["blocked"],
                "coverage": "partial", "details": {"x": 1}}
        view = build_view(encoded(data), path="report.json", selectors=["/details"])
        self.assertEqual({row["pointer"] for row in view["selected"]}, {"/details", "/status", "/errors", "/coverage"})
        for version in (None, True, {}, 2, 4):
            data = source_report()
            data["schema_version"] = version
            with self.assertRaisesRegex(ValueError, "version"):
                build_view(encoded(data), path="report.json")

    def test_consistency_check_rejects_every_changed_projection_and_source(self):
        raw = encoded({"data": [True, 2], "unselected": "old"})
        view = build_view(raw, path="data.json", selectors=["/data"])
        mutations = [lambda value: value["selected"][0]["value"].__setitem__(0, 1),
                     lambda value: value["source"].__setitem__("sha256", "0" * 64),
                     lambda value: value["delivery"].__setitem__("bytes", 1),
                     lambda value: value.__setitem__("acceptance_granted", True),
                     lambda value: value.__setitem__("extra", "unbound")]
        for mutate in mutations:
            changed = copy.deepcopy(view)
            mutate(changed)
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                verify_view(raw, changed, path="data.json")
        with self.assertRaisesRegex(ValueError, "stale"):
            verify_view(encoded({"data": [True, 2], "unselected": "new"}), view, path="data.json")
        with self.assertRaises(ValueError):
            verify_view(raw, view, path="other.json")

    def test_public_cli_is_read_only_and_checks_views_without_opening_siblings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data.json").write_bytes(encoded({"entries": [1, 2], "shards": [{"path": "missing.json"}]}))
            command = [sys.executable, str(ROOT / "tools/alatyr.py"), "support-json", "--target", directory,
                       "--path", "data.json"]
            before = {path.name: path.read_bytes() for path in root.iterdir()}
            completed = subprocess.run([*command, "--select", "/entries/0"], capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(before, {path.name: path.read_bytes() for path in root.iterdir()})
            (root / "view.json").write_bytes(completed.stdout)
            checked = subprocess.run([*command, "--check", "view.json"], capture_output=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            (root / "data.json").write_bytes(encoded({"entries": [3]}))
            stale = subprocess.run([*command, "--check", "view.json"], capture_output=True)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn(b"stale", stale.stderr)
            for arguments in (["--path", "../outside.json"], ["--select", "/absent"],
                              ["--check", ""],
                              ["--check", "view.json", "--select", "/entries"],
                              ["--max-output-bytes", "1"]):
                bad = subprocess.run([*command, *arguments], capture_output=True)
                self.assertNotEqual(bad.returncode, 0)
                self.assertNotIn(b"Traceback", bad.stderr)

    def test_containment_and_regular_file_guards(self):
        from support_json import read_bytes
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.json").write_text("{}")
            self.assertEqual(read_bytes(root, "source.json", 2), b"{}")
            with self.assertRaises(ValueError):
                read_bytes(root, "source.json", 1)
            for path in ("../source.json", str(root / "source.json"), "missing.json", "."):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    read_bytes(root, path, 10)
            try:
                (root / "link.json").symlink_to(root / "source.json")
            except OSError:
                pass
            else:
                with self.assertRaisesRegex(ValueError, "symlinks"):
                    read_bytes(root, "link.json", 10)
            with patch("support_json.read_regular_context_bytes", return_value=b"{}") as read:
                read_bytes(root, "source.json", 10)
                read.assert_called_once()

    def test_documented_command_arguments_use_live_parser(self):
        import shlex
        text = (ROOT / "tools/README.md").read_text()
        marker = "python3 tools/alatyr.py support-json "
        examples = [line.split(marker, 1)[1].split(" > ", 1)[0]
                    for line in text.splitlines() if line.startswith(marker)]
        self.assertEqual(len(examples), 3)
        for example in examples:
            build_parser().parse_args(shlex.split(example))

    def test_parser_disables_abbreviations(self):
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["--target", ".", "--path", "x.json", "--max-output", "4000"])


if __name__ == "__main__":
    unittest.main()
