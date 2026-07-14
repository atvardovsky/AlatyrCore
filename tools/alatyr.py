#!/usr/bin/env python3
"""Cross-platform entry point for optional AlatyrCore source tools."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


TOOLS = Path(__file__).resolve().parent
COMMANDS_FILE = TOOLS / "tool_commands.json"


def load_commands() -> list[dict[str, Any]]:
    try:
        data = json.loads(COMMANDS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid tool command manifest: {exc}") from exc
    if data.get("schema_version") != 1 or not isinstance(data.get("commands"), list):
        raise SystemExit("unsupported tool command manifest")
    commands = data["commands"]
    names: set[str] = set()
    for command in commands:
        if not isinstance(command, dict):
            raise SystemExit("tool command entries must be objects")
        for field in ["name", "script", "purpose", "write_scope"]:
            if not isinstance(command.get(field), str) or not command[field]:
                raise SystemExit(f"tool command entry has invalid {field}")
        if command["name"] in names:
            raise SystemExit(f"duplicate tool command: {command['name']}")
        names.add(command["name"])
    return commands


def print_help(commands: list[dict[str, Any]]) -> None:
    print("Usage: alatyr.py <command> [command arguments]")
    print()
    print("Optional source tools; these commands are not the Alatyr installation mechanism.")
    print()
    print("Commands:")
    for command in commands:
        print(f"  {command['name']:<18} {command['purpose']}")
        print(f"  {'':<18} write scope: {command['write_scope']}")
    print()
    print("Run `alatyr.py <command> --help` for command-specific arguments.")


def main() -> int:
    commands = load_commands()
    if len(sys.argv) == 1 or sys.argv[1] in {"-h", "--help", "help"}:
        print_help(commands)
        return 0

    command_name = sys.argv[1]
    index = {command["name"]: command for command in commands}
    command = index.get(command_name)
    if command is None:
        print(f"Unknown Alatyr tool command: {command_name}", file=sys.stderr)
        print_help(commands)
        return 2

    script_name = command.get("script")
    if not isinstance(script_name, str) or Path(script_name).name != script_name:
        print(f"Unsafe script entry for command: {command_name}", file=sys.stderr)
        return 2
    script = TOOLS / script_name
    if not script.is_file():
        print(f"Missing command script: {script_name}", file=sys.stderr)
        return 2

    result = subprocess.run([sys.executable, str(script), *sys.argv[2:]], check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
