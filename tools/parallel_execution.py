"""Bounded, deterministic subprocess execution for source checks."""

from __future__ import annotations

import concurrent.futures
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


CHILD_CAPACITY_ENV = "ALATYR_CHILD_CAPACITY"


@dataclass(frozen=True)
class CommandResult:
    item_id: str
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float = 0.0


def child_capacity(default: int = 1) -> int:
    """Return capacity assigned by the parent source-check scheduler."""

    raw = os.environ.get(CHILD_CAPACITY_ENV)
    if raw is None:
        return max(1, default)
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def run_commands(
    commands: Iterable[tuple[str, list[str]]],
    *,
    cwd: Path,
    capacity: int | None = None,
    on_complete: Callable[[CommandResult], None] | None = None,
) -> list[CommandResult]:
    """Notify as results become ready; return in declaration order.

    Notifications run on the collecting thread after command timing ends.
    Ordinary worker/observer errors propagate after all commands converge.
    Children inherit the caller's process group for its outer watchdog.
    """

    declared = list(commands)
    if not declared:
        return []
    item_ids = [item_id for item_id, _command in declared]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("parallel command item IDs must be unique")
    workers = min(max(1, capacity or child_capacity()), len(declared))

    def execute(item: tuple[str, list[str]]) -> CommandResult:
        item_id, command = item
        environment = os.environ.copy()
        environment[CHILD_CAPACITY_ENV] = "1"
        started = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            return CommandResult(
                item_id,
                127,
                "",
                str(exc),
                round(time.monotonic() - started, 6),
            )
        return CommandResult(
            item_id=item_id,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=round(time.monotonic() - started, 6),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(execute, (item_id, command)): item_id
            for item_id, command in declared
        }
        results: dict[str, CommandResult] = {}
        errors: dict[str, Exception] = {}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                errors[futures[future]] = exc
                continue
            results[futures[future]] = result
            if on_complete is not None:
                try:
                    on_complete(result)
                except Exception as exc:
                    errors[futures[future]] = exc
        if errors:
            raise next(errors[item_id] for item_id in item_ids if item_id in errors)
        return [results[item_id] for item_id, _command in declared]
