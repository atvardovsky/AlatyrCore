from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from target_adapter_validation.harness_scenarios.common import validator
from target_adapter_validation.project_support_documentation import (
    validate_project_support_documentation,
)


CONTOUR = """# Project Contour

## Project Orientation

Purpose: Example
Primary users or stakeholders: Maintainers
Main architectural areas and owners:
- core -> docs/architecture.md
Primary runtime or business workflows:
- request -> docs/runtime.md
Validation entry points:
- code -> pyproject.toml
Known contradictions, missing facts, or accepted limitations:
- none
"""


def registry(
    authority: str = "accepted",
    applicability: str = "applicable",
    decision_source: str = "docs/decision.md",
    evidence_revision: str = "abc123",
    last_reviewed: str = "2026-09-24",
) -> str:
    return f"""# Source Of Truth Registry

### Fact Type: `business rule`

Fact type: `business rule`
Applicability state: `{applicability}`
Authority state: `{authority}`
Decision source: `{decision_source}`
Evidence revision: `{evidence_revision}`
Last reviewed: `{last_reviewed}`
Gap severity: `none`
Canonical owner: `docs/business.md`
Consistency level: `fact`
Project area: `billing`
Consistency map node: `fact.business`
Relationship coverage: `mapped`
"""


def compact_registry(
    authority: str = "accepted",
    applicability: str = "applicable",
    decision_source: str = "docs/decision.md",
) -> str:
    return f"""# Source Of Truth Registry

### Fact Type: `business rule`

Fact type: `business rule`
Authority: applicability=`{applicability}`; state=`{authority}`; decision_source=`{decision_source}`; evidence_revision=`abc123`; reviewed=`2026-09-24`; gap=`none`
Canonical owner: `docs/business.md`
Routing: consistency_level=`fact`; project_area=`billing`; consistency_node=`fact.business`; relationship_coverage=`mapped`
"""


class ProjectSupportDocumentationTests(unittest.TestCase):
    def make_target(self, registry_text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        contour_path = target / ".ai/project/contour.md"
        contour_path.parent.mkdir(parents=True)
        contour_path.write_text(CONTOUR, encoding="utf-8")
        (target / ".ai/project/source-of-truth-registry.md").write_text(
            registry_text, encoding="utf-8"
        )
        return target

    def test_accepted_applicable_entry_passes(self) -> None:
        target = self.make_target(registry())
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertEqual(check.findings, [])

    def test_compact_authority_fields_preserve_acceptance_evidence(self) -> None:
        target = self.make_target(compact_registry())
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertEqual(check.findings, [])

    def test_observed_entry_cannot_claim_canonical_authority(self) -> None:
        target = self.make_target(registry(authority="observed"))
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_AUTHORITY_UNACCEPTED",
            {finding.code for finding in check.findings},
        )

    def test_unknown_applicability_is_rejected(self) -> None:
        target = self.make_target(registry(applicability="unknown"))
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_APPLICABILITY_UNRESOLVED",
            {finding.code for finding in check.findings},
        )

    def test_non_applicable_entry_with_resolved_evidence_passes(self) -> None:
        target = self.make_target(
            registry(authority="not-applicable", applicability="not-applicable")
        )
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertEqual(check.findings, [])

    def test_non_applicable_entry_requires_resolved_decision_source(self) -> None:
        target = self.make_target(
            registry(
                authority="not-applicable",
                applicability="not-applicable",
                decision_source="unknown",
            )
        )
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_EVIDENCE_UNRESOLVED",
            {finding.code for finding in check.findings},
        )

    def test_compact_non_applicable_entry_requires_decision_source(self) -> None:
        target = self.make_target(
            compact_registry(
                authority="not-applicable",
                applicability="not-applicable",
                decision_source="unknown",
            )
        )
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_EVIDENCE_UNRESOLVED",
            {finding.code for finding in check.findings},
        )

    def test_non_applicable_entry_requires_evidence_revision(self) -> None:
        target = self.make_target(
            registry(
                authority="not-applicable",
                applicability="not-applicable",
                evidence_revision="unknown",
            )
        )
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_EVIDENCE_UNRESOLVED",
            {finding.code for finding in check.findings},
        )

    def test_non_applicable_entry_requires_iso_review_date(self) -> None:
        target = self.make_target(
            registry(
                authority="not-applicable",
                applicability="not-applicable",
                last_reviewed="unknown",
            )
        )
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_REVIEW_DATE",
            {finding.code for finding in check.findings},
        )

    def test_non_applicable_entry_requires_matching_authority_state(self) -> None:
        target = self.make_target(registry(applicability="not-applicable"))
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_NOT_APPLICABLE_AUTHORITY",
            {finding.code for finding in check.findings},
        )

    def test_duplicate_fact_type_is_rejected(self) -> None:
        entry = registry()
        duplicate = entry[entry.index("### Fact Type"):]
        target = self.make_target(entry + "\n" + duplicate)
        check = validator(target, validation_phase="acceptance")

        validate_project_support_documentation(
            check.capability_validation_context(), None
        )

        self.assertIn(
            "SOURCE_REGISTRY_FACT_TYPE_DUPLICATE",
            {finding.code for finding in check.findings},
        )


if __name__ == "__main__":
    unittest.main()
