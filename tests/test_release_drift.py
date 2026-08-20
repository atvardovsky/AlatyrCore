from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from check_release_drift import nearest_tagged_baseline, prior_changelog_versions  # noqa: E402


class ReleaseBaselineTests(unittest.TestCase):
    def test_uses_nearest_real_tag_and_preserves_intervening_report_chain(self) -> None:
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

        tag, intervening = nearest_tagged_baseline(version)

        self.assertEqual(tag, "v0.1.0-alpha.3")
        self.assertEqual(intervening[0], "0.1.0-alpha.11")
        self.assertEqual(intervening[-1], "0.1.0-alpha.4")
        self.assertEqual(
            prior_changelog_versions(version)[: len(intervening)], intervening
        )


if __name__ == "__main__":
    unittest.main()
