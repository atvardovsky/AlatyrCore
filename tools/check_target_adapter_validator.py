#!/usr/bin/env python3
"""Exercise stable contracts of the portable target adapter validator."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from target_adapter_validation.harness_scenarios import run_scenarios
from target_adapter_validation.harness_scenarios.common import check_core_contracts


def main() -> int:
    failures: list[str] = []
    check_core_contracts(failures)
    with tempfile.TemporaryDirectory() as directory:
        run_scenarios(Path(directory), failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("OK: checked target adapter validator routing, scope, and evidence contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
