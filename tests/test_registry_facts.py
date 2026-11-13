from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from registry_facts import parse_registry_fact_entries, registry_route_health
from target_adapter_validation import consistency_map
from tests.test_project_support_documentation import registry, compact_registry, CONTOUR
from target_adapter_validation.harness_scenarios.common import validator
from target_adapter_validation.project_support_documentation import validate_project_support_documentation
import tempfile


class RegistryFactsTests(unittest.TestCase):
    def test_existing_map_consumers_use_the_identical_parser(self):
        self.assertIs(parse_registry_fact_entries, consistency_map.parse_registry_fact_entries)

    def test_long_compact_and_short_alias_fields_have_equal_meaning(self):
        long = parse_registry_fact_entries(registry())[0]
        compact = parse_registry_fact_entries(compact_registry())[0]
        short = compact_registry()
        for full, alias in (("applicability", "ap"), ("state", "st"), ("decision_source", "ds"),
                            ("evidence_revision", "er"), ("reviewed", "at"), ("gap", "gs"),
                            ("consistency_level", "cl"), ("project_area", "pa"),
                            ("consistency_node", "cn"), ("relationship_coverage", "rc")):
            short = short.replace(full + "=", alias + "=")
        self.assertEqual(long.fields, compact.fields)
        self.assertEqual(long.fields, parse_registry_fact_entries(short)[0].fields)
        self.assertEqual((), long.conflicts)
        self.assertEqual((), compact.conflicts)

    def test_empty_scalar_cannot_consume_the_next_field(self):
        entry = parse_registry_fact_entries(registry().replace("Authority state: `accepted`", "Authority state:"))[0]
        self.assertIsNone(entry.fields["Authority state"])
        self.assertEqual("docs/decision.md", entry.fields["Decision source"])

    def test_repeated_or_conflicting_representations_do_not_silently_win(self):
        for extra in ("Authority state: `observed`", "Authority: st=`observed`", "Fact type: `business rule`",
                      "Routing: cn=`another`", "Authority: st=`accepted`; st=`accepted`"):
            with self.subTest(extra=extra):
                self.assertTrue(parse_registry_fact_entries(compact_registry() + extra + "\n")[0].conflicts)

    def test_redundant_equal_long_and_compact_value_is_not_a_conflict(self):
        entry = parse_registry_fact_entries(compact_registry() + "Authority state: `accepted`\n")[0]
        self.assertEqual((), entry.conflicts)

    def test_deferred_coverage_does_not_override_authority_or_applicability(self):
        for node in ("deferred", "not-applicable:consistency-map deferred", "unknown", "not-installed"):
            text = registry().replace("`fact.business`", "`" + node + "`").replace("`mapped`", "`deferred`")
            with self.subTest(node=node):
                health = registry_route_health(parse_registry_fact_entries(text)[0])
                self.assertEqual("applicable", health["applicability"])
                self.assertEqual("accepted", health["authority"])
                self.assertEqual("unavailable", health["mapping"])
                self.assertEqual("not-established-by-registry-metadata", health["source_freshness"])

    def test_node_names_are_not_coverage_state_tokens(self):
        for node in ("deferred", "disabled", "missing", "not-installed", "node:deferred"):
            text = registry().replace("`fact.business`", "`" + node + "`")
            with self.subTest(node=node):
                health = registry_route_health(parse_registry_fact_entries(text)[0])
                self.assertEqual("mapped", health["relationship_coverage"])
                self.assertEqual("declared-not-verified", health["mapping"])

    def test_registered_project_support_validator_reports_ambiguous_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".ai/project").mkdir(parents=True)
            (target / ".ai/project/contour.md").write_text(CONTOUR, encoding="utf-8")
            (target / ".ai/project/source-of-truth-registry.md").write_text(
                compact_registry() + "Authority state: `observed`\n", encoding="utf-8")
            check = validator(target, validation_phase="acceptance")
            validate_project_support_documentation(check.capability_validation_context(), None)
            self.assertIn("SOURCE_REGISTRY_DECLARATION_CONFLICT", [finding.code for finding in check.findings])

    def test_double_backtick_fact_is_not_normalized_differently_by_consumers(self):
        text = registry().replace("Fact type: `business rule`", "Fact type: ``business rule``")
        self.assertEqual("`business rule`", parse_registry_fact_entries(text)[0].declared_fact_type)
        self.assertEqual(parse_registry_fact_entries(text), consistency_map.parse_registry_fact_entries(text))


if __name__ == "__main__":
    unittest.main()
