from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_target_adapter import AdapterValidatorConfig, Validator  # noqa: E402


class ProjectAgentEntrypointRoutingTests(unittest.TestCase):
    def validator(self, target: Path) -> Validator:
        return Validator(
            target,
            framework_source=None,
            diff_ref=None,
            approval_records=[],
            enforce_approval_scope=False,
            change_packages=[],
            enforce_change_package=False,
            migration_diff=None,
            allow_placeholders=False,
            allow_local_paths=[],
            config=AdapterValidatorConfig(),
        )

    def findings_for(self, text: str | None) -> set[str]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        target = Path(directory.name)
        if text is not None:
            (target / "AGENT.md").write_text(text, encoding="utf-8")
        checked = self.validator(target)
        checked.check_bootstrap_references()
        return {finding.code for finding in checked.findings}

    def test_absent_project_entrypoint_is_allowed(self) -> None:
        self.assertEqual(self.findings_for(None), set())

    def test_compact_project_entrypoint_preserves_local_instructions(self) -> None:
        findings = self.findings_for(
            """# Project instructions

Start with `AGENTS.md` and `.ai/assistant/bootstrap-index.json`.
Preserve the project-specific release checklist below.
"""
        )

        self.assertNotIn("AGENT_CANONICAL_ENTRYPOINT_MISSING", findings)
        self.assertNotIn("BOOTSTRAP_INDEX_REFERENCE_MISSING", findings)
        self.assertNotIn("AGENT_BROAD_PRELOAD", findings)

    def test_project_entrypoint_requires_canonical_and_bootstrap_routes(self) -> None:
        findings = self.findings_for("Read the local project instructions first.\n")

        self.assertIn("AGENT_CANONICAL_ENTRYPOINT_MISSING", findings)
        self.assertIn("BOOTSTRAP_INDEX_REFERENCE_MISSING", findings)

    def test_broad_mandatory_preload_is_rejected(self) -> None:
        findings = self.findings_for(
            """# Project instructions

Read `AGENTS.md`, `.ai/README.md`, `.ai/project/contour.md`, and
`.ai/framework/logical-integrity.md` before every task. Then load
`.ai/assistant/bootstrap-index.json`.
"""
        )

        self.assertIn("AGENT_BROAD_PRELOAD", findings)

    def test_negated_broad_preload_is_not_rejected(self) -> None:
        findings = self.findings_for(
            """# Project instructions

Start with `AGENTS.md` and `.ai/assistant/bootstrap-index.json`.
Do not load or read `.ai/framework` as a directory.
"""
        )

        self.assertNotIn("AGENT_BROAD_PRELOAD", findings)


if __name__ == "__main__":
    unittest.main()
