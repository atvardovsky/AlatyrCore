#!/usr/bin/env python3
"""Select a declared least-cost eligible worker option without dispatching."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cli_inputs import Once, json_object
from context_input_snapshot import read_regular_context_bytes
from worker_model_selection import review_selection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", type=Path, required=True, action=Once)
    parser.add_argument("--record", type=Path, required=True, action=Once)
    args = parser.parse_args()
    try:
        root = args.target.resolve(strict=True)
        path = (root / args.record).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError("model selection record must remain inside the target")
        raw = read_regular_context_bytes(path, max_bytes=65536)
        record = json_object(raw, "model selection")
        result = review_selection(record, packet_id=record.get("packet_id"), node_id=record.get("node_id"),
            capability_sha256=record.get("capability_sha256"), execution_state="PLANNED", choose=True)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc), "authorization_granted": False, "acceptance_granted": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
