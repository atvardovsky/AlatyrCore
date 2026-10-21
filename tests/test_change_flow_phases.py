import unittest
from pathlib import Path
import sys
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_context_selection import markdown_sections

FLOW_ROOT = ROOT / "templates/target/.ai/assistant/flows"
FAMILY = ("logical-integrity-review", "blueprint-driven-change", "change-package",
          "large-task-orchestration", "project-blueprint-creation")
MUTATING = {"apply", "initialize", "material-updates", "finalize", "workstreams", "converge"}


def phase_link_failures(texts):
    """Check this bounded family only; prose effects still require human review."""
    sections = {name: markdown_sections(text) for name, text in texts.items()}
    failures, edges = [], {}
    link = re.compile(r"\[[^\]]+\]\(([^\s)]+\.flow\.md)(?:#([a-z0-9-]+))?\)")
    for name, anchors in sections.items():
        for phase in ("analyze", "plan", "apply", "verify", "initialize", "material-updates", "finalize", "workstreams", "converge"):
            if phase not in anchors:
                if phase in {"analyze", "plan", "apply", "verify"} and not (name == "logical-integrity-review" and phase == "plan"):
                    failures.append(f"missing phase: {name}#{phase}")
                continue
            edges[name, phase] = []
            body = anchors[phase][0]
            for destination, target_phase in link.findall(body):
                target = Path(destination).name.removesuffix(".flow.md")
                if target not in texts:
                    continue
                if Path(destination).parts != (target + ".flow.md",) or not target_phase or len(sections[target].get(target_phase, [])) != 1:
                    failures.append(f"unqualified or missing anchor: {name}#{phase} -> {destination}#{target_phase}")
                else:
                    edges[name, phase].append((target, target_phase))
            for target in FAMILY:
                if f"`{target}.flow.md`" in body or f"`.ai/assistant/flows/{target}.flow.md`" in body:
                    failures.append(f"unqualified family flow in {name}#{phase}: {target}")
    for origin in edges:
        if origin[1] not in {"analyze", "plan", "verify"}:
            continue
        pending, visited = list(edges[origin]), set()
        while pending:
            target = pending.pop()
            if target in visited:
                continue
            visited.add(target)
            if target[1] in MUTATING:
                failures.append(f"read-only phase reaches mutation: {origin} -> {target}")
            pending.extend(edges.get(target, []))
    return failures


class ChangeFlowPhaseTests(unittest.TestCase):
    def family(self):
        return {name: (FLOW_ROOT / (name + ".flow.md")).read_text() for name in FAMILY}

    def test_all_callers_resolve_phase_specific_links_without_mutation_reachability(self):
        self.assertEqual(phase_link_failures(self.family()), [])

    def test_nested_orchestration_handoffs_do_not_duplicate_execution_or_finalize_early(self):
        texts = self.family()
        blueprint = markdown_sections(texts["blueprint-driven-change"])
        self.assertIn("large-task-orchestration.flow.md#initialize", blueprint["apply"][0])
        self.assertIn("large-task-orchestration.flow.md#workstreams", blueprint["apply"][0])
        self.assertIn("Do not execute both paths", blueprint["apply"][0])
        orchestration = markdown_sections(texts["large-task-orchestration"])
        self.assertIn("existing operation", blueprint["apply"][0])
        self.assertIn("logical-integrity-review.flow.md#apply", orchestration["workstreams"][0])
        self.assertLess(texts["large-task-orchestration"].index("Complete the combined Project Contour Sync Decision"),
                        texts["large-task-orchestration"].index("12. When a change package"))
        self.assertIn("post-finalization binding validation", orchestration["verify"][0])
        mutated = dict(texts)
        mutated["blueprint-driven-change"] = mutated["blueprint-driven-change"].replace("logical-integrity-review.flow.md#analyze", "large-task-orchestration.flow.md#workstreams")
        self.assertTrue(any("reaches mutation" in failure for failure in phase_link_failures(mutated)))

    def test_link_mutations_and_transitive_phase_leakage_are_rejected(self):
        cases = [
            ("blueprint-driven-change", "change-package.flow.md#plan", "change-package.flow.md"),
            ("blueprint-driven-change", "change-package.flow.md#plan", "change-package.flow.md#finalize"),
            ("project-blueprint-creation", "logical-integrity-review.flow.md#analyze", "logical-integrity-review.flow.md#missing"),
            ("logical-integrity-review", "### Apply", "### Missing"),
        ]
        for name, old, new in cases:
            texts = self.family()
            self.assertIn(old, texts[name])
            texts[name] = texts[name].replace(old, new)
            with self.subTest(name=name, new=new):
                self.assertTrue(phase_link_failures(texts))
        texts = self.family()
        texts["change-package"] = texts["change-package"].replace("### Verify", "### Verify\n\nInvoke [Finalize](change-package.flow.md#finalize).")
        texts["blueprint-driven-change"] = texts["blueprint-driven-change"].replace("change-package.flow.md#plan", "change-package.flow.md#verify")
        self.assertTrue(any("reaches mutation" in failure for failure in phase_link_failures(texts)))

    def test_candidate_persistence_and_finalization_have_authorized_milestones(self):
        texts = self.family()
        integrity = markdown_sections(texts["logical-integrity-review"])
        self.assertNotIn("relationship-candidates.json", integrity["analyze"][0])
        self.assertIn("relationship-candidates.json", integrity["apply"][0])
        package = markdown_sections(texts["change-package"])
        self.assertIn("current modification authorization", package["initialize"][0])
        self.assertIn("after implementation and global reconciliation", package["finalize"][0])
        self.assertIn("sole finalization owner", package["finalize"][0])
        blueprint = texts["blueprint-driven-change"]
        self.assertLess(blueprint.index("test-first recommendation gate"), blueprint.index("smallest\n   coherent implementation"))
        self.assertIn("module is enabled", package["plan"][0])
    def test_integrity_analysis_cannot_include_repair_or_completion_steps(self):
        path = ROOT / "templates/target/.ai/assistant/flows/logical-integrity-review.flow.md"
        text = path.read_text()
        sections = markdown_sections(text)
        analysis = sections["analyze"][0]
        self.assertIn("9. Choose the source of truth", analysis)
        self.assertNotIn("10. Repair", analysis)
        self.assertNotIn("13. Run", analysis)
        self.assertIn("current modification authorization", text)
        self.assertIn("14. For multi-workstream", sections["verify"][0])
        self.assertIn("Project Contour Sync", sections["verify"][0])
        self.assertIn("returns to Apply", sections["verify"][0])

    def test_blueprint_invokes_phase_specific_integrity_and_keeps_final_scope(self):
        text = (ROOT / "templates/target/.ai/assistant/flows/blueprint-driven-change.flow.md").read_text()
        positions = [text.index("### " + phase) for phase in ("Analyze", "Plan", "Apply", "Verify")]
        self.assertEqual(positions, sorted(positions))
        sections = markdown_sections(text)
        self.assertIn("logical-integrity-review.flow.md#analyze", sections["analyze"][0])
        self.assertNotIn("logical-integrity-review.flow.md#apply", sections["analyze"][0])
        self.assertIn("current modification authorization", sections["apply"][0])
        self.assertIn("logical-integrity-review.flow.md#verify", sections["verify"][0])
        self.assertIn("complete Git change set", sections["verify"][0])
        self.assertIn("not the", sections["verify"][0])
        self.assertIn("views, not instructions to create one artifact", text)
