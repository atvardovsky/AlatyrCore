import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from source_context_selection import markdown_sections


class ChangeFlowPhaseTests(unittest.TestCase):
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
