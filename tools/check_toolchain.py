#!/usr/bin/env python3
"""Report AlatyrCore source-tooling prerequisites with one actionable result."""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from toolchain import (
    MINIMUM_PYTHON,
    REQUIRED_PACKAGES,
    git_failure,
    missing_packages,
    package_failure,
    python_failure,
    toolchain_failure,
)


def build_report(*, require_git: bool) -> dict[str, object]:
    missing = missing_packages(REQUIRED_PACKAGES)
    failures = [
        failure
        for failure in (
            python_failure(),
            package_failure(REQUIRED_PACKAGES),
            git_failure() if require_git else None,
        )
        if failure is not None
    ]
    return {
        "status": "failed" if failures else "ok",
        "python": sys.version.split()[0],
        "minimum_python": ".".join(str(part) for part in MINIMUM_PYTHON),
        "required_packages": list(REQUIRED_PACKAGES),
        "missing_packages": list(missing),
        "git": shutil.which("git"),
        "failure": failures[0] if failures else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-git",
        action="store_true",
        help="Fail when Git is unavailable (needed by check_all and release tools).",
    )
    parser.add_argument("--json", action="store_true", help="Emit a machine-readable report.")
    args = parser.parse_args()

    failure = toolchain_failure(require_git=args.require_git)
    if args.json:
        print(json.dumps(build_report(require_git=args.require_git), sort_keys=True))
    elif failure is not None:
        print(f"FAIL: {failure}", file=sys.stderr)
    else:
        print(
            f"OK: Python {sys.version.split()[0]}, required packages, and "
            f"{'Git' if args.require_git else 'runtime'} prerequisites are available"
        )
    return 2 if failure is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
