#!/usr/bin/env python3
"""Review selected current and retained case evidence without executing tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cli_inputs import Once, json_object
from qualification_evidence import review_qualification
from target_adapter_validation.context import TargetRepositoryView


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True, action=Once)
    parser.add_argument("--manifest", required=True, action=Once)
    args = parser.parse_args()
    try:
        from request_values import request_path
        root = args.target.resolve(strict=True)
        view = TargetRepositoryView(root)
        read = view.read_bytes_result(root / request_path(args.manifest), max_bytes=65536)
        if read.value is None:
            raise ValueError("qualification manifest is unavailable")
        result = review_qualification(view, root, json_object(read.value, "qualification manifest"))
        if view.finalize():
            raise ValueError("qualification inputs changed during review")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc), "authorization_granted": False, "acceptance_granted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
