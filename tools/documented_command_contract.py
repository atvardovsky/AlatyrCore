"""Validate documented command examples against their executable parser."""

from __future__ import annotations

import argparse
import contextlib
import io
import shlex
from dataclasses import dataclass
from typing import Callable, Literal, Mapping


ShellKind = Literal["posix", "powershell", "cmd"]


@dataclass(frozen=True)
class DocumentedInvocation:
    marker: str
    shell: ShellKind


def _argument_tokens(text: str, shell: ShellKind) -> list[str]:
    return shlex.split(text, posix=shell == "posix")


def _argument_text(line: str, marker_start: int, marker: str) -> str:
    prefix = line[:marker_start]
    argument_text = line[marker_start + len(marker) :].strip()
    if prefix.endswith("`") and argument_text.endswith("`"):
        argument_text = argument_text[:-1].rstrip()
    return argument_text


def argparse_documentation_failures(
    documents: Mapping[str, str],
    *,
    invocations: tuple[DocumentedInvocation, ...],
    parser_factory: Callable[[], argparse.ArgumentParser],
) -> list[str]:
    """Parse every recognized example with the command's canonical parser."""

    failures: list[str] = []
    seen: set[DocumentedInvocation] = set()
    for relpath, text in documents.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            for invocation in invocations:
                marker_start = line.find(invocation.marker)
                if marker_start < 0:
                    continue
                seen.add(invocation)
                raw_arguments = _argument_text(
                    line, marker_start, invocation.marker
                )
                try:
                    arguments = _argument_tokens(raw_arguments, invocation.shell)
                except ValueError as exc:
                    failures.append(
                        f"{relpath}:{line_number} cannot tokenize documented "
                        f"command: {exc}"
                    )
                    continue
                stderr = io.StringIO()
                try:
                    with contextlib.redirect_stderr(stderr):
                        parser_factory().parse_args(arguments)
                except SystemExit as exc:
                    diagnostic = stderr.getvalue().strip().splitlines()
                    reason = diagnostic[-1] if diagnostic else f"parser exit {exc.code}"
                    failures.append(
                        f"{relpath}:{line_number} documented command is rejected "
                        f"by its parser: {reason}"
                    )
    for invocation in invocations:
        if invocation not in seen:
            failures.append(
                f"missing documented command example: {invocation.marker}"
            )
    return failures
