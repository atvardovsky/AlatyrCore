from pathlib import Path
import tempfile
import unittest

from tests.core_repair_workflow_fixture import run_core_repair_workflow


class CoreRepairWorkflowTests(unittest.TestCase):
    def test_public_core_workflow_accepts_current_repair_and_blocks_stale_result(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            product = target / "existing.py"
            original = b'pattern = r"\\d{2}\\."\n'
            product.write_bytes(original)
            result = run_core_repair_workflow(target)
            self.assertEqual(product.read_bytes(), original)
        self.assertFalse(result["optional_policy_created"])
        self.assertEqual(result["accepted"]["task_acceptance"]["state"], "accepted")
        self.assertEqual(result["stale_result"]["task_acceptance"]["state"], "blocked")
        self.assertTrue(any(row["level"] == "error" for row in result["stale_result"]["findings"]))


if __name__ == "__main__":
    unittest.main()
