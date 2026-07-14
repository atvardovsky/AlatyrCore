#!/usr/bin/env python3
"""Exercise captured-run validation and cost/integrity summary output."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from check_conformance_reports import REPORTS, SHARED, load_json, validate_actual_reports
from summarize_conformance_reports import load_reports, summarize_reports


def main() -> int:
    failures: list[str] = []
    shared = load_json(SHARED)
    with tempfile.TemporaryDirectory() as directory:
        actual = Path(directory)
        for source in sorted(REPORTS.glob("*.json")):
            report = load_json(source)
            report.update(
                {
                    "report_kind": "assistant-run-result",
                    "run_id": "synthetic-source-contract",
                    "assistant_surface": "codex",
                    "source_commit": "synthetic",
                    "run_provenance": {
                        "provider": "synthetic",
                        "product": "source-contract-check",
                        "model": "unknown",
                        "version_or_date": "unknown",
                        "execution_mode": "manual",
                        "started_at": "unknown",
                        "completed_at": "unknown",
                        "operator": "source-check",
                        "report_origin": "synthetic-source-contract",
                    },
                    "conformance_scope": (
                        "Synthetic source contract exercise; not target validation."
                    ),
                    "bridge_behavior_evidence": {
                        "entry_files_used": ["AGENTS.md"],
                        "auto_load_observed": "unknown; synthetic source contract",
                        "help_found": "yes; required by source contract",
                        "context_router_found": "yes; required by source contract",
                        "known_surface_limitations": [
                            "vendor behavior is not exercised by this synthetic report"
                        ],
                    },
                    "context_cost_evidence": {
                        "measurement_kind": "synthetic-source-contract",
                        "loaded_files": ["AGENTS.md", ".ai/assistant/context-router.json"],
                        "loaded_file_count": 2,
                        "approximate_words": 100,
                        "budget_exceeded": False,
                        "expansion_reasons": ["none; synthetic source contract"],
                        "receipt_reused": False,
                    },
                }
            )
            (actual / source.name).write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )

        failures.extend(
            validate_actual_reports(
                actual,
                shared,
                require_reports=True,
                require_all_fixtures=True,
            )
        )
        if not failures:
            summary = summarize_reports(load_reports([actual]))
            for required in [
                "Average loaded files: 2.00",
                "Average approximate words: 100.00",
                "Context budget exceeded: 0",
                "Changed fact evidence items:",
                "Companion surface evidence items:",
            ]:
                if required not in summary:
                    failures.append(f"captured-run summary missing {required}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("OK: checked captured-run cost and logical-integrity summary evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
