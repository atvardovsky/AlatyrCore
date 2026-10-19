"""Shared current-task bindings for finalization and upgrade verification."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

TASK_CLASSES = ("small-task", "standard-task", "large-or-resumable", "protected-or-sensitive")


def add_task_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task-id")
    parser.add_argument("--task-class", choices=TASK_CLASSES)
    parser.add_argument("--problem-model", action="append", type=Path, default=[])
    parser.add_argument("--require-task-acceptance", action="store_true",
                        help="Require final closure of the explicitly bound current task, not only adapter health.")


def task_arguments(*, task_id: str | None, task_class: str | None,
                   problem_models: Iterable[Path] = (), required: bool = False) -> list[str]:
    if required and not (task_id and task_class):
        raise ValueError("--require-task-acceptance requires --task-id and --task-class")
    if task_class and not task_id:
        raise ValueError("--task-class requires --task-id")
    result = []
    if task_id:
        result.extend(["--task-id", task_id])
    if task_class:
        result.extend(["--task-class", task_class])
    for model in problem_models:
        result.extend(["--problem-model", str(model)])
    if required:
        result.append("--require-task-acceptance")
    return result
