## Timing Feedback

Source unit tests retain the same suites, order within each shard, fixtures,
failures, and coverage. The wrapper measures execution of file suites, excluding
discovery and imports; it does not estimate file duration from shard size.
Mixed-module custom suites remain executable but may have no timing observation.

`python3 tools/check_all.py --cache-mode timing` retains runtime/content-bound
timing observations through the existing optional cache. Invalid or missing
hints fall back to normal scheduling. Partial hints use a seconds-based fallback
rather than mixing seconds with bytes. Hints cannot select or skip tests, change
validation outcomes, or establish acceptance.
