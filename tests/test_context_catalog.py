from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from context_catalog import (
    CatalogItem,
    ContextCatalogError,
    build_context_packet,
    catalog_content_bytes,
    file_digest,
    load_codebook,
    validate_context_catalog,
    word_count,
)
from render_context_catalogs import (
    build_directory_catalog_contents,
    build_framework_catalog_contents,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def entry(root: Path, item_id: str, kind: str, path: str) -> dict[str, object]:
    target = root / path
    return {
        "id": item_id,
        "kind": kind,
        "path": path,
        "summary": item_id,
        "selectors": {"tasks": ["test"]},
        "load_when": ["selected by test"],
        "semantic_refs": [],
        "owner_refs": [],
        "estimated_words": word_count(target),
        "content_digest": file_digest(target),
    }


class ContextCatalogTests(unittest.TestCase):
    def test_generated_json_catalog_content_ignores_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "entry-packet.json"
            second = root / "nested" / "entry-packet.json"
            write_json(
                first,
                {
                    "packet_kind": "target-agent-entry-packet",
                    "value": {"stable": True},
                    "generated_by": {"source_dirty_paths": ["first.md"]},
                },
            )
            write_json(
                second,
                {
                    "packet_kind": "target-agent-entry-packet",
                    "value": {"stable": True},
                    "generated_by": {"source_dirty_paths": ["second.md"]},
                },
            )

            self.assertEqual(catalog_content_bytes(first), catalog_content_bytes(second))
            self.assertEqual(file_digest(first), file_digest(second))
            self.assertEqual(word_count(first), word_count(second))

    def test_non_generated_json_catalog_content_keeps_provenance_exact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "ordinary.json"
            second = root / "nested" / "ordinary.json"
            write_json(first, {"value": True, "generated_by": {"revision": "a"}})
            write_json(second, {"value": True, "generated_by": {"revision": "b"}})

            self.assertNotEqual(catalog_content_bytes(first), catalog_content_bytes(second))
            self.assertNotEqual(file_digest(first), file_digest(second))

    def test_directory_catalog_normalizes_generated_payload_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "entry-packet.json").write_text(
                "{}\n", encoding="utf-8"
            )
            outputs = build_directory_catalog_contents(
                root,
                "assistant",
                selected_files={"entry-packet.json"},
                content_overrides={
                    "entry-packet.json": json.dumps(
                        {
                            "packet_kind": "target-agent-entry-packet",
                            "stable": True,
                            "generated_by": {"source_dirty_paths": ["one.md"]},
                        },
                        indent=2,
                    )
                    + "\n"
                },
            )
            root_index = json.loads(outputs["context-index.json"])
            entry_digest = root_index["entries"][0]["content_digest"]
            entry_words = root_index["entries"][0]["estimated_words"]
            (root / "entry-packet.json").write_text(
                json.dumps(
                    {
                        "packet_kind": "target-agent-entry-packet",
                        "stable": True,
                        "generated_by": {"source_dirty_paths": ["two.md"]},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(entry_digest, file_digest(root / "entry-packet.json"))
            self.assertEqual(entry_words, word_count(root / "entry-packet.json"))

    def test_assistant_catalog_excludes_generated_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bootstrap-index.json").write_text(
                '{"generated": true}\n', encoding="utf-8"
            )
            (root / "context-router.json").write_text(
                '{"schema_version": 8}\n', encoding="utf-8"
            )
            outputs = build_directory_catalog_contents(root, "assistant")
            root_index = json.loads(outputs["context-index.json"])
            indexed_paths = {entry["path"] for entry in root_index["entries"]}
            self.assertIn("context-router.json", indexed_paths)
            self.assertNotIn("bootstrap-index.json", indexed_paths)

    def test_framework_projection_uses_projected_markdown_title(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root / "rule-registry.json", {"rules": []})
            (root / "README.md").write_text("# Source Title\n", encoding="utf-8")
            outputs = build_framework_catalog_contents(
                {"README.md"},
                {"README.md": "# Projected Title\n"},
                root=root,
            )
            core_index = json.loads(outputs["catalog/core/context-index.json"])
            self.assertEqual(core_index["entries"][0]["summary"], "Projected Title")

    def test_recursive_catalog_resolves_nested_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "areas/payments/rules.md"
            content.parent.mkdir(parents=True)
            content.write_text("payment rule\n", encoding="utf-8")
            child = root / "areas/context-index.json"
            write_json(
                child,
                {
                    "schema_version": 1,
                    "index_kind": "alatyr-context-index",
                    "index_id": "areas",
                    "contour": "project",
                    "title": "Areas",
                    "summary": "Project areas",
                    "max_depth": 4,
                    "entries": [entry(root, "payments", "content", "areas/payments/rules.md")],
                },
            )
            root_index = root / "context-index.json"
            write_json(
                root_index,
                {
                    "schema_version": 1,
                    "index_kind": "alatyr-context-index",
                    "index_id": "root",
                    "contour": "project",
                    "title": "Root",
                    "summary": "Root index",
                    "max_depth": 4,
                    "entries": [entry(root, "areas-index", "index", "areas/context-index.json")],
                },
            )
            result = validate_context_catalog(root_index)
            self.assertEqual([item.path for item in result.items], ["areas/payments/rules.md"])

    def test_context_catalog_inherits_entry_default_load_when(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "rule.md"
            content.write_text("rule\n", encoding="utf-8")
            item = entry(root, "rule", "content", "rule.md")
            item.pop("load_when")
            index = root / "context-index.json"
            write_json(
                index,
                {
                    "schema_version": 1,
                    "index_kind": "alatyr-context-index",
                    "index_id": "root",
                    "contour": "framework",
                    "title": "Root",
                    "summary": "Root",
                    "max_depth": 2,
                    "entry_defaults": {"load_when": ["selected by default"]},
                    "entries": [item],
                },
            )

            result = validate_context_catalog(index)

            self.assertEqual(result.items[0].load_when, ("selected by default",))

    def test_context_catalog_rejects_missing_load_when_without_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "rule.md"
            content.write_text("rule\n", encoding="utf-8")
            item = entry(root, "rule", "content", "rule.md")
            item.pop("load_when")
            index = root / "context-index.json"
            write_json(
                index,
                {
                    "schema_version": 1,
                    "index_kind": "alatyr-context-index",
                    "index_id": "root",
                    "contour": "framework",
                    "title": "Root",
                    "summary": "Root",
                    "max_depth": 2,
                    "entries": [item],
                },
            )

            with self.assertRaisesRegex(ContextCatalogError, "entry_defaults"):
                validate_context_catalog(index)

    def test_recursive_catalog_rejects_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "context-index.json"
            second = root / "child.json"
            first.write_text("{}", encoding="utf-8")
            second.write_text("{}", encoding="utf-8")
            base = {
                "schema_version": 1,
                "index_kind": "alatyr-context-index",
                "contour": "framework",
                "title": "Index",
                "summary": "Index",
                "max_depth": 4,
            }
            write_json(first, {**base, "index_id": "first", "entries": [entry(root, "second", "index", "child.json")]})
            write_json(second, {**base, "index_id": "second-index", "entries": [entry(root, "first-entry", "index", "context-index.json")]})
            # Refresh the first digest after writing its referenced child; the cycle is
            # detected before stale recursive digests can become relevant.
            first_data = json.loads(first.read_text())
            first_data["entries"][0] = entry(root, "second", "index", "child.json")
            write_json(first, first_data)
            with self.assertRaisesRegex(ContextCatalogError, "cycle"):
                validate_context_catalog(first, verify_content=False)

    def test_catalog_rejects_stale_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / "rule.md"
            content.write_text("rule\n", encoding="utf-8")
            item = entry(root, "rule", "content", "rule.md")
            item["content_digest"] = "sha256:" + "0" * 64
            index = root / "context-index.json"
            write_json(index, {
                "schema_version": 1,
                "index_kind": "alatyr-context-index",
                "index_id": "root",
                "contour": "framework",
                "title": "Root",
                "summary": "Root",
                "max_depth": 2,
                "entries": [item],
            })
            with self.assertRaisesRegex(ContextCatalogError, "digest"):
                validate_context_catalog(index)

    def test_codebook_loads_preload_and_dependency_closure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard = root / "core.json"
            terms = [
                {
                    "id": "alatyr:owner",
                    "version": 1,
                    "definition": "Read the canonical owner.",
                    "owner_rule_id": "ALATYR-SOURCE-001",
                    "canonical_owner": "framework/source.md",
                    "scope": "all tasks",
                    "non_meanings": [],
                    "depends_on": [],
                    "replaced_by": None,
                },
                {
                    "id": "alatyr:integrity",
                    "version": 1,
                    "definition": "Review changed facts and dependent surfaces.",
                    "owner_rule_id": "ALATYR-INTEGRITY-001",
                    "canonical_owner": "framework/integrity.md",
                    "scope": "semantic changes",
                    "non_meanings": [],
                    "depends_on": ["alatyr:owner"],
                    "replaced_by": None,
                },
            ]
            write_json(shard, {"schema_version": 1, "record_kind": "alatyr-semantic-codebook-shard", "shard_id": "core", "preload": False, "selectors": {"tasks": ["test"]}, "terms": terms})
            index = root / "index.json"
            write_json(index, {
                "schema_version": 1,
                "index_kind": "alatyr-semantic-codebook-index",
                "codebook_id": "test",
                "shards": [{
                    "id": "core",
                    "path": "core.json",
                    "preload": False,
                    "selectors": {"tasks": ["test"]},
                    "term_ids": [term["id"] for term in terms],
                    "content_digest": file_digest(shard),
                }],
            })
            resolved = load_codebook(index, required_terms=["alatyr:integrity"])
            self.assertEqual(list(resolved), ["alatyr:owner", "alatyr:integrity"])

            selected = load_codebook(index, selectors={"tasks": "test"})
            self.assertEqual(list(selected), ["alatyr:owner", "alatyr:integrity"])

            unselected = load_codebook(index, selectors={"tasks": "other"})
            self.assertEqual(unselected, {})

    def test_codebook_rejects_dependency_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shard = root / "core.json"
            terms = []
            for term_id, dependency in [("alatyr:first", "alatyr:second"), ("alatyr:second", "alatyr:first")]:
                terms.append({
                    "id": term_id,
                    "version": 1,
                    "definition": term_id,
                    "owner_rule_id": "ALATYR-CONTEXT-001",
                    "canonical_owner": "framework/context.md",
                    "scope": "test",
                    "non_meanings": [],
                    "depends_on": [dependency],
                    "replaced_by": None,
                })
            write_json(shard, {"schema_version": 1, "record_kind": "alatyr-semantic-codebook-shard", "shard_id": "core", "preload": True, "selectors": {}, "terms": terms})
            index = root / "index.json"
            write_json(index, {
                "schema_version": 1,
                "index_kind": "alatyr-semantic-codebook-index",
                "codebook_id": "test",
                "shards": [{
                    "id": "core",
                    "path": "core.json",
                    "preload": True,
                    "selectors": {},
                    "term_ids": [term["id"] for term in terms],
                    "content_digest": file_digest(shard),
                }],
            })
            with self.assertRaisesRegex(ContextCatalogError, "cycle"):
                load_codebook(index)

    def test_packet_enforces_budget_and_resolves_terms(self) -> None:
        item = CatalogItem(
            item_id="rule",
            kind="content",
            path="rule.md",
            summary="Rule",
            selectors={},
            load_when=("task match",),
            semantic_refs=("alatyr:owner",),
            owner_refs=("ALATYR-SOURCE-001",),
            estimated_words=10,
            content_digest="sha256:" + hashlib.sha256(b"rule").hexdigest(),
        )
        terms = {
            "alatyr:owner": {
                "version": 1,
                "definition": "Read the canonical owner.",
                "canonical_owner": "framework/source.md",
            }
        }
        packet = build_context_packet(
            profile="code-local",
            operation="review",
            selected_items=[item],
            semantic_terms=terms,
            max_words=20,
            selection_reasons={"rule": ["rule-id:ALATYR-SOURCE-001"]},
            task_classification="small-task",
            expansion_triggers=["owner conflict"],
            omitted_item_ids=["unrelated"],
        )
        self.assertEqual(packet["budget"]["total_words"], 14)
        self.assertEqual(packet["schema_version"], 2)
        self.assertEqual(
            packet["cache_delivery"]["capability_record"],
            ".ai/assistant/assistant-capabilities/generic.json",
        )
        self.assertFalse(packet["cache_delivery"]["cache_hit_required"])
        self.assertFalse(packet["cache_delivery"]["context_window_reduction"])
        self.assertEqual(packet["selected_items"][0]["reason"], ["rule-id:ALATYR-SOURCE-001"])
        self.assertEqual(packet["routing"]["omitted_item_ids"], ["unrelated"])
        self.assertEqual(packet["receipt"]["planned"]["approximate_words"], 14)
        schema = json.loads(
            (ROOT / "schemas/alatyr-context-packet.schema.json").read_text(
                encoding="utf-8"
            )
        )
        jsonschema.validate(packet, schema)
        self.assertRegex(
            packet["cache_delivery"]["stable_prefix_digest"],
            r"^sha256:[0-9a-f]{64}$",
        )
        with self.assertRaisesRegex(ContextCatalogError, "exceeds budget"):
            build_context_packet(
                profile="code-local",
                operation="review",
                selected_items=[item],
                semantic_terms=terms,
                max_words=13,
            )

    def test_packet_cache_prefix_is_order_independent_and_surface_specific(self) -> None:
        terms = {
            "alatyr:second": {
                "version": 1,
                "definition": "Second stable definition.",
                "canonical_owner": "framework/second.md",
            },
            "alatyr:first": {
                "version": 1,
                "definition": "First stable definition.",
                "canonical_owner": "framework/first.md",
            },
        }
        first = build_context_packet(
            profile="docs-local",
            operation="review",
            selected_items=[],
            semantic_terms=terms,
            max_words=20,
            assistant_surface="codex",
        )
        second = build_context_packet(
            profile="docs-local",
            operation="review",
            selected_items=[],
            semantic_terms=dict(reversed(list(terms.items()))),
            max_words=20,
            assistant_surface="codex",
        )

        self.assertEqual(first["semantic_terms"], second["semantic_terms"])
        self.assertEqual(
            first["cache_delivery"]["stable_prefix_digest"],
            second["cache_delivery"]["stable_prefix_digest"],
        )
        self.assertEqual(
            first["cache_delivery"]["capability_record"],
            ".ai/assistant/assistant-capabilities/codex.json",
        )


if __name__ == "__main__":
    unittest.main()
