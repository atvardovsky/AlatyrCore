"""Read-only topic-layout proposals; measurements never authorize migration."""

from __future__ import annotations

import hashlib
from itertools import islice
from typing import Iterable, TypeVar

from source_context_selection import markdown_sections


REVIEW_WORDS = 1600
MAX_REVIEW_FILES = 64
T = TypeVar("T")


def bounded_layout_inputs(values: Iterable[T]) -> list[T]:
    items = list(islice(values, MAX_REVIEW_FILES + 1))
    if len(items) > MAX_REVIEW_FILES:
        raise ValueError(f"select at most {MAX_REVIEW_FILES} documents for topic review")
    return items


def assess_topic_layout(entries: Iterable[tuple[str, str]]) -> dict:
    entries = bounded_layout_inputs(entries)
    if any(not isinstance(path, str) or not isinstance(text, str) for path, text in entries):
        raise ValueError("topic review requires path/text pairs")
    if len({path for path, _ in entries}) != len(entries):
        raise ValueError("topic review requires unique document paths")
    documents = []
    for path, text in sorted(entries):
        sections = markdown_sections(text)
        topics = [blocks[0] for blocks in sections.values()
                  if len(blocks) == 1 and blocks[0].lstrip().split(maxsplit=1)[0] == "##"]
        ambiguous = any(len(blocks) > 1 for blocks in sections.values())
        words = len(text.split())
        status = "keep-cohesive"
        if words >= REVIEW_WORDS:
            status = "propose-topic-review" if len(topics) >= 2 and not ambiguous else "review-boundaries"
        record = {
            "path": path,
            "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "words": words,
            "unique_h2_topics": len(topics),
            "ambiguous_heading_ids": ambiguous,
            "disposition": status,
        }
        if topics and not ambiguous:
            # H2 bodies do not overlap. Retain everything outside them, even
            # when a fenced example repeats a topic's exact bytes.
            common = words - sum(len(topic.split()) for topic in topics)
            # The index is a cost model, not generated or accepted documentation.
            index_words = 60 + sum(12 + len(topic.splitlines()[0].split()) - 1 for topic in topics)
            payloads = [common + index_words + len(topic.split()) for topic in topics]
            record["single_topic_model"] = {
                "retained_non_topic_words": common,
                "index_words_estimate": index_words,
                "payload_words_min": min(payloads),
                "payload_words_max": max(payloads),
                "reduction_vs_whole_percent_min": round(100 * (1 - max(payloads) / words), 1),
                "reduction_vs_whole_percent_max": round(100 * (1 - min(payloads) / words), 1),
                "body_reduction_vs_existing_section_extraction_percent": 0,
                "required_dependency_cost": "unmeasured",
            }
        documents.append(record)
    return {
        "status": "proposal-only", "automatic_migration_performed": False,
        "review_word_threshold": REVIEW_WORDS, "documents": documents,
        "model_assumptions": "index: 60 framing words, heading links and 10 summary words per H2; shared introduction retained",
        "required_before_migration": [
            "review canonical owners, generated boundaries and required dependency closure",
            "bind the proposal to current source hashes and current-scope approval",
            "pilot equivalent tasks against whole-file AND existing section extraction",
            "preserve intent, provenance, conflicts, references and a rollback mapping",
            "rebuild existing routes/catalogs and validate before retiring old paths",
        ],
        "limitations": [
            "heading boundaries do not establish semantic independence or task completeness",
            "word models do not measure tokens, latency, billing or live-agent quality",
            "small coherent documents need not be split; physical splitting alone saves no selected body text",
        ],
    }
